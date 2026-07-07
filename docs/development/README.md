# Development Guide

This document is the current development guide for Skeleton. It replaces older
planning notes that mixed completed release work with future integrations.

Skeleton is already a published PyPI package. The active development posture is:
keep the Python engine dependency-light and non-invasive, preserve runtime
evidence as the product boundary, and add integrations only when they feed the
same trace, snapshot, workflow, quality, report, and session artifacts.

## Current Product Surface

Installed package:

```bash
pip install skeleton-replay
```

Primary commands:

```bash
skeleton run path/to/script.py
skeleton pytest -- tests/test_checkout.py -q
python -m skeleton_replay run path/to/script.py
python -m skeleton_replay pytest -- tests/test_checkout.py -q
```

Primary Python API:

```python
from skeleton_replay import TraceSession

result = TraceSession(project_root=".").run_script("scripts/demo.py")
```

Generated artifacts:

- `trace.jsonl`
- `snapshot.json`
- `workflow.md`
- `quality.json`
- `architecture_quality.md`
- `session.json`
- optional `report.html`

`session.json` is the integration entrypoint for IDEs and automation. It records
the command, invocation, target, generated artifact paths, metrics, exit status,
target error, and Skeleton version for each run.

## Development Workflow

Use the Makefile and `uv`:

```bash
make setup
make test
make check
uv build
```

Before handoff or release, run:

```bash
git diff --check
make check
uv build
```

`make check` runs Ruff, formatting checks, mypy, pytest, and coverage.

Test and source ownership should mirror the package layout where practical:

- runtime tracing under `skeleton_replay/runtime`
- snapshot, quality, roles, and static analysis under `skeleton_replay/analysis`
- report and workflow rendering under `skeleton_replay/reporting`
- CLI, console, output paths, artifacts, and session manifest under
  `skeleton_replay/interface`
- safety/redaction under `skeleton_replay/safety`

## Release Workflow

Release commits should keep version metadata and changelog aligned in one
change. Update:

- `pyproject.toml`
- `skeleton_replay/version.py`
- `uv.lock`
- `CHANGELOG.md`

Then run:

```bash
uv lock
git diff --check
make check
uv build
```

Publishing is tag-driven. Push a `v*` tag matching the package version:

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin main
git push origin vX.Y.Z
```

The GitHub Publish workflow verifies the tag matches `pyproject.toml`, runs
`make check`, builds distributions, and publishes to PyPI through Trusted
Publishing. Create GitHub release notes from the matching `CHANGELOG.md`
section.

## Integration Roadmap

### `run-module`

Add module execution for package-first projects:

```bash
skeleton run-module my_app.cli -- run-demo
```

Expected shape:

- resolve project root and `sys.path`
- execute with `runpy.run_module(module_name, run_name="__main__")`
- preserve module arguments in `sys.argv`
- emit the same artifact set as `skeleton run`

### Pytest Evolution

The first pytest integration has landed as `skeleton pytest` and
`TraceSession.run_pytest()`. Future work should build on that seam rather than
replacing it prematurely.

Useful next slices:

- one report per selected test when tracing a suite
- mark-based scenario selection
- pytest-native options such as `--skeleton` and `--skeleton-out-dir`
- CI artifact attachment
- snapshot comparison between commits

Parallel pytest execution needs separate trace outputs before it can be
supported safely.

### Live Web Request Tracing

Live request tracing should start with explicit in-process boundaries rather
than external process attach.

Preferred first shapes:

```python
app.add_middleware(SkeletonTraceMiddleware, project_root=".")
```

or:

```python
with SkeletonTraceSession(project_root=".").capture("checkout-request"):
    response = client.post("/checkout", json={"order_id": "A-100"})
```

Risks to solve before shipping:

- concurrent request isolation
- async call stacks
- request/header/body secret redaction
- avoiding profiler leakage across unrelated requests

### PyCharm Plugin

The PyCharm plugin lives in the separate private repository
`ml-affairs/skeleton-replay-plugin`.

The plugin should stay a thin IDE frontend over the PyPI package. It should:

- call the installed `skeleton-replay` engine through the configured project
  interpreter
- pass explicit project root and output directory arguments
- read `session.json` as the primary discovery contract
- embed or open `report.html`
- show workflow, quality, artifacts, and run logs
- eventually bridge report node selections back to PyCharm source navigation

The plugin must not reimplement tracing.

## Design References

Design doctrine lives outside this development guide:

- `docs/design/README.md`

Architecture decisions are recorded under `docs/architecture/`. Add a new ADR
when a change creates or changes a durable product boundary, artifact contract,
runtime model, integration seam, or report interpretation rule.
