from __future__ import annotations

import os
from dataclasses import dataclass, field

from matrix_bridge.secrets import BridgeSecrets, load_secrets

_instance: BridgeConfig | None = None


@dataclass
class BridgeConfig:
    # From SOPS
    matrix_bot_access_token: str
    database_url: str
    _allowed_users_raw: str
    _allowed_rooms_raw: str

    # From env — non-sensitive runtime config
    matrix_homeserver_url: str = field(default="http://localhost:8008")
    matrix_bot_user_id: str = field(default="")
    matrix_bridge_sync_timeout_ms: int = field(default=30000)
    projects_dir: str = field(default="/srv/claude-matrix/projects")
    skills_dir: str = field(default="/srv/claude-matrix/skills")
    metrics_port: int = field(default=8090)

    @property
    def allowed_users(self) -> set[str]:
        return {u.strip() for u in self._allowed_users_raw.split(",") if u.strip()}

    @property
    def allowed_rooms(self) -> set[str]:
        return {r.strip() for r in self._allowed_rooms_raw.split(",") if r.strip()}

    @classmethod
    def load(cls) -> BridgeConfig:
        secrets: BridgeSecrets = load_secrets()
        return cls(
            matrix_bot_access_token=secrets.bot_access_token,
            database_url=secrets.database_url,
            _allowed_users_raw=secrets.allowed_users,
            _allowed_rooms_raw=secrets.allowed_rooms,
            matrix_homeserver_url=os.environ.get(
                "MATRIX_HOMESERVER_URL", "http://localhost:8008"
            ),
            matrix_bot_user_id=os.environ.get("MATRIX_BOT_USER_ID", ""),
            matrix_bridge_sync_timeout_ms=int(
                os.environ.get("MATRIX_BRIDGE_SYNC_TIMEOUT_MS", "30000")
            ),
            projects_dir=os.environ.get(
                "MATRIX_BRIDGE_PROJECTS_DIR", "/srv/claude-matrix/projects"
            ),
            skills_dir=os.environ.get(
                "MATRIX_BRIDGE_SKILLS_DIR", "/srv/claude-matrix/skills"
            ),
            metrics_port=int(os.environ.get("MATRIX_BRIDGE_METRICS_PORT", "8090")),
        )


def get_config() -> BridgeConfig:
    global _instance
    if _instance is None:
        _instance = BridgeConfig.load()
    return _instance
