from __future__ import annotations

import json
import logging
import os
import time

from matrix_bridge.commands import CommandContext
from matrix_bridge.commands.run import configure_runner, get_runner
from matrix_bridge.secrets import SecretsError, load_secrets

logger = logging.getLogger(__name__)

_CREDS_FILE = os.path.expanduser("~/.claude/.credentials.json")


def _oauth_status() -> str:
    """Return a human-readable status string for the OAuth credentials on disk."""
    try:
        creds = json.loads(open(_CREDS_FILE).read())
        tok = creds.get("claudeAiOauth", {})
        if not tok:
            return "no OAuth credentials found (~/.claude/.credentials.json missing or empty)"
        expires_ms = tok.get("expiresAt", 0)
        days_left = (expires_ms / 1000 - time.time()) / 86400
        if days_left < 0:
            return f"access token expired {abs(days_left):.1f}d ago (will auto-refresh on next command)"
        return f"access token valid ({days_left:.1f}d remaining)"
    except FileNotFoundError:
        return "~/.claude/.credentials.json not found — run !login to authenticate"
    except Exception as exc:
        return f"could not read credentials: {exc}"


async def handle_reauth(ctx: CommandContext) -> None:
    """
    Force-reload SOPS secrets and hot-swap both the Matrix bot token and the
    Anthropic API key used by the Claude runner.  Reports what was updated.
    In OAuth mode, verifies the token is healthy by running a test command.
    """
    await ctx.client.send_text(ctx.room_id, "Reloading secrets…")

    try:
        secrets = load_secrets(force_reload=True)
    except SecretsError as exc:
        logger.error("Reauth failed: %s", exc)
        await ctx.client.send_text(
            ctx.room_id,
            f"Failed to reload secrets: {exc}\n"
            f"Check SECRETS_FILE and SOPS_AGE_KEY_FILE are correctly mounted.",
        )
        return

    lines: list[str] = []

    # Hot-swap Matrix bot token
    new_token = secrets.bot_access_token
    old_token = ctx.config.matrix_bot_access_token  # type: ignore[attr-defined]
    if new_token != old_token:
        ctx.config.matrix_bot_access_token = new_token  # type: ignore[attr-defined]
        ctx.client.update_token(new_token)
        lines.append("Matrix bot token: updated")
        logger.info("Matrix bot token hot-swapped via !reauth")
    else:
        lines.append("Matrix bot token: unchanged")

    # Hot-swap Anthropic API key or verify OAuth
    if secrets.anthropic_api_key:
        configure_runner(secrets.anthropic_api_key)
        lines.append("Claude API key: loaded from secrets")
        logger.info("Claude API key refreshed via !reauth")
    else:
        # OAuth mode — run a minimal test to trigger auto-refresh and verify health
        lines.append(f"Claude auth: OAuth mode — {_oauth_status()}")
        lines.append("Claude OAuth: verifying…")
        await ctx.client.send_text(ctx.room_id, "\n".join(lines))
        lines.clear()

        runner = get_runner()
        home = os.environ.get("HOME", "/home/ppowell")
        cwd = home
        result = await runner.run(
            'echo "ping"',
            cwd=cwd,
            claude_session_id=None,
        )
        if result.auth_error_hit:
            lines.append(
                "Claude OAuth: FAILED — token refresh did not work.\n"
                "Run !login to re-authenticate via browser."
            )
            logger.error("OAuth verify failed after !reauth")
        else:
            lines.append("Claude OAuth: OK (token verified / refreshed)")
            logger.info("OAuth token verified via !reauth")

    # Verify Matrix connectivity with the new token
    try:
        whoami = await ctx.client.whoami()
        bot_id = whoami.get("user_id", "unknown")
        lines.append(f"Matrix verify: OK (bot is {bot_id})")
    except Exception as exc:
        lines.append(f"Matrix verify: FAILED — {exc}")
        logger.error("Matrix verify failed after !reauth: %s", exc)

    await ctx.client.send_text(ctx.room_id, "\n".join(lines))
