from __future__ import annotations

import re

# Dangerous substrings that must not be forwarded to Claude unreviewed.
# Checked case-insensitively against the raw prompt text.
_DANGEROUS_SUBSTRINGS: tuple[str, ...] = (
    "rm -rf /",
    "rm -rf ~",
    "rm -rf $home",
    "terraform apply",
    "kubectl delete",
    "helm uninstall",
    "aws iam",
    "aws secretsmanager get-secret-value",
    "op item get",
    "security find-generic-password",
)

# Patterns that look like secrets in Claude output — redacted before sending to Matrix.
_REDACT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"), "[ANTHROPIC-KEY-REDACTED]"),
    (re.compile(r"(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}"), "[GITHUB-TOKEN-REDACTED]"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[AWS-KEY-REDACTED]"),
    (re.compile(r"AGE-SECRET-KEY-[A-Z0-9]+"), "[AGE-KEY-REDACTED]"),
    (re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "[JWT-REDACTED]"),
    (re.compile(r"Bearer\s+[A-Za-z0-9._\-]{20,}", re.IGNORECASE), "[BEARER-TOKEN-REDACTED]"),
)


def check_dangerous_prompt(prompt: str) -> str | None:
    """Return the matched dangerous pattern, or None if the prompt is clean."""
    lower = prompt.lower()
    for substring in _DANGEROUS_SUBSTRINGS:
        if substring.lower() in lower:
            return substring
    return None


def redact_secrets(text: str) -> str:
    """Replace known secret patterns in text with safe placeholders."""
    for pattern, replacement in _REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text
