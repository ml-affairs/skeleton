# Missing Integration Plans

## Status

Planning document.

Skeleton currently traces Python scripts. That is enough for the MVP because any
application can create a small scenario script that imports real code and drives
one workflow. The next integration seams should make that less manual.

## `python -m package.module`

### What It Means

Python can run an importable module as a program:

```bash
python -m package.module arg1 arg2
```

Examples:

```bash
python -m http.server 8000
python -m pytest tests/test_checkout.py
python -m my_app.cli run-demo
```

The module is found on `sys.path` and executed as `__main__`. Today Skeleton
expects a file path:

```bash
skeleton run scripts/demo.py
```

It does not yet accept:

```bash
skeleton run-module my_app.cli -- run-demo
```

### Why It Matters

Many Python projects expose behavior through package modules instead of script
files. Supporting this makes Skeleton feel natural for modern package layouts.

### Likely Shape

```bash
skeleton run-module my_app.cli -- run-demo
```

Implementation direction:

- add a `run-module` command
- resolve project root and `sys.path`
- use `runpy.run_module(module_name, run_name="__main__")`
- preserve module arguments in `sys.argv`
- write the same trace, snapshot, workflow, and report artifacts

## Pytest Tracing

### What It Means

The current first slice lets users trace tests or selected test scenarios
without creating separate runner scripts:

Current usage:

```bash
skeleton pytest --out-dir .skeleton/checkout -- tests/test_checkout.py -q
```

This is deliberately a Skeleton-owned CLI command rather than a pytest plugin
hook. It keeps the non-invasive runner seam intact, preserves pytest's exit
code, and emits the same `trace.jsonl`, `snapshot.json`, `workflow.md`,
`quality.json`, `architecture_quality.md`, and optional `report.html` artifacts
as script tracing.

Later plugin-style usage may add:

```bash
pytest tests/test_checkout.py --skeleton --skeleton-out-dir .skeleton/checkout
```

### Why It Matters

Tests already encode business workflows. A pytest integration would let teams
turn existing acceptance tests, service tests, or integration tests into
architecture replays.

### Likely Shape

Landed first slice:

- `skeleton pytest [Skeleton options] -- [pytest args...]`
- trace one full pytest session, selected test file, or selected test node
- emit artifacts after pytest finishes
- preserve pytest's exit code
- write useful partial artifacts for failing tests

Later slices:

- one report per test
- mark-based scenario selection
- pytest-native options such as `--skeleton`, `--skeleton-out-dir`, and
  `--skeleton-project-root`
- compare snapshots between commits
- attach generated reports to CI artifacts

### Risks

- pytest itself is a large Python application; filters must keep third-party and
  pytest internals out of the graph by default
- failed tests should still write useful partial artifacts
- parallel test execution requires separate trace outputs

## Live Web Request Tracing

### What It Means

Tracing a live web request means Skeleton would trace one request handled by an
already running server, such as FastAPI, Flask, Django, or Starlette.

Today Skeleton runs a script from start to finish. It does not attach to an
existing process and it does not know which request should be traced.

### Why It Matters

Large applications often express workflows as HTTP requests, queue jobs, or
background tasks. A developer may want to click a UI button or send one API
request and then replay the architecture path.

### Possible Shapes

Middleware mode:

```python
app.add_middleware(SkeletonTraceMiddleware, project_root=".")
```

Context-manager mode:

```python
with SkeletonTraceSession(project_root=".").capture("checkout-request"):
    response = client.post("/checkout", json={"order_id": "A-100"})
```

External attach mode is a later, harder problem and should not be the first
slice.

### Risks

- concurrent requests need trace isolation
- async call stacks need careful handling
- secrets in request bodies, headers, cookies, and environment variables need
  stronger redaction policy
- server tracing should avoid global profiler leakage across unrelated requests

## PyCharm Plugin

### Can Skeleton Become One?

Yes. A PyCharm plugin is feasible, but it should be a thin IDE frontend over the
Skeleton CLI/API rather than a separate tracer.

The plugin should not reimplement tracing. It should call the installed
`skeleton` package, pass the selected run configuration, and open or embed the
generated report.

The Python package writes `session.json` beside each artifact set. The plugin
should use that manifest as its primary discovery contract, then render the
linked `report.html`, `workflow.md`, `architecture_quality.md`, `snapshot.json`,
and `trace.jsonl` artifacts in the workbench.

### Useful First Features

- right-click a Python file and choose "Run with Skeleton"
- right-click a pytest test and choose "Replay with Skeleton"
- choose project root and output directory
- show links to `session.json`, `trace.jsonl`, `snapshot.json`, `workflow.md`,
  `architecture_quality.md`, and `report.html`
- open `report.html` in PyCharm's browser panel when available
- show CLI command used for reproducibility

### Technical Shape

PyCharm plugins are JVM/Kotlin/Java plugins. A first implementation would likely
be a separate repository or package that:

- defines an IDE action
- reads the current module/content root
- invokes `skeleton run ...`, `python -m skeleton_replay run ...`, or future Python API through the
  configured interpreter
- watches the generated artifact directory and reads `session.json`
- opens the HTML report

### Risks

- interpreter selection matters in PyCharm projects
- virtualenv and uv environments need detection
- Windows path handling must be tested
- plugin signing and JetBrains Marketplace publishing are separate release
  tasks

## Recommended Sequence

1. Stabilize public Python API (`TraceSession.run_script`).
2. Add `run-module` support.
3. Add pytest tracing MVP.
4. Add PyCharm plugin prototype using CLI/API.
5. Add live request tracing as middleware/context-manager, not process attach.

This order keeps the non-invasive runner seam intact while opening practical
entrypoints for real projects.
