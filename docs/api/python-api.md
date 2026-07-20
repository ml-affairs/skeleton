# Python API

## Status

Available in v0.1.0.

Skeleton's primary interface is still the CLI:

```bash
python -m skeleton_replay run path/to/script.py
python -m skeleton_replay pytest -- tests/test_checkout.py -q
```

The public Python API is `trace()` and `TraceSession`. Most lower-level classes
remain contributor-facing implementation details.

## Stable Public API

### `trace()`

Traces Python code that is already running in the current process and writes the
same artifact set as the CLI. This is the preferred API when pytest fixtures,
monkeypatches, dependency injection, or an existing harness must remain active
during the trace.

```python
from pathlib import Path

from skeleton_replay import trace

with trace(
    project_root=Path("."),
    label="Monitor",
    include=("src/",),
    max_events=10_000,
) as session:
    Monitor({}).run()

print(session.result.trace_path)
print(session.result.snapshot_path)
print(session.result.workflow_path)
print(session.result.session_path)
print(session.result.report_path)
```

When `out_dir` is omitted, callable traces write to
`<project-root>/.skeleton/<label>/latest/`. Explicit `out_dir`,
`SKELETON_OUT_DIR`, and `SKELETON_HOME` still take precedence.

If the traced block raises, Skeleton still writes the artifacts collected up to
the exception and records the failure on `session.result`; the original
exception is not suppressed.

### `skeleton_trace`

Installing Skeleton also registers a pytest fixture:

```python
def test_monitor(skeleton_trace):
    with skeleton_trace("Monitor") as session:
        Monitor({}).run()

    assert session.result.succeeded
```

The fixture is a thin wrapper around `trace()` and preserves active pytest
fixtures and monkeypatches because the traced code runs inside the current test
process.

### `TraceSession`

Runs a Python script under Skeleton and writes the same artifacts as the CLI.

```python
from pathlib import Path

from skeleton_replay import TraceSession

result = TraceSession(
    project_root=Path("."),
    out_dir=Path(".skeleton"),
    include=("src/",),
    exclude=("tests/",),
    max_events=10_000,
).run_script(
    Path("scripts/replay_checkout.py"),
    script_args=["--example-order", "A-100"],
)

print(result.trace_path)
print(result.snapshot_path)
print(result.workflow_path)
print(result.session_path)
print(result.report_path)
```

The same session can trace an existing pytest invocation:

```python
from pathlib import Path

from skeleton_replay import TraceSession

result = TraceSession(
    project_root=Path("."),
).run_pytest(["tests/test_checkout.py", "-q"])

print(result.target_exit_code)
print(result.report_path)
```

The same session can also create an in-process context manager:

```python
from skeleton_replay import TraceSession

configured_session = TraceSession(project_root=".", html_enabled=False)

with configured_session.trace("Monitor") as session:
    Monitor({}).run()

print(session.result.event_count)
```

Constructor fields:

| Field | Purpose |
| --- | --- |
| `project_root` | Root used to decide which frames are project-local. |
| `out_dir` | Artifact directory. Uses the same default resolution as the CLI when omitted. `run_script()` defaults to `<script-parent>/.skeleton/<script-stem>/latest/`. `run_pytest()` preserves selected pytest node ids, for example `<test-dir>/.skeleton/<file-stem>/<test-node>/latest/`; whole-file and whole-directory runs use `file/latest/` and `directory/latest/` sentinels. `trace()` defaults to `<project-root>/.skeleton/<label>/latest/`. |
| `include` | Optional path or module patterns to include. |
| `exclude` | Optional path or module patterns to exclude. |
| `max_events` | Optional cap on written trace events. |
| `html_enabled` | Generate `report.html` when true. |
| `open_report` | Open `report.html` in the default browser when true. Defaults to false for library callers. |

### `TraceSessionResult`

Returned by `TraceSession.run_script`, `TraceSession.run_pytest`, and
`trace(...).result`.

