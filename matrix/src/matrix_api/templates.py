from __future__ import annotations

from matrix_common.errors import TemplateNotFoundError
from matrix_common.messages import escape_html

# Templates are defined here in source — no user-supplied template strings allowed.
# Each entry is (plain_text_template, html_template).
# Values are escaped before substitution.

_TEMPLATES: dict[str, tuple[str, str]] = {
    "elastic_pq_warning": (
        "Elastic PQ warning: {cluster} pipeline {pipeline} queue is {pq_size_gb} GB",
        "<strong>Elastic PQ warning</strong>: {cluster} pipeline <code>{pipeline}</code> queue is <strong>{pq_size_gb} GB</strong>",
    ),
    "device_discovered": (
        "New device discovered: {hostname} ({ip}) — {vendor}",
        "New device discovered: <strong>{hostname}</strong> ({ip}) — {vendor}",
    ),
    "service_down": (
        "Service down: {service} on {host}",
        "<strong>Service down</strong>: <code>{service}</code> on {host}",
    ),
    "service_up": (
        "Service restored: {service} on {host}",
        "<strong>Service restored</strong>: <code>{service}</code> on {host}",
    ),
    "scan_complete": (
        "Network scan complete: {network} — {discovered} devices found",
        "Network scan complete: <code>{network}</code> — <strong>{discovered}</strong> devices found",
    ),
}


def render(template: str, values: dict) -> tuple[str, str]:
    """Return (plain_body, html_body) with all values HTML-escaped."""
    if template not in _TEMPLATES:
        raise TemplateNotFoundError(template)
    plain_tmpl, html_tmpl = _TEMPLATES[template]
    safe = {k: escape_html(v) for k, v in values.items()}
    return plain_tmpl.format_map(safe), html_tmpl.format_map(safe)


def available() -> list[str]:
    return list(_TEMPLATES.keys())
