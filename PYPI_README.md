# skeleton-replay

Skeleton is a developer-understanding tool, not a profiler. It runs a Python
script under a lightweight runtime tracer and turns the observed execution into
an interactive, replayable architecture map.

Core promise:

> Replay and visualise the living architecture of a Python application.

Package naming:

```text
Product name:  Skeleton
PyPI package:  skeleton-replay
Import name:   skeleton_replay
CLI command:   skeleton
Module entry:  python -m skeleton_replay
```

## What Skeleton Generates

Skeleton produces runtime evidence in four complementary forms:

| Artifact | Purpose |
| --- | --- |
| `trace.jsonl` | Ordered public call and return events. |
| `snapshot.json` | Graph-shaped modules, classes, functions, instances, and edges. |
| `workflow.md` | LLM-readable workflow evidence with stable event and node references. |
| `report.html` | Interactive visual replay for humans. |

By default, artifacts are written to:

```text
~/.skeleton/<application-name>/
  trace.jsonl
  snapshot.json
  workflow.md
  report.html
```

## Install

```bash
pip install skeleton-replay
```

## CLI Quickstart

```bash
skeleton run path/to/script.py
```

The module entrypoint is also available:

```bash
python -m skeleton_replay run path/to/script.py
```

Options:

```text
--project-root PATH   Root used to decide which files are project-local.
--out-dir PATH        Output directory. Defaults to ~/.skeleton/<application-name>.
--include PATTERN     Only trace matching relative paths or module names.
--exclude PATTERN     Exclude matching relative paths or module names.
--max-events N        Stop writing trace events after N events.
--no-html             Skip report.html generation and opening.
--no-open             Do not open report.html after generation.
```

## Python API

Use `TraceSession` when you want to generate Skeleton artifacts from Python
without shelling out to the CLI:

```python
from pathlib import Path

from skeleton_replay import TraceSession

result = TraceSession(
    project_root=Path("path/to/project"),
    out_dir=Path("path/to/project/.skeleton"),
).run_script("path/to/project/app.py")

print(result.report_path)
print(result.workflow_path)
```

The Python API writes the same `trace.jsonl`, `snapshot.json`, `workflow.md`,
and optional `report.html` artifacts as the CLI. Unlike the CLI, it does not
open the HTML report by default; pass `open_report=True` when that is wanted.

## What Gets Traced

Skeleton uses `sys.setprofile` and records Python `call` and `return` events
when all of these are true:

- The frame's file is under the project root.
- The file is not in ignored local infrastructure such as `.venv`, `.git`, or
  `.skeleton`.
- The callable name is public. Names beginning with `_` are ignored.

The trace identifies the module, class where practical, function or method,
caller, callee, instance identity where practical, call depth, event order,
timestamp, safe argument summaries, and safe return summaries.

## Safety Model

Skeleton records summaries, not full object contents.

- Primitive values are summarized and long strings are truncated.
- Containers show type, length, and a small preview.
- Objects show class name and run-local object identity only.
- Likely secret fields are redacted by name, including `password`, `token`,
  `secret`, `key`, `auth`, and `credential`.

## Scope

The first version is intentionally non-invasive. You do not add decorators or
modify application code. The runner wraps an existing script, traces only
project-local public functions and methods by default, and records safe
summaries of arguments and return values.

Skeleton currently runs a script path. That script can drive CLI workflows,
service objects, batch jobs, web-app internals, or library calls. The
application being traced does not need to be a CLI application, but v0 needs a
script entrypoint that exercises the behavior.

## Links

- Repository: https://github.com/ml-affairs/skeleton
- Issues: https://github.com/ml-affairs/skeleton/issues
- Python API docs: https://github.com/ml-affairs/skeleton/blob/main/docs/api/python-api.md
- Design principles: https://github.com/ml-affairs/skeleton/blob/main/docs/design/software-design-principles.md
- Runtime introspection model: https://github.com/ml-affairs/skeleton/blob/main/docs/design/runtime-introspection.md
- Changelog: https://github.com/ml-affairs/skeleton/blob/main/CHANGELOG.md
