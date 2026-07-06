"""Worker actors for the workflow fixture."""

from __future__ import annotations

from queueing import stage_one, stage_three, stage_two


class Worker:
    """Simple runtime actor with observable stage orchestration."""

    def __init__(self, strategy: str) -> None:
        self.strategy = strategy

    def execute(self, plan: list[str]) -> str:
        """Run ordered steps and return a traceable execution status."""
        step_outcomes = [self._run_step(plan)]
        return step_outcomes[0]

    def _run_step(self, plan: list[str]) -> str:
        """Private method intentionally captured and marked as internal."""
        ordered = [stage_one(plan), stage_two(plan), stage_three(plan)]
        return "+".join(ordered)
