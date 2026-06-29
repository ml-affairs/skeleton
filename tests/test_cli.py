import json
from pathlib import Path

import pytest

from skeleton.cli import CliApplication, OutputPathResolver


def test_cli_run_writes_trace_snapshot_and_report(tmp_path: Path) -> None:
    # Given
    project_root = Path("tests/fixtures/sample_project").resolve()
    out_dir = tmp_path / ".skeleton"

    # When
    exit_code = CliApplication().run(
        [
            "run",
            "--color",
            "never",
            "--project-root",
            str(project_root),
            "--out-dir",
            str(out_dir),
            str(project_root / "app.py"),
        ]
    )

    # Then
    assert exit_code == 0
    assert (out_dir / "trace.jsonl").exists()
    assert (out_dir / "snapshot.json").exists()
    assert (out_dir / "workflow.md").exists()
    assert (out_dir / "report.html").exists()

    snapshot = json.loads((out_dir / "snapshot.json").read_text(encoding="utf-8"))
    assert snapshot["event_count"] > 0
    assert any(node["id"] == "function:app.main" for node in snapshot["nodes"])
    assert any(node["id"] == "function:service.Greeter.greet" for node in snapshot["nodes"])
    assert not any(node["id"] == "function:service.Greeter" for node in snapshot["nodes"])
    assert not any(node["id"] == "function:service.Greeter._format" for node in snapshot["nodes"])


def test_output_path_resolver_defaults_to_skeleton_home_application_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given
    skeleton_home = tmp_path / "home" / ".skeleton"
    project_root = Path("tests/fixtures/sample_project").resolve()
    monkeypatch.setenv("SKELETON_HOME", str(skeleton_home))

    # When
    out_dir = OutputPathResolver().resolve(project_root=project_root, requested_out_dir=None)

    # Then
    assert out_dir == skeleton_home / "sample_project"
