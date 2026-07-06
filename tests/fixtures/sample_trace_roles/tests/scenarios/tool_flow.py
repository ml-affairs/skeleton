"""Script-style scenario with import-time setup and shared test helpers."""

from app.service import Service
from tests.helpers.factory import build_service


def compute_import_payload() -> dict[str, object]:
    """Compute import-time metadata before the scenario entrypoint starts."""
    return {"phase": "setup", "service": Service.__name__}


IMPORT_PAYLOAD = compute_import_payload()


def run_scenario() -> str:
    """Run the scenario entrypoint."""
    service = build_service("tool-flow")
    return service.run()


if __name__ == "__main__":
    run_scenario()
