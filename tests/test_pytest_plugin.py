import json

import pytest

pytest_plugins = ("pytester",)


def test_skeleton_trace_fixture_traces_live_test_with_active_fixtures(pytester: pytest.Pytester) -> None:
    # Given
    pytester.makepyfile(
        fixture_app="""
class Monitor:
    def __init__(self, clock):
        self.clock = clock

    def run(self):
        return self.clock()
"""
    )
    pytester.makepyfile(
        test_monitor="""
from pathlib import Path

import time

from fixture_app import Monitor


def test_monitor_uses_monkeypatched_clock(monkeypatch, skeleton_trace):
    monkeypatch.setattr(time, "time", lambda: 123.0)

    with skeleton_trace("Monitor", html_enabled=False) as session:
        assert Monitor(time.time).run() == 123.0

    assert session.result.event_count > 0
    assert session.result.session_path == Path.cwd() / ".skeleton" / "Monitor" / "latest" / "session.json"
"""
    )

    # When
    result = pytester.runpytest("-q")

    # Then
    result.assert_outcomes(passed=1)
    session_path = pytester.path / ".skeleton" / "Monitor" / "latest" / "session.json"
    session_manifest = json.loads(session_path.read_text(encoding="utf-8"))
    assert session_manifest["command"] == "trace"
    assert session_manifest["target"] == {"args": [], "kind": "callable", "label": "Monitor"}
    assert session_manifest["metrics"]["events"] > 0
