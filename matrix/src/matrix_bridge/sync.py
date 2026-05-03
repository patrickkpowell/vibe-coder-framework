from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx

from matrix_bridge.config import BridgeConfig
from matrix_bridge.db import Database
from matrix_bridge.dispatcher import Dispatcher

logger = logging.getLogger(__name__)

# Ignore events older than this on startup to avoid replaying history
_MAX_AGE_MS = 60_000
# How often to scan for handoff-requested sentinels (seconds)
_SENTINEL_CHECK_INTERVAL = 30

SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR", "/srv/vibe-code/claude-sessions"))


class SyncLoop:
    def __init__(
        self,
        settings: BridgeConfig,
        db: Database,
        dispatcher: Dispatcher,
        handoff_handler=None,
    ) -> None:
        self._settings = settings
        self._db = db
        self._dispatcher = dispatcher
        self._running = False
        self._handoff_handler = handoff_handler
        self._last_sentinel_check: float = 0

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._settings.matrix_bot_access_token}"}

    async def run(self) -> None:
        self._running = True
        since = await self._db.get_sync_token()

        if since is None:
            since = await self._initial_sync()

        logger.info("Sync loop started", extra={"since": since})

        async with httpx.AsyncClient(
            base_url=self._settings.matrix_homeserver_url, timeout=45.0
        ) as http:
            while self._running:
                since = await self._poll(http, since)

    async def stop(self) -> None:
        self._running = False

    async def _initial_sync(self) -> str:
        """Fast-forward to now without processing any events."""
        async with httpx.AsyncClient(
            base_url=self._settings.matrix_homeserver_url, timeout=30.0
        ) as http:
            r = await http.get(
                "/_matrix/client/v3/sync",
                headers=self._headers,
                params={"timeout": 0, "full_state": "false"},
            )
            r.raise_for_status()
            token: str = r.json()["next_batch"]
            await self._db.save_sync_token(token)
            logger.info("Initial sync complete, positioned at now")
            return token

    async def _poll(self, http: httpx.AsyncClient, since: str) -> str:
        try:
            r = await http.get(
                "/_matrix/client/v3/sync",
                headers=self._headers,
                params={
                    "since": since,
                    "timeout": self._settings.matrix_bridge_sync_timeout_ms,
                    "full_state": "false",
                },
            )
            r.raise_for_status()
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            logger.warning("Sync request failed: %s — retrying in 5s", exc)
            await asyncio.sleep(5)
            return since
        except httpx.HTTPStatusError as exc:
            logger.error("Sync HTTP error %s — retrying in 10s", exc.response.status_code)
            await asyncio.sleep(10)
            return since

        data = r.json()
        next_batch: str = data["next_batch"]

        for room_id, room_data in data.get("rooms", {}).get("join", {}).items():
            if room_id not in self._settings.allowed_rooms:
                continue
            for event in room_data.get("timeline", {}).get("events", []):
                await self._handle_event(room_id, event)

        await self._db.save_sync_token(next_batch)

        # Periodic sentinel file check (fallback for MCP→bridge signaling)
        now = time.monotonic()
        if self._handoff_handler and now - self._last_sentinel_check > _SENTINEL_CHECK_INTERVAL:
            self._last_sentinel_check = now
            asyncio.create_task(self._check_sentinels())

        return next_batch

    async def _check_sentinels(self) -> None:
        if not SESSIONS_DIR.exists():
            return
        try:
            for session_dir in SESSIONS_DIR.iterdir():
                if not session_dir.is_dir():
                    continue
                sentinel = session_dir / "handoff-requested"
                if sentinel.exists():
                    try:
                        data = json.loads(sentinel.read_text())
                        nonce = data.get("nonce", "")
                        name = session_dir.name
                        logger.info("Sentinel found for session %s — triggering handoff", name)
                        asyncio.create_task(self._handoff_handler(name, nonce))
                    except Exception as exc:
                        logger.warning("Sentinel read error %s: %s", sentinel, exc)
        except Exception as exc:
            logger.warning("Sentinel scan error: %s", exc)

    async def _handle_event(self, room_id: str, event: dict[str, Any]) -> None:
        if event.get("type") != "m.room.message":
            return

        event_id: str = event.get("event_id", "")
        sender: str = event.get("sender", "")
        content = event.get("content", {})
        body: str = content.get("body", "")
        age_ms: int = event.get("unsigned", {}).get("age", 0)

        if not event_id or not sender or not body:
            return
        if sender == self._settings.matrix_bot_user_id:
            return
        if sender not in self._settings.allowed_users:
            logger.debug("Ignoring message from unauthorized user %s", sender)
            return
        if age_ms > _MAX_AGE_MS:
            logger.debug("Skipping old event %s (age %dms)", event_id, age_ms)
            return
        if await self._db.is_processed(event_id):
            return

        await self._db.mark_processed(event_id)
        logger.info(
            "Event received",
            extra={"event_id": event_id, "sender": sender, "room_id": room_id},
        )

        await self._dispatcher.dispatch(room_id, sender, event_id, body)
