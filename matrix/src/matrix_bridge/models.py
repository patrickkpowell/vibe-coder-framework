from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Session:
    session_id: str
    matrix_room_id: str
    matrix_user_id: str
    state: str
    created_at: datetime
    updated_at: datetime
    project_id: str | None = None
    project_name: str | None = None
    project_root_path: str | None = None
    loaded_skills: list[str] | None = None
    claude_session_id: str | None = None
    active_transport: str = "matrix"
    last_prompt: str | None = None
    summary: str | None = None
    summary_at: datetime | None = None
    usage_status: str | None = None  # usage_ok | usage_expired | usage_unknown


@dataclass
class Task:
    task_id: str
    session_id: str
    prompt: str
    working_directory: str
    state: str  # active | paused_usage_expired | done | cancelled
    created_at: datetime
    updated_at: datetime
    project_id: str | None = None


@dataclass
class Message:
    session_id: str
    room_id: str
    event_id: str
    direction: str  # 'inbound' | 'outbound'
    body: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: int | None = None
