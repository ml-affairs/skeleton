"""Fixture showing multi-module orchestration and cross-actor collaboration."""

from orchestrated_telemetry import read_text
from orchestrator import WorkflowOrchestrator


def bootstrap() -> dict[str, str]:
    """Build a lightweight manifest and seed the execution path."""
    manifest = read_text("manifest.json")
    orchestrator = WorkflowOrchestrator(manifest["strategy"])
    result = orchestrator.run(manifest["order_id"])
    return {"order": manifest["order_id"], "result": result}


def main() -> str:
    """Entrypoint used by regression tests and demos."""
    data = bootstrap()
    return data["result"]


if __name__ == "__main__":
    print(main())
