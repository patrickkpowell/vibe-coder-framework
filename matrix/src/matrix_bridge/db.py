from __future__ import annotations

import logging
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row

from matrix_bridge.models import Message, Session, Task
from matrix_bridge.projects import ProjectManifest

logger = logging.getLogger(__name__)

_MIGRATIONS = """
ALTER TABLE matrix_bridge.projects
    ADD COLUMN IF NOT EXISTS root_path TEXT,
    ADD COLUMN IF NOT EXISTS default_branch TEXT DEFAULT 'main',
    ADD COLUMN IF NOT EXISTS notification_policy TEXT DEFAULT 'matrix-active-only',
    ADD COLUMN IF NOT EXISTS allowed_tools JSONB;

ALTER TABLE matrix_bridge.sessions
    ADD COLUMN IF NOT EXISTS loaded_skills JSONB,
    ADD COLUMN IF NOT EXISTS project_root_path TEXT,
    ADD COLUMN IF NOT EXISTS claude_session_id TEXT,
    ADD COLUMN IF NOT EXISTS active_transport TEXT DEFAULT 'matrix',
    ADD COLUMN IF NOT EXISTS last_prompt TEXT,
    ADD COLUMN IF NOT EXISTS summary TEXT,
    ADD COLUMN IF NOT EXISTS summary_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS usage_status TEXT;
"""

_SCHEMA = """
CREATE SCHEMA IF NOT EXISTS matrix_bridge;

CREATE TABLE IF NOT EXISTS matrix_bridge.sessions (
    session_id      TEXT PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    matrix_room_id  TEXT NOT NULL,
    matrix_user_id  TEXT NOT NULL,
    state           TEXT NOT NULL DEFAULT 'active',
    project_id      TEXT,
    project_name    TEXT
);

CREATE TABLE IF NOT EXISTS matrix_bridge.messages (
    id          BIGSERIAL PRIMARY KEY,
    session_id  TEXT NOT NULL,
    room_id     TEXT NOT NULL,
    event_id    TEXT NOT NULL UNIQUE,
    direction   TEXT NOT NULL,
    body        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS matrix_bridge.processed_events (
    event_id        TEXT PRIMARY KEY,
    processed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS matrix_bridge.sync_state (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matrix_bridge.projects (
    project_id      TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    matrix_room_id  TEXT,
    room_state      TEXT NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS matrix_bridge.tasks (
    task_id             TEXT PRIMARY KEY,
    session_id          TEXT NOT NULL,
    project_id          TEXT,
    state               TEXT NOT NULL DEFAULT 'active',
    prompt              TEXT NOT NULL,
    working_directory   TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS matrix_bridge.audit_events (
    id              BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type      TEXT NOT NULL,
    session_id      TEXT,
    room_id_hash    TEXT,
    matrix_user_id  TEXT,
    command         TEXT,
    detail          TEXT
);
"""


