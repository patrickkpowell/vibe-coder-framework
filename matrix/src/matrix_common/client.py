from __future__ import annotations

import uuid
from urllib.parse import quote

import httpx

from .errors import MatrixAuthError, MatrixSendError
from .messages import build_formatted_payload, build_text_payload
from .retry import retry_async


class MatrixClient:
    def __init__(
        self,
        homeserver_url: str,
        access_token: str,
        timeout: float = 15.0,
    ) -> None:
        self._base = homeserver_url.rstrip("/")
        self._token = access_token
        self._timeout = timeout

    @property
    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------ send

    async def send_text(self, room_id: str, body: str, severity: str = "info") -> str:
        return await self._send_event(room_id, build_text_payload(body, severity))

    async def send_formatted(
        self, room_id: str, body: str, formatted_body: str, severity: str = "info"
    ) -> str:
        return await self._send_event(
            room_id, build_formatted_payload(body, formatted_body, severity)
        )

    async def _send_event(self, room_id: str, payload: dict) -> str:
        txn_id = str(uuid.uuid4())
        encoded = quote(room_id, safe="")
        url = (
            f"{self._base}/_matrix/client/v3/rooms/{encoded}"
            f"/send/m.room.message/{txn_id}"
        )

        async def attempt() -> str:
            async with httpx.AsyncClient(timeout=self._timeout) as http:
                r = await http.put(url, headers=self._auth_headers, json=payload)
                if r.status_code == 401:
                    raise MatrixAuthError("Bot access token rejected by homeserver")
                if r.status_code >= 500:
                    raise MatrixSendError(
                        f"Homeserver error {r.status_code}", r.status_code
                    )
                r.raise_for_status()
                return r.json()["event_id"]

        return await retry_async(
            attempt,
            max_attempts=3,
            retriable=(MatrixSendError, httpx.TransportError, httpx.TimeoutException),
        )

    # ------------------------------------------------------------------ rooms

    async def create_room(
        self,
        name: str,
        alias: str | None = None,
        invite_users: list[str] | None = None,
    ) -> str:
        url = f"{self._base}/_matrix/client/v3/createRoom"
        payload: dict = {
            "name": name,
            "preset": "private_chat",
            "visibility": "private",
        }
        if alias:
            payload["room_alias_name"] = alias
        if invite_users:
            payload["invite"] = invite_users
        async with httpx.AsyncClient(timeout=self._timeout) as http:
            r = await http.post(url, headers=self._auth_headers, json=payload)
            if r.status_code == 401:
                raise MatrixAuthError("Bot access token rejected by homeserver")
            r.raise_for_status()
            return r.json()["room_id"]

    async def invite_user(self, room_id: str, user_id: str) -> None:
        encoded = quote(room_id, safe="")
        url = f"{self._base}/_matrix/client/v3/rooms/{encoded}/invite"
        async with httpx.AsyncClient(timeout=self._timeout) as http:
            r = await http.post(
                url, headers=self._auth_headers, json={"user_id": user_id}
            )
            if r.status_code == 401:
                raise MatrixAuthError("Bot access token rejected by homeserver")
            r.raise_for_status()

    def update_token(self, token: str) -> None:
        self._token = token

    # ------------------------------------------------------------------ health

    async def whoami(self) -> dict:
        url = f"{self._base}/_matrix/client/v3/account/whoami"
        async with httpx.AsyncClient(timeout=self._timeout) as http:
            r = await http.get(url, headers=self._auth_headers)
            if r.status_code == 401:
                raise MatrixAuthError("Bot access token rejected")
            r.raise_for_status()
            return r.json()

    async def check_homeserver(self) -> bool:
        url = f"{self._base}/_matrix/client/versions"
        try:
            async with httpx.AsyncClient(timeout=5.0) as http:
                r = await http.get(url)
                return r.status_code == 200
        except Exception:
            return False
