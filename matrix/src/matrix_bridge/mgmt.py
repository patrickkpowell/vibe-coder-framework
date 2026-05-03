"""Loopback-only management HTTP server.

Handles MCP-to-bridge coordination signals — never bound to a public interface.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR", "/srv/vibe-code/claude-sessions"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MgmtServer:
    """Minimal asyncio TCP server handling /internal/handoff/<name>."""

    def __init__(self, port: int, handoff_handler) -> None:
        self._port = port
        self._handoff_handler = handoff_handler
        self._server = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle, "127.0.0.1", self._port
        )
        logger.info("Management server listening on 127.0.0.1:%d", self._port)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            raw = await asyncio.wait_for(reader.read(4096), timeout=5.0)
            text = raw.decode(errors="replace")
            lines = text.split("\r\n")
            if not lines:
                self._respond(writer, 400, "Bad Request")
                return

            # Parse request line: METHOD PATH HTTP/1.1
            parts = lines[0].split()
            if len(parts) < 2 or parts[0] != "POST":
                self._respond(writer, 405, "Method Not Allowed")
                return

            path = parts[1]
            # Expected: /internal/handoff/<name>
            if not path.startswith("/internal/handoff/"):
                self._respond(writer, 404, "Not Found")
                return

            session_name = path[len("/internal/handoff/"):]
            if not session_name:
                self._respond(writer, 400, "Missing session name")
                return

            # Extract JSON body (last non-empty line after blank separator)
            body = ""
            sep = text.find("\r\n\r\n")
            if sep != -1:
                body = text[sep + 4:].strip()
            nonce = ""
            if body:
                try:
                    nonce = json.loads(body).get("nonce", "")
                except Exception:
                    pass

            logger.info(
                "Handoff request for session %s nonce=%s", session_name, nonce[:8]
            )

            asyncio.create_task(self._handoff_handler(session_name, nonce))
            self._respond(writer, 202, "Accepted")

        except Exception as exc:
            logger.exception("Management request error: %s", exc)
            self._respond(writer, 500, "Internal Server Error")
        finally:
            writer.close()
            await writer.wait_closed()

    def _respond(self, writer: asyncio.StreamWriter, code: int, msg: str) -> None:
        body = json.dumps({"status": msg}).encode()
        response = (
            f"HTTP/1.1 {code} {msg}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode() + body
        writer.write(response)


async def write_handoff_to_nas(
    session_name: str,
    content: str,
    nonce: str = "",
) -> None:
    """Write handoff content to the NAS session directory."""
    session_dir = SESSIONS_DIR / session_name
    if not session_dir.exists():
        logger.warning("Session directory not found: %s", session_dir)
        return

    # Atomic write of handoff.md
    tmp = session_dir / "handoff.tmp"
    tmp.write_text(content)
    tmp.rename(session_dir / "handoff.md")

    if nonce:
        (session_dir / f"handoff-{nonce}.md").write_text(content)

    # Update meta.json
    meta_path = session_dir / "meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            meta["last_handoff"] = _now()
            meta["last_activity"] = _now()
            tmp_meta = meta_path.with_suffix(".tmp")
            tmp_meta.write_text(json.dumps(meta, indent=2))
            tmp_meta.rename(meta_path)
        except Exception as exc:
            logger.warning("Could not update meta.json: %s", exc)

    # Clean up sentinel
    sentinel = session_dir / "handoff-requested"
    sentinel.unlink(missing_ok=True)

    logger.info("Handoff written for session %s nonce=%s", session_name, nonce[:8] if nonce else "")