| Field | Meaning |
| --- | --- |
| `trace_path` | Path to `trace.jsonl`. |
| `snapshot_path` | Path to `snapshot.json`. |
| `workflow_path` | Path to `workflow.md`. |
| `session_path` | Path to `session.json`, the stable session manifest for IDEs and automation. |
| `report_path` | Path to `report.html`, or `None` when HTML is disabled. |
| `report_opened` | Whether browser opening was attempted and accepted. |
| `event_count` | Number of captured trace events. |
| `node_count` | Number of snapshot nodes. |
| `edge_count` | Number of observed runtime call edges. |
| `target_exit_code` | Exit code from the traced script or pytest invocation. |
| `target_error` | String summary when the traced script or pytest runner raised an exception. |
| `succeeded` | Convenience property for `target_exit_code == 0`. |

## Current Importable Building Blocks

The current pipeline is:

```text
CliApplication
  -> RunCommand
    -> TargetScriptRunner
      -> RuntimeTracer
  -> PytestCommand
    -> TargetPytestRunner
      -> RuntimeTracer
  -> trace()/TraceSession.trace()
    -> RuntimeTracer
    -> SnapshotBuilder
    -> WorkflowNarrativeWriter
    -> HtmlReportWriter
```

These objects are useful for contributors and tests, but the application-facing
API is intentionally smaller than the internal pipeline.

## IDE Integration Manifest

Every CLI and Python API run writes `session.json` next to the other artifacts.
IDE integrations should discover a completed run through this manifest instead
of reconstructing paths from CLI output.

The manifest currently includes:

- `schema_version`
- `skeleton_version`
- `command` and reproducible `invocation`
- `project_root`
- traced `target`
- artifact paths for `trace`, `snapshot`, `workflow`, `quality`,
  `quality_markdown`, optional `report`, and `session`
- `metrics` for events, nodes, and runtime edges
- `target_exit_code`, `target_error`, and `report_opened`

The manifest is the preferred contract for PyCharm and other IDE surfaces. Raw
trace and snapshot details can still evolve while the manifest gives tools a
stable place to find generated artifacts and the run outcome.

### `CliApplication`

Owns command parsing and dispatch for the `skeleton` executable.

Use this only when embedding the current CLI behavior:

```python
from skeleton_replay.cli import CliApplication

exit_code = CliApplication().run(["run", "--no-open", "scripts/demo.py"])
```

### `RunCommand`

Coordinates one `skeleton run` invocation after arguments have been parsed.

This is primarily a CLI command object, not the intended user-facing library
entrypoint.

### `TargetScriptRunner`

Runs a Python script under `RuntimeTracer` with adjusted `sys.argv` and
`sys.path`.

This currently powers all target execution.

### `TargetPytestRunner`

Runs pytest in-process under `RuntimeTracer`, preserving pytest's exit code
while writing the same replay artifacts. Importing pytest is delayed until the
runner is used, so Skeleton's runtime package still has no hard pytest
dependency for script-only users.

### `RuntimeTracer`

Installs `sys.setprofile()` and records project-local call and return events.
Private/internal callables are captured and marked for report filtering.

This is a low-level tracing boundary. Prefer `trace()` for application code that
needs a complete artifact set.

## What Is Not Public Yet

Do not treat these as stable API contracts yet:

- trace JSON schema beyond `schema_version: 1`
- derived snapshot presentation details used by workflow and HTML reports
- report JavaScript internals
- exact output styling or graph layout behavior
- private helpers inside runtime, analysis, safety, interface, or reporting

## Design Rule

The public API should describe user intent, not Skeleton's implementation
sequence. Prefer:

```python
TraceSession(project_root=".").run_script("scripts/demo.py")
```

over asking users to assemble:

```python
RunCommand(...)
TargetScriptRunner(...)
SnapshotBuilder(...)
HtmlReportWriter(...)
```
