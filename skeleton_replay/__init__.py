"""Runtime architecture replay for Python applications."""

from __future__ import annotations

from typing import TYPE_CHECKING

from skeleton_replay.version import __version__

if TYPE_CHECKING:
    from skeleton_replay.session import InProcessTraceSession, TraceSession, TraceSessionResult, trace

__all__ = ["InProcessTraceSession", "TraceSession", "TraceSessionResult", "__version__", "trace"]


def __getattr__(name: str) -> object:
    """Load heavier public API objects only when callers request them."""
    if name in {"InProcessTraceSession", "TraceSession", "TraceSessionResult", "trace"}:
        from skeleton_replay.session import InProcessTraceSession, TraceSession, TraceSessionResult, trace

        exports = {
            "InProcessTraceSession": InProcessTraceSession,
            "TraceSession": TraceSession,
            "TraceSessionResult": TraceSessionResult,
            "trace": trace,
        }
        return exports[name]
    raise AttributeError(f"module 'skeleton_replay' has no attribute {name!r}")
