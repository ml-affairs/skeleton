"""Sample app that materializes metadata dictionaries during setup."""

from __future__ import annotations

from boundaries import ContextLaneBoundary


def build_boundaries() -> list[ContextLaneBoundary]:
    """Create a small set of context lane boundaries."""
    return [
        ContextLaneBoundary(name="memory", id="lane-memory", kind="context", lane="summary", owner="memory", role="source", stage="setup", event_type="materialized", active=True),
        ContextLaneBoundary(name="retrieval", id="lane-retrieval", kind="context", lane="rag", owner="search", role="source", stage="setup", event_type="materialized", active=True),
        ContextLaneBoundary(name="tools", id="lane-tools", kind="context", lane="tooling", owner="interface", role="adapter", stage="setup", event_type="materialized", active=False),
        ContextLaneBoundary(name="persona", id="lane-persona", kind="context", lane="voice", owner="profile", role="policy", stage="setup", event_type="materialized", active=True),
        ContextLaneBoundary(name="safety", id="lane-safety", kind="context", lane="guardrails", owner="runtime", role="policy", stage="setup", event_type="materialized", active=True),
        ContextLaneBoundary(name="output", id="lane-output", kind="context", lane="response", owner="renderer", role="sink", stage="setup", event_type="materialized", active=True),
    ]


def main() -> list[dict[str, object]]:
    """Materialize setup metadata and return it for inspection."""
    boundaries = build_boundaries()
    return [boundary.payload() for boundary in boundaries]


if __name__ == "__main__":
    main()
