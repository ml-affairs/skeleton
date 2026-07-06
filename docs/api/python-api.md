# Python API

## Status

Available in v0.1.0.

Skeleton's primary interface is still the CLI:

```bash
python -m skeleton_replay run path/to/script.py
python -m skeleton_replay pytest -- tests/test_checkout.py -q
```

The public Python API is `TraceSession`. Most lower-level classes remain
contributor-facing implementation details.

## Stable Public API

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

Constructor fields:

| Field | Purpose |
| --- | --- |
| `project_root` | Root used to decide which frames are project-local. |
| `out_dir` | Artifact directory. Uses the same default resolution as the CLI when omitted. `run_script()` defaults to `<script-parent>/.skeleton/<script-stem>/latest/`. `run_pytest()` preserves selected pytest node ids, for example `<test-dir>/.skeleton/<file-stem>/<test-node>/latest/`; whole-file and whole-directory runs use `file/latest/` and `directory/latest/` sentinels. |
| `include` | Optional path or module patterns to include. |
| `exclude` | Optional path or module patterns to exclude. |
| `max_events` | Optional cap on written trace events. |
| `html_enabled` | Generate `report.html` when true. |
| `open_report` | Open `report.html` in the default browser when true. Defaults to false for library callers. |

### `TraceSessionResult`

Returned by `TraceSession.run_script` and `TraceSession.run_pytest`.

| Field | Meaning |
| --- | --- |
| `trace_path` | Path to `trace.jsonl`. |
| `snapshot_path` | Path to `snapshot.json`. |
| `workflow_path` | Path to `workflow.md`. |
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
    -> SnapshotBuilder
    -> WorkflowNarrativeWriter
    -> HtmlReportWriter
```

These objects are useful for contributors and tests, but the application-facing
API is intentionally smaller than the internal pipeline.

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

This is a low-level tracing boundary. It should remain importable for advanced
users eventually, but its direct API should not be the first thing most users
need.

## Planned Callable API

A second seam should run one Python callable directly:

```python
from skeleton_replay import TraceSession

def checkout_scenario() -> None:
    service = build_checkout_service()
    service.reserve_order("A-100")

TraceSession(project_root=".").run_callable(checkout_scenario)
```

This would help notebooks, tests, and programmatic documentation examples. It
requires careful handling of `sys.path`, working directory, exceptions, and
callable names, so it should be added deliberately with tests.

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
