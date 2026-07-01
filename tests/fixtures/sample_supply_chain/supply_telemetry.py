"""Small storage and transport helpers for observable fixture behavior."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import gettempdir
from typing import Any


def _fixture_root() -> Path:
    """Return a private scratch directory for this fixture."""
    root = Path(gettempdir()) / "skeleton-replay-fixtures"
    root.mkdir(parents=True, exist_ok=True)
    return root


def read_text(name: str) -> dict[str, Any]:
    """Read a JSON payload from a fixture-scoped location."""
    path = _fixture_root() / name
    if not path.exists():
        return {"recipient": "Ada Lovelace", "destination": "main-warehouse", "method": "standard"}
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw) if raw else {}


def write_text(name: str, payload: dict[str, Any] | str) -> bool:
    """Write JSON payloads into a fixture-scoped file."""
    path = _fixture_root() / name
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path.exists()


def post(payload: dict[str, Any] | str) -> str:
    """Mock a network-like dependency as a traceable call site."""
    return f"ack:{len(json.dumps(payload, sort_keys=True, default=str))}"
