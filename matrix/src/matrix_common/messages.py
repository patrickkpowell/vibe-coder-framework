from __future__ import annotations

import html as _html


def build_text_payload(body: str, severity: str = "info") -> dict:
    return {"msgtype": "m.text", "body": body}


def build_formatted_payload(body: str, formatted_body: str, severity: str = "info") -> dict:
    return {
        "msgtype": "m.text",
        "body": body,
        "format": "org.matrix.custom.html",
        "formatted_body": formatted_body,
    }


def escape_html(value: object) -> str:
    return _html.escape(str(value))


SEVERITY_LABELS: dict[str, str] = {
    "debug": "[DEBUG]",
    "info": "[INFO]",
    "warning": "[WARNING]",
    "error": "[ERROR]",
    "critical": "[CRITICAL]",
}
