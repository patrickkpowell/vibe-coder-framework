from __future__ import annotations

import hashlib
import logging
import time
from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from matrix_common.client import MatrixClient
from matrix_common.destinations import DestinationResolver
from matrix_common.errors import (
    DestinationNotFoundError,
    MatrixAuthError,
    MatrixSendError,
    TemplateNotFoundError,
)

from .config import Settings, get_settings
from .logging_config import configure_logging
from .models import (
    DestinationsResponse,
    HealthResponse,
    SendRequest,
    SendResponse,
    SendTemplateRequest,
)
from .ratelimit import TokenBucket, parse_rate
from . import templates as tmpl

configure_logging("matrix-api")
logger = logging.getLogger(__name__)

_bearer = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    rate, per = parse_rate(settings.matrix_rate_limit)
    app.state.bucket = TokenBucket(rate, per)
    app.state.client = MatrixClient(
        homeserver_url=settings.matrix_homeserver_url,
        access_token=settings.matrix_bot_access_token,
    )
    app.state.resolver = DestinationResolver.from_json(settings.matrix_destinations_json)
    logger.info("matrix-api started", extra={"homeserver": settings.matrix_homeserver_url})
    yield
    logger.info("matrix-api shutting down")


app = FastAPI(title="matrix-api", lifespan=lifespan)


# ── auth ──────────────────────────────────────────────────────────────────────


def _require_auth(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    if credentials.credentials != settings.matrix_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ── helpers ───────────────────────────────────────────────────────────────────


async def _rate_limit(request: Request) -> None:
    bucket: TokenBucket = request.app.state.bucket
    if not await bucket.acquire():
        retry = bucket.retry_after_seconds()
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(int(retry) + 1)},
        )


def _hash_room_id(room_id: str) -> str:
    return hashlib.sha256(room_id.encode()).hexdigest()[:12]


# ── routes ────────────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
async def health(request: Request) -> Any:
    settings = get_settings()
    client: MatrixClient = request.app.state.client
    hs_ok = await client.check_homeserver()
    if not hs_ok:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "detail": "homeserver unreachable"},
        )
    return HealthResponse(
        status="ok",
        homeserver=settings.matrix_homeserver_url,
        bot_user_id=settings.matrix_bot_user_id,
    )


@app.get(
    "/destinations",
    response_model=DestinationsResponse,
    dependencies=[Depends(_require_auth)],
)
async def list_destinations(request: Request) -> Any:
    settings = get_settings()
    resolver: DestinationResolver = request.app.state.resolver
    return DestinationsResponse(
        default=settings.matrix_default_destination,
        destinations=resolver.names(),
    )


@app.post(
    "/send",
    response_model=SendResponse,
    dependencies=[Depends(_require_auth), Depends(_rate_limit)],
)
async def send_message(body: SendRequest, request: Request) -> Any:
    settings = get_settings()
    resolver: DestinationResolver = request.app.state.resolver
    client: MatrixClient = request.app.state.client

    dest_name = body.destination or settings.matrix_default_destination
    t0 = time.monotonic()
    try:
        room_id = resolver.resolve(dest_name)
    except DestinationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown destination: {dest_name!r}")

    try:
        if body.formatted_message:
            event_id = await client.send_formatted(
                room_id, body.message, body.formatted_message, body.severity
            )
        else:
            event_id = await client.send_text(room_id, body.message, body.severity)
    except MatrixAuthError as exc:
        logger.error("Bot auth failure", extra={"error": str(exc)})
        raise HTTPException(status_code=502, detail="Bot authentication failure")
    except MatrixSendError as exc:
        logger.error("Matrix send failed", extra={"error": str(exc), "dest": dest_name})
        raise HTTPException(status_code=502, detail="Failed to deliver Matrix message")
    except Exception as exc:
        logger.error("Unexpected error", extra={"error": str(exc), "dest": dest_name})
        raise HTTPException(status_code=503, detail="Service error")

    latency_ms = int((time.monotonic() - t0) * 1000)
    logger.info(
        "Message sent",
        extra={
            "destination": dest_name,
            "room_id_hash": _hash_room_id(room_id),
            "event_id": event_id,
            "severity": body.severity,
            "latency_ms": latency_ms,
            "metadata_keys": list(body.metadata.keys()),
        },
    )
    return SendResponse(
        status="ok", destination=dest_name, room_id=room_id, event_id=event_id
    )


@app.post(
    "/send-template",
    response_model=SendResponse,
    dependencies=[Depends(_require_auth), Depends(_rate_limit)],
)
async def send_template(body: SendTemplateRequest, request: Request) -> Any:
    settings = get_settings()
    resolver: DestinationResolver = request.app.state.resolver
    client: MatrixClient = request.app.state.client

    dest_name = body.destination or settings.matrix_default_destination
    try:
        room_id = resolver.resolve(dest_name)
    except DestinationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown destination: {dest_name!r}")

    try:
        plain_body, html_body = tmpl.render(body.template, body.values)
    except TemplateNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown template: {body.template!r}")
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"Missing template value: {exc}")

    try:
        event_id = await client.send_formatted(room_id, plain_body, html_body)
    except MatrixAuthError as exc:
        logger.error("Bot auth failure", extra={"error": str(exc)})
        raise HTTPException(status_code=502, detail="Bot authentication failure")
    except MatrixSendError as exc:
        logger.error("Matrix send failed", extra={"error": str(exc)})
        raise HTTPException(status_code=502, detail="Failed to deliver Matrix message")

    logger.info(
        "Template message sent",
        extra={
            "destination": dest_name,
            "room_id_hash": _hash_room_id(room_id),
            "event_id": event_id,
            "template": body.template,
        },
    )
    return SendResponse(
        status="ok", destination=dest_name, room_id=room_id, event_id=event_id
    )
