from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    _SKIP = frozenset(
        {
            "msg", "args", "exc_info", "exc_text", "stack_info",
            "lineno", "name", "levelname", "levelno", "pathname",
            "filename", "module", "funcName", "created", "msecs",
            "relativeCreated", "thread", "threadName", "processName",
            "process", "message",
        }
    )

    def __init__(self, service: str) -> None:
        super().__init__()
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        data: dict = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "service": self._service,
            "message": record.message,
        }
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in self._SKIP and not key.startswith("_"):
                data[key] = value
        return json.dumps(data, default=str)


def configure_logging(service: str = "matrix-mcp", level: int = logging.INFO) -> None:
    # Log to stderr so it never mixes with MCP STDIO JSON-RPC if that mode is used.
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_JsonFormatter(service))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
