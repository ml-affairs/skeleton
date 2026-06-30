# Python API

## Status

Early design contract.

Skeleton's stable v0 interface is the CLI:

```bash
python -m skeleton_replay run path/to/script.py
```

The internals are already object-oriented, but most Python classes are not yet
promised as a long-term public API. This page names the current surfaces and the
API shape Skeleton should expose before a wider PyPI release.

## Current Importable Building Blocks

The current pipeline is:

```text
CliApplication
  -> RunCommand
    -> TargetScriptRunner
      -> RuntimeTracer
    -> SnapshotBuilder
    -> WorkflowNarrativeWriter
    -> HtmlReportWriter
```

These objects are useful for contributors and tests, but the application-facing
API should be smaller than the internal pipeline.

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

### `RuntimeTracer`

Installs `sys.setprofile()` and records project-local public call and return
events.

This is a low-level tracing boundary. It should remain importable for advanced
users eventually, but its direct API should not be the first thing most users
need.

## Intended Stable API

Before a broad PyPI release, Skeleton should expose a small public object that
wraps the pipeline without exposing CLI parsing details.

The likely shape is:

```python
from pathlib import Path

from skeleton_replay import TraceSession

result = TraceSession(project_root=Path(".")).run_script(
    Path("scripts/replay_checkout.py"),
    script_args=["--example-order", "A-100"],
)

print(result.trace_path)
print(result.snapshot_path)
print(result.workflow_path)
print(result.report_path)
```

The stable object should:

- run a script path
- accept script arguments
- accept output directory, include/exclude filters, and max-events
- optionally render and open HTML
- return typed artifact paths and basic metrics
- avoid exposing `argparse.Namespace`

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
- snapshot projection details used only by the HTML report
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
