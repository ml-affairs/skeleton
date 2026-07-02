"""Safe value summaries for trace events."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

SECRET_KEYWORDS = ("password", "token", "secret", "key", "auth", "credential")
JsonValue = dict[str, Any]


@dataclass(frozen=True)
class ValueSummariser:
    """Creates JSON-safe summaries of runtime values without walking objects."""

    max_string: int = 120
    max_container_items: int = 12
    max_depth: int = 2
    secret_keywords: tuple[str, ...] = SECRET_KEYWORDS

    def summarise_arguments(self, values: Mapping[str, object]) -> dict[str, JsonValue]:
        """Summarise argument values by name, applying key-based redaction."""
        return {name: self.summarise_value(value, name=name) for name, value in values.items()}

    def summarise_value(self, value: object, *, name: str | None = None, depth: int = 0) -> JsonValue:
        """Return a small JSON-safe description of a runtime value."""
        if self.is_secret_name(name):
            return {"type": "redacted", "reason": "sensitive-name"}

        if value is None:
            return {"type": "NoneType", "value": None}
        if isinstance(value, bool):
            return {"type": "bool", "value": value}
        if isinstance(value, int | float):
            return {"type": type(value).__name__, "value": value}
        if isinstance(value, str):
            truncated = len(value) > self.max_string
            return {
                "type": "str",
                "value": value[: self.max_string],
                "len": len(value),
                "truncated": truncated,
            }
        if isinstance(value, bytes):
            return {"type": "bytes", "len": len(value)}
        if depth >= self.max_depth:
            return {"type": type(value).__name__, "summary": "max-depth"}
        if isinstance(value, Mapping):
            return self._summarise_mapping(value, depth=depth)
        if isinstance(value, set | frozenset):
            return self._summarise_sequence(tuple(value), depth=depth, type_name=type(value).__name__)
        if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
            return self._summarise_sequence(value, depth=depth, type_name=type(value).__name__)

        value_type = type(value)
        return {
            "type": f"{value_type.__module__}.{value_type.__qualname__}",
            "object_id": f"0x{id(value):x}",
        }

    def is_secret_name(self, name: str | None) -> bool:
        """Return whether an argument or mapping key name looks sensitive."""
        if not name:
            return False
        lowered = name.lower()
        return any(keyword in lowered for keyword in self.secret_keywords)

    def _summarise_mapping(self, value: Mapping[object, object], *, depth: int) -> JsonValue:
        preview = []
        for index, (item_key, item_value) in enumerate(value.items()):
            if index >= self.max_container_items:
                break
            key_summary = self.summarise_value(item_key, depth=depth + 1)
            key_name = item_key if isinstance(item_key, str) else None
            preview.append(
                {
                    "key": key_summary,
                    "value": self.summarise_value(item_value, name=key_name, depth=depth + 1),
                }
            )
        return {"type": type(value).__name__, "len": len(value), "preview": preview}

    def _summarise_sequence(self, value: Sequence[object], *, depth: int, type_name: str) -> JsonValue:
        preview = [self.summarise_value(item, depth=depth + 1) for index, item in enumerate(value) if index < self.max_container_items]
        return {"type": type_name, "len": len(value), "preview": preview}
