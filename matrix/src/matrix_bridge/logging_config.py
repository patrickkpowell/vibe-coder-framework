from __future__ import annotations

import logging
import sys


def configure_logging(service: str) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s [{service}] %(levelname)s %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("psycopg").setLevel(logging.WARNING)
