"""Simple observable adapters for the orchestrated workflow fixture."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import gettempdir
from typing import Any


def _root() -> Path:
    """Return a private directory for fixture artefacts."""
    root = Path(gettempdir()) / "skeleton-replay-workflow"
    root.mkdir(parents=True, exist_ok=True)
    return root


def read_text(name: str) -> dict[str, Any]:
    """Read JSON-backed workflow config by name."""
    path = _root() / name
    if not path.exists():
        return {"strategy": "standard", "order_id": "PO-900", "priority": "medium"}
    body = path.read_text(encoding="utf-8")
    return json.loads(body) if body else {}


def get(endpoint: str) -> dict[str, Any]:
    """Mock a network GET call for observable outbound interaction."""
    return {"endpoint": endpoint, "status": "ok"}


def write_text(name: str, payload: dict[str, Any]) -> str:
    """Persist a JSON event for replayable proof points."""
    path = _root() / name
    encoded = json.dumps(payload, sort_keys=True)
    path.write_text(encoded, encoding="utf-8")
    return encoded
