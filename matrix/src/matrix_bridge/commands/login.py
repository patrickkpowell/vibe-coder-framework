"""
!login — headless PKCE OAuth re-authentication for the Claude CLI.

Usage:
  !login          Generate an auth URL and send it via Matrix.
  !login <url>    Complete the flow by pasting the redirect callback URL.
  !login cancel   Cancel a pending login.

Flow:
  1. Bridge generates PKCE code_verifier / code_challenge.
  2. Sends the claude.ai authorization URL via Matrix.
  3. User opens the URL in any browser, authorizes.
  4. Browser redirects to https://platform.claude.com/oauth/code/callback?code=...
  5. User copies the full redirect URL (or just the `code=` value) and sends it back.
  6. Bridge exchanges the code for tokens via a Node.js subprocess (bypasses Cloudflare).
  7. Writes new tokens to ~/.claude/.credentials.json.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import secrets
import tempfile
import time
import urllib.parse
from dataclasses import dataclass

from matrix_bridge.commands import CommandContext

logger = logging.getLogger(__name__)

# OAuth constants (from claude CLI binary)
_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
_AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
_TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
_MANUAL_REDIRECT_URL = "https://platform.claude.com/oauth/code/callback"
_SCOPES = "user:inference user:profile"

_CREDS_FILE = os.path.expanduser("~/.claude/.credentials.json")

# In-memory pending login state keyed by room_id
_pending: dict[str, _PendingLogin] = {}

# Token exchange script — runs in Node.js to use the correct TLS stack
_EXCHANGE_SCRIPT = """
const https = require('https');
const fs = require('fs');

const [,, code, codeVerifier, credsFile] = process.argv;

const body = JSON.stringify({
  grant_type: 'authorization_code',
  code,
  redirect_uri: '{REDIRECT_URI}',
  client_id: '{CLIENT_ID}',
  code_verifier: codeVerifier,
});

const req = https.request({
  hostname: 'platform.claude.com',
  path: '/v1/oauth/token',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(body),
    'User-Agent': 'claude-code/1.0 node/22',
    'Accept': 'application/json',
  },
}, (res) => {
  let data = '';
  res.on('data', d => data += d);
  res.on('end', () => {
    if (res.statusCode === 200) {
      const tokens = JSON.parse(data);
      let existing = {};
      try { existing = JSON.parse(fs.readFileSync(credsFile, 'utf8')); } catch {}
      const prev = existing.claudeAiOauth || {};
      existing.claudeAiOauth = {
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token || prev.refreshToken || '',
        expiresAt: Date.now() + (tokens.expires_in || 86400) * 1000,
        scopes: tokens.scope ? tokens.scope.split(' ') : (prev.scopes || ['user:inference', 'user:profile']),
        subscriptionType: prev.subscriptionType || 'pro',
        rateLimitTier: prev.rateLimitTier || 'default_claude_ai',
      };
      fs.writeFileSync(credsFile, JSON.stringify(existing, null, 2));
      console.log('OK');
    } else {
      process.stderr.write('HTTP ' + res.statusCode + ': ' + data + '\\n');
      process.exit(1);
    }
  });
});

req.on('error', e => { process.stderr.write(e.message + '\\n'); process.exit(1); });
req.write(body);
req.end();
""".replace("{REDIRECT_URI}", _MANUAL_REDIRECT_URL).replace("{CLIENT_ID}", _CLIENT_ID)


@dataclass
class _PendingLogin:
    code_verifier: str
    state: str
    expires_at: float  # unix timestamp


def _build_auth_url(code_challenge: str, state: str) -> str:
    params = {
        "client_id": _CLIENT_ID,
        "response_type": "code",
        "redirect_uri": _MANUAL_REDIRECT_URL,
        "scope": _SCOPES,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    return f"{_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def _extract_code(text: str) -> tuple[str | None, str | None]:
    """Return (code, state) from a callback URL or bare code value."""
    text = text.strip()
    if "?" in text or "&" in text:
        try:
            parsed = urllib.parse.urlparse(text)
            qs = urllib.parse.parse_qs(parsed.query)
            code = (qs.get("code") or [""])[0]
            state = (qs.get("state") or [""])[0]
            return (code or None, state or None)
        except Exception:
            pass
    # bare code
    if text and " " not in text and len(text) > 10:
        return text, None
    return None, None


async def _exchange_code(code: str, code_verifier: str) -> str | None:
    """Run the Node.js token exchange script. Returns None on success, error string on failure."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False, prefix="claude_oauth_"
    ) as f:
        f.write(_EXCHANGE_SCRIPT)
        script_path = f.name

    try:
        proc = await asyncio.create_subprocess_exec(
            "node", script_path, code, code_verifier, _CREDS_FILE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=20)
        if proc.returncode == 0:
            return None
        err = stderr_b.decode(errors="replace").strip()
        return err or f"node exited {proc.returncode}"
    except asyncio.TimeoutError:
        return "token exchange timed out"
    except FileNotFoundError:
        return "node not found in PATH"
    except Exception as exc:
        return str(exc)
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass


async def handle_login(ctx: CommandContext) -> None:
    args = ctx.args

    # !login cancel
    if args and args[0].lower() == "cancel":
        _pending.pop(ctx.room_id, None)
        await ctx.client.send_text(ctx.room_id, "Login cancelled.")
        return

    # !login <code_or_url> — complete a pending flow
    if args:
        pending = _pending.get(ctx.room_id)
        if not pending:
            await ctx.client.send_text(
                ctx.room_id,
                "No pending login. Run !login first to start the flow."
            )
            return
        if time.time() > pending.expires_at:
            _pending.pop(ctx.room_id, None)
            await ctx.client.send_text(
                ctx.room_id,
                "Login session expired. Run !login to start a new one."
            )
            return

        code, state = _extract_code(" ".join(args))
        if not code:
            await ctx.client.send_text(
                ctx.room_id,
                "Could not find an authorization code in that input.\n"
                "Paste the full redirect URL or just the code= value."
            )
            return

        if state and state != pending.state:
            await ctx.client.send_text(
                ctx.room_id,
                "State mismatch — this code doesn't match the pending login. Try !login again."
            )
            return

        await ctx.client.send_text(ctx.room_id, "Exchanging authorization code…")
        err = await _exchange_code(code, pending.code_verifier)
        _pending.pop(ctx.room_id, None)

        if err:
            logger.error("OAuth token exchange failed: %s", err)
            await ctx.client.send_text(ctx.room_id, f"Token exchange failed: {err}")
            return

        logger.info("OAuth re-authentication completed via !login")
        await ctx.client.send_text(
            ctx.room_id,
            "Authentication successful — ~/.claude/.credentials.json updated.\n"
            "Run !reauth to verify."
        )
        return

    # !login (no args) — start the PKCE flow
    _pending.pop(ctx.room_id, None)  # clear any stale state

    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)

    _pending[ctx.room_id] = _PendingLogin(
        code_verifier=code_verifier,
        state=state,
        expires_at=time.time() + 600,  # 10 min window
    )

    auth_url = _build_auth_url(code_challenge, state)

    await ctx.client.send_text(
        ctx.room_id,
        "Open this URL in a browser to authenticate:\n"
        f"{auth_url}\n\n"
        "After authorizing, your browser will redirect to a URL like:\n"
        "https://platform.claude.com/oauth/code/callback?code=...&state=...\n\n"
        "Copy that full URL (or just the code= value) and reply with:\n"
        "!login <url_or_code>\n\n"
        "This link expires in 10 minutes. Run !login cancel to abort."
    )
