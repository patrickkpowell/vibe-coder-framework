from __future__ import annotations

import json
import re

from .errors import DestinationNotFoundError

_ROOM_ID_RE = re.compile(r"^![a-zA-Z0-9._~/-]+:.+$")


class DestinationResolver:
    def __init__(self, mapping: dict[str, str]) -> None:
        for name, room_id in mapping.items():
            if not _ROOM_ID_RE.match(room_id):
                raise ValueError(
                    f"Invalid Matrix room ID for destination {name!r}: {room_id!r}"
                )
        self._mapping = mapping

    @classmethod
    def from_json(cls, json_str: str) -> DestinationResolver:
        try:
            mapping = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ValueError(f"MATRIX_DESTINATIONS_JSON is not valid JSON: {exc}") from exc
        if not isinstance(mapping, dict):
            raise ValueError("MATRIX_DESTINATIONS_JSON must be a JSON object")
        return cls(mapping)

    def resolve(self, destination: str) -> str:
        if destination not in self._mapping:
            raise DestinationNotFoundError(destination)
        return self._mapping[destination]

    def names(self) -> list[str]:
        return list(self._mapping.keys())

    def has(self, destination: str) -> bool:
        return destination in self._mapping
