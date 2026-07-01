"""Workflow orchestration fixture for runtime replay scenarios."""

from __future__ import annotations

from orchestrated_telemetry import get, write_text
from pipeline import build_plan, summarize
from workers import Worker


class WorkflowOrchestrator:
    """Coordinates planning, execution, and reporting."""

    def __init__(self, strategy: str) -> None:
        self.strategy = strategy
        self.worker = Worker(strategy)

    def run(self, order_id: str) -> str:
        """Run an execution plan and return a compact status label."""
        plan = build_plan(order_id, self.strategy)
        status = self.worker.execute(plan)
        snapshot = get("/workflow/status")
        summary = summarize(order_id=order_id, status=status, response=snapshot)
        write_text("workflow-status.json", summary)
        return summary["result"]
