from __future__ import annotations

import logging

from matrix_bridge.commands import CommandContext
from matrix_bridge.commands.run import configure_runner
from matrix_bridge.secrets import SecretsError, load_secrets

logger = logging.getLogger(__name__)


async def handle_reauth(ctx: CommandContext) -> None:
    """
    Force-reload SOPS secrets and hot-swap both the Matrix bot token and the
    Anthropic API key used by the Claude runner.  Reports what was updated.
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
        logger.info("Matrix bot token hot-swapped via /reauth")
    else:
        lines.append("Matrix bot token: unchanged")

    # Hot-swap Anthropic API key
    if secrets.anthropic_api_key:
        configure_runner(secrets.anthropic_api_key)
        lines.append("Claude API key: loaded from secrets")
        logger.info("Claude API key refreshed via /reauth")
    else:
        lines.append(
            "Claude API key: not set in secrets — Claude is using OAuth (~/.claude).\n"
            "To enable API key auth: add anthropic_api_key to the matrix_bridge secrets block.\n"
            "To fix an expired OAuth session: SSH to agent01 and run `claude login` as ppowell."
        )

    # Verify Matrix connectivity with the new token
    try:
        whoami = await ctx.client.whoami()
        bot_id = whoami.get("user_id", "unknown")
        lines.append(f"Matrix verify: OK (bot is {bot_id})")
    except Exception as exc:
        lines.append(f"Matrix verify: FAILED — {exc}")
        logger.error("Matrix verify failed after /reauth: %s", exc)

    await ctx.client.send_text(ctx.room_id, "\n".join(lines))
