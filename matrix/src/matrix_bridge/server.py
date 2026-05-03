from __future__ import annotations

import asyncio
import json
import logging

from matrix_bridge.metrics import bridge_metrics

logger = logging.getLogger(__name__)

_CONTENT_TYPES = {
    "/metrics": "text/plain; version=0.0.4",
    "/health": "application/json",
    "/ready": "application/json",
}


class HealthServer:
    """Minimal asyncio HTTP server exposing /health, /ready, and /metrics."""

    def __init__(self, db, matrix_client, host: str = "0.0.0.0", port: int = 8090) -> None:
        self._db = db
        self._matrix_client = matrix_client
        self._host = host
        self._port = port
        self._server: asyncio.Server | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle, self._host, self._port
        )
        logger.info("Health server listening on %s:%d", self._host, self._port)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            raw = await asyncio.wait_for(reader.read(512), timeout=5.0)
        except (asyncio.TimeoutError, ConnectionResetError):
            writer.close()
            return

        try:
            request_line = raw.decode(errors="replace").split("\r\n")[0]
            parts = request_line.split(" ")
            path = parts[1] if len(parts) >= 2 else "/"
        except Exception:
            path = "/"

        status, body, content_type = await self._route(path)
        encoded = body.encode()
        response = (
            f"HTTP/1.1 {status}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(encoded)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode() + encoded

        try:
            writer.write(response)
            await writer.drain()
        finally:
            writer.close()

    async def _route(self, path: str) -> tuple[str, str, str]:
        if path == "/health":
            return "200 OK", json.dumps({"status": "ok"}), "application/json"

        if path == "/ready":
            checks: dict[str, str] = {}
            ok = True

            try:
                await self._db.ping()
                checks["database"] = "ok"
            except Exception as exc:
                checks["database"] = f"error: {exc}"
                ok = False

            try:
                result = await self._matrix_client.whoami()
                checks["matrix"] = "ok" if result else "no response"
                if not result:
                    ok = False
            except Exception as exc:
                checks["matrix"] = f"error: {exc}"
                ok = False

            status = "200 OK" if ok else "503 Service Unavailable"
            body = json.dumps({"status": "ok" if ok else "degraded", "checks": checks})
            return status, body, "application/json"

        if path == "/metrics":
            return "200 OK", bridge_metrics.render(), "text/plain; version=0.0.4"

        return "404 Not Found", json.dumps({"error": "not found"}), "application/json"
