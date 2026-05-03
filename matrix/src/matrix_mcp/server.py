from __future__ import annotations

import logging
import re
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from matrix_common.client import MatrixClient
from matrix_common.destinations import DestinationResolver
from matrix_common.errors import DestinationNotFoundError, MatrixAuthError, MatrixSendError

from .config import get_settings
from .logging_config import configure_logging
from .schemas import (
    CreateRoomResult,
    DestinationsResult,
    InviteUserResult,
    SendMessageResult,
    SendTemplateResult,
)

configure_logging("matrix-mcp")
logger = logging.getLogger(__name__)

settings = get_settings()
resolver = DestinationResolver.from_json(settings.matrix_destinations_json)
matrix = MatrixClient(
    homeserver_url=settings.matrix_homeserver_url,
    access_token=settings.matrix_bot_access_token,
)

mcp = FastMCP("matrix-notifications")

_MATRIX_USER_ID_RE = re.compile(r"^@[a-zA-Z0-9._~!$&'()*+,;=%-]+:.+$")

# ── tools ─────────────────────────────────────────────────────────────────────


@mcp.tool()
async def send_matrix_message(
    message: str = Field(..., description="Plain text message body", min_length=1, max_length=16000),
    destination: str | None = Field(None, description="Named destination (e.g. 'home-alerts'). Defaults to the configured default."),
    severity: str = Field("info", description="One of: debug, info, warning, error, critical"),
) -> SendMessageResult:
    """Send a plain text notification to an allowlisted Matrix destination."""
    dest_name = destination or settings.matrix_default_destination
    try:
        room_id = resolver.resolve(dest_name)
    except DestinationNotFoundError:
        raise ValueError(f"Unknown destination: {dest_name!r}. Available: {resolver.names()}")

    try:
        event_id = await matrix.send_text(room_id=room_id, body=message, severity=severity)
    except MatrixAuthError as exc:
        raise RuntimeError(f"Bot authentication failure: {exc}") from exc
    except MatrixSendError as exc:
        raise RuntimeError(f"Failed to deliver message: {exc}") from exc

    logger.info("Message sent via MCP", extra={"destination": dest_name, "event_id": event_id})
    return SendMessageResult(status="ok", destination=dest_name, event_id=event_id)


@mcp.tool()
async def send_matrix_template(
    template: str = Field(..., description="Template name (e.g. 'elastic_pq_warning')"),
    values: dict[str, Any] = Field(default_factory=dict, description="Template substitution values"),
    destination: str | None = Field(None, description="Named destination. Defaults to the configured default."),
) -> SendTemplateResult:
    """Send a message using a server-side template. Only bundled templates may be used."""
    from matrix_api import templates as tmpl
    from matrix_common.errors import TemplateNotFoundError

    dest_name = destination or settings.matrix_default_destination
    try:
        room_id = resolver.resolve(dest_name)
    except DestinationNotFoundError:
        raise ValueError(f"Unknown destination: {dest_name!r}. Available: {resolver.names()}")

    try:
        plain_body, html_body = tmpl.render(template, values)
    except TemplateNotFoundError:
        raise ValueError(f"Unknown template: {template!r}. Available: {tmpl.available()}")
    except KeyError as exc:
        raise ValueError(f"Missing template value: {exc}") from exc

    try:
        event_id = await matrix.send_formatted(room_id=room_id, body=plain_body, formatted_body=html_body)
    except MatrixAuthError as exc:
        raise RuntimeError(f"Bot authentication failure: {exc}") from exc
    except MatrixSendError as exc:
        raise RuntimeError(f"Failed to deliver message: {exc}") from exc

    logger.info("Template message sent via MCP", extra={"destination": dest_name, "template": template})
    return SendTemplateResult(status="ok", destination=dest_name, event_id=event_id)


@mcp.tool()
async def list_matrix_destinations() -> DestinationsResult:
    """List configured Matrix notification destinations and the default."""
    return DestinationsResult(
        default=settings.matrix_default_destination,
        destinations=resolver.names(),
    )


@mcp.tool()
async def create_matrix_room(
    name: str = Field(..., description="Display name for the new room"),
    alias: str | None = Field(None, description="Local room alias (no server part, e.g. 'elastic-alerts')"),
    invite_users: list[str] = Field(default_factory=list, description="Matrix user IDs to invite (e.g. '@patrick:matrix.powellcompanies.com')"),
) -> CreateRoomResult:
    """Create a new private Matrix room. ADMIN TOOL — disabled unless MATRIX_MCP_ENABLE_ADMIN_TOOLS=true."""
    if not settings.matrix_mcp_enable_admin_tools:
        raise PermissionError("Admin tools are disabled. Set MATRIX_MCP_ENABLE_ADMIN_TOOLS=true to enable.")

    for uid in invite_users:
        if not _MATRIX_USER_ID_RE.match(uid):
            raise ValueError(f"Invalid Matrix user ID: {uid!r}")

    try:
        room_id = await matrix.create_room(name=name, alias=alias, invite_users=invite_users or None)
    except MatrixAuthError as exc:
        raise RuntimeError(f"Bot authentication failure: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Room creation failed: {exc}") from exc

    logger.info("Room created via MCP", extra={"room_id": room_id, "name": name})
    return CreateRoomResult(status="ok", room_id=room_id, name=name)


@mcp.tool()
async def invite_matrix_user(
    destination: str = Field(..., description="Named destination to invite the user to"),
    user_id: str = Field(..., description="Matrix user ID to invite (e.g. '@patrick:matrix.powellcompanies.com')"),
) -> InviteUserResult:
    """Invite a Matrix user to a configured destination room. ADMIN TOOL — disabled unless MATRIX_MCP_ENABLE_ADMIN_TOOLS=true."""
    if not settings.matrix_mcp_enable_admin_tools:
        raise PermissionError("Admin tools are disabled. Set MATRIX_MCP_ENABLE_ADMIN_TOOLS=true to enable.")

    if not _MATRIX_USER_ID_RE.match(user_id):
        raise ValueError(f"Invalid Matrix user ID: {user_id!r}")

    try:
        room_id = resolver.resolve(destination)
    except DestinationNotFoundError:
        raise ValueError(f"Unknown destination: {destination!r}. Available: {resolver.names()}")

    try:
        await matrix.invite_user(room_id=room_id, user_id=user_id)
    except MatrixAuthError as exc:
        raise RuntimeError(f"Bot authentication failure: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Invite failed: {exc}") from exc

    logger.info("User invited via MCP", extra={"destination": destination, "user_id": user_id})
    return InviteUserResult(status="ok", destination=destination, user_id=user_id)


# ── health route ──────────────────────────────────────────────────────────────


async def health(request: Request) -> JSONResponse:
    hs_ok = await matrix.check_homeserver()
    if not hs_ok:
        return JSONResponse(
            {"status": "degraded", "detail": "homeserver unreachable"}, status_code=503
        )
    return JSONResponse(
        {"status": "ok", "service": "matrix-mcp", "bot_user_id": settings.matrix_bot_user_id}
    )


# ── entry point ───────────────────────────────────────────────────────────────


if __name__ == "__main__":
    mcp_asgi = mcp.streamable_http_app()
    app = Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Mount("/mcp", app=mcp_asgi),
        ]
    )
    logger.info(
        "matrix-mcp starting",
        extra={"host": settings.matrix_mcp_host, "port": settings.matrix_mcp_port},
    )
    uvicorn.run(
        app,
        host=settings.matrix_mcp_host,
        port=settings.matrix_mcp_port,
        log_config=None,
    )
