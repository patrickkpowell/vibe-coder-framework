from __future__ import annotations

import asyncio
import json
import logging
import os
import pwd
from dataclasses import dataclass
from typing import Any

from matrix_bridge.safety import redact_secrets

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 300
MAX_RESPONSE_CHARS = 3800
DEFAULT_MODEL = "claude-sonnet-4-6"

_PATH = "/usr/local/bin:/usr/bin:/bin"

_USAGE_LIMIT_PATTERNS = (
    "usage limit",
    "rate limit",
    "overloaded",
    "too many requests",
    "claude ai usage limit",
)

_AUTH_ERROR_PATTERNS = (
    "authentication_error",
    "invalid_api_key",
    "invalid x-api-key",
    "invalid authentication",
    "401",
)


@dataclass
class RunResult:
    text: str
    session_id: str | None
    usage_limit_hit: bool = False
    auth_error_hit: bool = False


def _drop_to_ppowell() -> None:
    """Drop container-root privileges to ppowell (uid 1000) before exec'ing claude."""
    try:
        pw = pwd.getpwnam("ppowell")
        uid, gid = pw.pw_uid, pw.pw_gid
    except KeyError:
        uid, gid = 1000, 1000
    os.setgroups([gid])
    os.setgid(gid)
    os.setuid(uid)


def _is_usage_limit(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in _USAGE_LIMIT_PATTERNS)


def _is_auth_error(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in _AUTH_ERROR_PATTERNS)


class ClaudeRunner:
    def __init__(
        self,
        claude_bin: str = "claude",
        home_dir: str = "/home/ppowell",
        model: str = DEFAULT_MODEL,
        api_key: str = "",
    ) -> None:
        self._claude_bin = claude_bin
        self._home_dir = home_dir
        self._model = model
        self._api_key = api_key

    def update_api_key(self, api_key: str) -> None:
        self._api_key = api_key
        logger.info("Claude API key updated")

    async def run(
        self,
        message: str,
        cwd: str,
        claude_session_id: str | None,
        allowed_tools: list[str] | None = None,
    ) -> RunResult:
        """Run claude --print with the given message."""
        cmd = [
            self._claude_bin,
            "--print",
            "--output-format", "stream-json",
            "--verbose",
            "--model", self._model,
            "--dangerously-skip-permissions",
        ]
        if claude_session_id:
            cmd += ["--resume", claude_session_id]
        if allowed_tools:
            cmd += ["--allowedTools", ",".join(allowed_tools)]

        env = {**os.environ, "HOME": self._home_dir, "PATH": _PATH}
        if self._api_key:
            env["ANTHROPIC_API_KEY"] = self._api_key

        logger.info(
            "Running claude",
            extra={"cwd": cwd, "resume": claude_session_id or "new", "model": self._model},
        )

        preexec = _drop_to_ppowell if os.getuid() == 0 else None

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
                preexec_fn=preexec,
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(message.encode()),
                    timeout=TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                proc.kill()
                logger.warning("claude timed out after %ds", TIMEOUT_SECONDS)
                return RunResult(redact_secrets("Request timed out after 5 minutes."), claude_session_id)
        except FileNotFoundError:
            logger.error("claude binary not found: %s", self._claude_bin)
            return RunResult(
                "Claude CLI is not installed. Run: npm install -g @anthropic-ai/claude-code",
                None,
            )
        except Exception as exc:
            logger.exception("Failed to spawn claude: %s", exc)
            return RunResult(f"Failed to run Claude: {exc}", claude_session_id)

        stdout = stdout_b.decode(errors="replace")
        stderr = stderr_b.decode(errors="replace")

        # Session not found — clear stored ID and retry as a new session
        if proc.returncode != 0 and "No conversation found" in stderr and claude_session_id:
            logger.warning("Stored claude session %s not found — starting new session", claude_session_id)
            return await self.run(message, cwd, None, allowed_tools)

        if proc.returncode != 0 and not stdout.strip():
            logger.error("claude exited %d: %s", proc.returncode, stderr[:500])
            text = f"Claude exited with error (code {proc.returncode})."
            if _is_auth_error(stderr):
                logger.error("Claude authentication error detected — run /reauth or `claude login` on agent01")
                return RunResult(text, claude_session_id, auth_error_hit=True)
            return RunResult(text, claude_session_id, usage_limit_hit=_is_usage_limit(stderr))

        return self._parse(stdout, claude_session_id)

    def _parse(self, raw: str, fallback_session: str | None) -> RunResult:
        response: str | None = None
        session_id: str | None = fallback_session
        usage_limit_hit = False
        auth_error_hit = False

        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError:
                continue

            if sid := event.get("session_id"):
                session_id = sid

            if event.get("type") == "result":
                if event.get("subtype") == "success":
                    response = event.get("result", "").strip()
                else:
                    err = event.get("error", "Unknown error")
                    response = f"Error: {err}"
                    if _is_auth_error(err):
                        auth_error_hit = True
                        logger.error("Claude authentication error — run /reauth or `claude login` on agent01")
                    elif _is_usage_limit(err):
                        usage_limit_hit = True

        if response is None:
            # Fall back: assemble from assistant message blocks
            parts: list[str] = []
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "assistant":
                    for block in event.get("message", {}).get("content", []):
                        if block.get("type") == "text":
                            parts.append(block["text"])
            response = "".join(parts).strip() or "(No response)"

        return RunResult(
            redact_secrets(response),
            session_id,
            usage_limit_hit=usage_limit_hit,
            auth_error_hit=auth_error_hit,
        )


def split_response(text: str) -> list[str]:
    """Split a long response into Matrix-sized chunks at newline boundaries."""
    if len(text) <= MAX_RESPONSE_CHARS:
        return [text]
    chunks: list[str] = []
    while text:
        if len(text) <= MAX_RESPONSE_CHARS:
            chunks.append(text)
            break
        chunk = text[:MAX_RESPONSE_CHARS]
        split = chunk.rfind("\n")
        if split > MAX_RESPONSE_CHARS // 2:
            chunk = text[:split]
        chunks.append(chunk)
        text = text[len(chunk):].lstrip("\n")
    return chunks