def _row_to_session(row: dict) -> Session:
    import json as _json

    loaded_skills = row.get("loaded_skills")
    if isinstance(loaded_skills, str):
        loaded_skills = _json.loads(loaded_skills)
    return Session(
        session_id=row["session_id"],
        matrix_room_id=row["matrix_room_id"],
        matrix_user_id=row["matrix_user_id"],
        state=row["state"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        project_id=row.get("project_id"),
        project_name=row.get("project_name"),
        project_root_path=row.get("project_root_path"),
        loaded_skills=loaded_skills,
        claude_session_id=row.get("claude_session_id"),
        active_transport=row.get("active_transport") or "matrix",
        last_prompt=row.get("last_prompt"),
        summary=row.get("summary"),
        summary_at=row.get("summary_at"),
        usage_status=row.get("usage_status"),
    )


def _row_to_task(row: dict) -> Task:
    return Task(
        task_id=row["task_id"],
        session_id=row["session_id"],
        project_id=row.get("project_id"),
        state=row["state"],
        prompt=row["prompt"],
        working_directory=row["working_directory"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class Database:
    def __init__(self, conn: psycopg.AsyncConnection) -> None:
        self._conn = conn

    @classmethod
    async def connect(cls, database_url: str) -> Database:
        conn = await psycopg.AsyncConnection.connect(
            database_url, row_factory=dict_row, autocommit=False
        )
        db = cls(conn)
        await db._migrate()
        return db

    async def close(self) -> None:
        await self._conn.close()

    async def _migrate(self) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(_SCHEMA)
            await cur.execute(_MIGRATIONS)
        await self._conn.commit()
        logger.info("matrix_bridge schema ready")

    # ------------------------------------------------------------------ dedup

    async def is_processed(self, event_id: str) -> bool:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM matrix_bridge.processed_events WHERE event_id = %s",
                (event_id,),
            )
            return await cur.fetchone() is not None

    async def mark_processed(self, event_id: str) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO matrix_bridge.processed_events (event_id) VALUES (%s)"
                " ON CONFLICT DO NOTHING",
                (event_id,),
            )
        await self._conn.commit()

    # ------------------------------------------------------------------ sync state

    async def get_sync_token(self) -> str | None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "SELECT value FROM matrix_bridge.sync_state WHERE key = 'next_batch'"
            )
            row = await cur.fetchone()
            return row["value"] if row else None

    async def save_sync_token(self, token: str) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO matrix_bridge.sync_state (key, value) VALUES ('next_batch', %s)"
                " ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (token,),
            )
        await self._conn.commit()

    # ------------------------------------------------------------------ sessions

    async def create_session(self, session: Session) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO matrix_bridge.sessions
                    (session_id, matrix_room_id, matrix_user_id, state, created_at, updated_at,
                     project_id, project_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session.session_id,
                    session.matrix_room_id,
                    session.matrix_user_id,
                    session.state,
                    session.created_at,
                    session.updated_at,
                    session.project_id,
                    session.project_name,
                ),
            )
        await self._conn.commit()

    async def get_active_session(self, room_id: str) -> Session | None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM matrix_bridge.sessions
                WHERE matrix_room_id = %s AND state = 'active'
                ORDER BY created_at DESC LIMIT 1
                """,
                (room_id,),
            )
            row = await cur.fetchone()
        if not row:
            return None
        return _row_to_session(row)

    async def list_sessions_all(self, limit: int = 10) -> list[Session]:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM matrix_bridge.sessions ORDER BY updated_at DESC LIMIT %s",
                (limit,),
            )
            rows = await cur.fetchall()
        return [_row_to_session(r) for r in rows]

    async def list_sessions(self, room_id: str, limit: int = 10) -> list[Session]:
        async with self._conn.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM matrix_bridge.sessions
                WHERE matrix_room_id = %s
                ORDER BY created_at DESC LIMIT %s
                """,
                (room_id, limit),
            )
            rows = await cur.fetchall()
        return [_row_to_session(r) for r in rows]

    async def touch_session(self, session_id: str) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "UPDATE matrix_bridge.sessions SET updated_at = %s WHERE session_id = %s",
                (datetime.now(timezone.utc), session_id),
            )
        await self._conn.commit()

    # ------------------------------------------------------------------ messages

    async def save_message(self, msg: Message) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO matrix_bridge.messages
                    (session_id, room_id, event_id, direction, body)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO NOTHING
                """,
                (msg.session_id, msg.room_id, msg.event_id, msg.direction, msg.body),
            )
        await self._conn.commit()

    async def set_claude_session_id(self, session_id: str, claude_session_id: str) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "UPDATE matrix_bridge.sessions SET claude_session_id = %s, updated_at = %s"
                " WHERE session_id = %s",
                (claude_session_id, datetime.now(timezone.utc), session_id),
            )
        await self._conn.commit()

    async def get_session_by_id(self, session_id: str) -> Session | None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM matrix_bridge.sessions WHERE session_id = %s",
                (session_id,),
            )
            row = await cur.fetchone()
        return _row_to_session(row) if row else None

    async def set_session_state(self, session_id: str, state: str) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "UPDATE matrix_bridge.sessions SET state = %s, updated_at = %s WHERE session_id = %s",
                (state, datetime.now(timezone.utc), session_id),
            )
        await self._conn.commit()

    async def archive_active_sessions(self, room_id: str) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "UPDATE matrix_bridge.sessions SET state = 'archived', updated_at = %s"
                " WHERE matrix_room_id = %s AND state = 'active'",
                (datetime.now(timezone.utc), room_id),
            )
        await self._conn.commit()

    async def save_last_prompt(self, session_id: str, prompt: str) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "UPDATE matrix_bridge.sessions SET last_prompt = %s, updated_at = %s WHERE session_id = %s",
                (prompt, datetime.now(timezone.utc), session_id),
            )
        await self._conn.commit()

    async def save_summary(self, session_id: str, summary: str) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "UPDATE matrix_bridge.sessions SET summary = %s, summary_at = %s, updated_at = %s WHERE session_id = %s",
                (summary, datetime.now(timezone.utc), datetime.now(timezone.utc), session_id),
            )
        await self._conn.commit()

    async def count_session_messages(self, session_id: str) -> int:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) AS cnt FROM matrix_bridge.messages WHERE session_id = %s",
                (session_id,),
            )
            row = await cur.fetchone()
        return row["cnt"] if row else 0

    async def set_session_project(
        self,
        session_id: str,
        project_id: str,
        project_name: str,
        project_root_path: str,
        loaded_skills: list[str],
    ) -> None:
        import json as _json
        async with self._conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE matrix_bridge.sessions
                SET project_id = %s, project_name = %s, project_root_path = %s,
                    loaded_skills = %s, updated_at = %s
                WHERE session_id = %s
                """,
                (
                    project_id,
                    project_name,
                    project_root_path,
                    _json.dumps(loaded_skills),
                    datetime.now(timezone.utc),
                    session_id,
                ),
            )
        await self._conn.commit()

    async def ping(self) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute("SELECT 1")

    # ------------------------------------------------------------------ audit

    async def write_audit_event(
        self,
        event_type: str,
        *,
        session_id: str | None = None,
        room_id: str | None = None,
        matrix_user_id: str | None = None,
        command: str | None = None,
        detail: str | None = None,
    ) -> None:
        import hashlib

        room_id_hash = (
            hashlib.sha256(room_id.encode()).hexdigest()[:12] if room_id else None
        )
        async with self._conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO matrix_bridge.audit_events
                    (event_type, session_id, room_id_hash, matrix_user_id, command, detail)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (event_type, session_id, room_id_hash, matrix_user_id, command, detail),
            )
        await self._conn.commit()

    # ------------------------------------------------------------------ transport

    async def set_session_transport(self, session_id: str, transport: str) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "UPDATE matrix_bridge.sessions SET active_transport = %s, updated_at = %s"
                " WHERE session_id = %s",
                (transport, datetime.now(timezone.utc), session_id),
            )
        await self._conn.commit()

    async def set_session_usage_status(self, session_id: str, status: str) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "UPDATE matrix_bridge.sessions SET usage_status = %s, updated_at = %s"
                " WHERE session_id = %s",
                (status, datetime.now(timezone.utc), session_id),
            )
        await self._conn.commit()

    # ------------------------------------------------------------------ tasks

    async def create_task(self, task: Task) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO matrix_bridge.tasks
                    (task_id, session_id, project_id, state, prompt, working_directory,
                     created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    task.task_id,
                    task.session_id,
                    task.project_id,
                    task.state,
                    task.prompt,
                    task.working_directory,
                    task.created_at,
                    task.updated_at,
                ),
            )
        await self._conn.commit()

    async def set_task_state(self, task_id: str, state: str) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "UPDATE matrix_bridge.tasks SET state = %s, updated_at = %s"
                " WHERE task_id = %s",
                (state, datetime.now(timezone.utc), task_id),
            )
        await self._conn.commit()

    async def get_paused_task(self, session_id: str) -> Task | None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM matrix_bridge.tasks
                WHERE session_id = %s AND state = 'paused_usage_expired'
                ORDER BY created_at DESC LIMIT 1
                """,
                (session_id,),
            )
            row = await cur.fetchone()
        return _row_to_task(row) if row else None

    # ------------------------------------------------------------------ projects

    async def list_projects(self) -> list[dict]:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM matrix_bridge.projects ORDER BY project_id"
            )
            return await cur.fetchall()

    async def upsert_project(self, manifest: ProjectManifest) -> None:
        import json as _json
        async with self._conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO matrix_bridge.projects
                    (project_id, name, matrix_room_id, root_path, default_branch,
                     notification_policy, allowed_tools)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (project_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    matrix_room_id = EXCLUDED.matrix_room_id,
                    root_path = EXCLUDED.root_path,
                    default_branch = EXCLUDED.default_branch,
                    notification_policy = EXCLUDED.notification_policy,
                    allowed_tools = EXCLUDED.allowed_tools
                """,
                (
                    manifest.project_id,
                    manifest.name,
                    manifest.matrix_room_id,
                    manifest.root_path,
                    manifest.default_branch,
                    manifest.notification_policy,
                    _json.dumps(manifest.allowed_tools),
                ),
            )
        await self._conn.commit()
