"""Pytest fixture integration for in-process Skeleton tracing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from skeleton_replay.session import InProcessTraceSession


@dataclass(frozen=True)
class SkeletonTraceFixture:
    """Factory for tracing one live pytest scenario."""

    project_root: Path

    def __call__(
        self,
        label: str,
        *,
        project_root: Path | str | None = None,
        out_dir: Path | str | None = None,
        include: tuple[str, ...] = (),
        exclude: tuple[str, ...] = (),
        max_events: int | None = None,
        html_enabled: bool = True,
        open_report: bool = False,
    ) -> InProcessTraceSession:
        """Return a trace context manager for code running inside this pytest process."""
        from skeleton_replay.session import trace

        return trace(
            project_root=project_root or self.project_root,
            label=label,
            out_dir=out_dir,
            include=include,
            exclude=exclude,
            max_events=max_events,
            html_enabled=html_enabled,
            open_report=open_report,
        )


@pytest.fixture
def skeleton_trace() -> SkeletonTraceFixture:
    """Trace a live pytest scenario while preserving active fixtures and monkeypatches."""
    return SkeletonTraceFixture(project_root=Path.cwd())
