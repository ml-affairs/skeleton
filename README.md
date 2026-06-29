# skeleton

![Skeleton: replay and visualise the living architecture of your code.](https://raw.githubusercontent.com/ml-affairs/skeleton/main/docs/images/readme.png)

Skeleton is a developer-understanding tool, not a profiler. It runs a Python
script under a lightweight runtime tracer and turns the observed execution into
an interactive, replayable architecture map.

Core promise:

> Replay and visualise the living architecture of a Python application.

Skeleton produces runtime evidence in four complementary forms:

| Surface | Purpose |
| --- | --- |
| ![Trace icon](https://raw.githubusercontent.com/ml-affairs/skeleton/main/docs/images/product/trace.svg) `trace.jsonl` | Ordered public call and return events. |
| ![Snapshot icon](https://raw.githubusercontent.com/ml-affairs/skeleton/main/docs/images/product/snapshot.svg) `snapshot.json` | Graph-shaped modules, classes, functions, instances, and edges. |
| ![Workflow icon](https://raw.githubusercontent.com/ml-affairs/skeleton/main/docs/images/product/workflow.svg) `workflow.md` | LLM-readable workflow evidence with stable event and node references. |
| ![Replay icon](https://raw.githubusercontent.com/ml-affairs/skeleton/main/docs/images/product/replay.svg) `report.html` | Interactive visual replay for humans. |

## MVP workflow

```bash
python -m skeleton run path/to/script.py
```

Skeleton writes:

```text
.skeleton/
  trace.jsonl
  snapshot.json
  workflow.md
  report.html
```

The first version is intentionally non-invasive. You do not add decorators or
modify application code. The runner wraps an existing script, traces only
project-local public functions and methods by default, and records safe
summaries of arguments and return values.

`workflow.md` is a compact text explanation of the observed run. It is designed
for humans and LLMs: event ids, node ids, caller/callee relationships, safe
examples, and known trace gaps are written in a form that can be quoted and
reasoned over without scraping the HTML report.

## Install and develop

```bash
make setup
make check
```

Run locally from the checkout:

```bash
uv run python -m skeleton run examples/app.py
```

## CLI

```bash
python -m skeleton run [options] path/to/script.py [args...]
```

Options:

```text
--project-root PATH   Root used to decide which files are project-local.
--out-dir PATH        Output directory. Defaults to <project-root>/.skeleton.
--include PATTERN     Only trace matching relative paths or module names.
--exclude PATTERN     Exclude matching relative paths or module names.
--max-events N        Stop writing trace events after N events.
--no-html             Generate trace.jsonl and snapshot.json only.
```

## What gets traced

Skeleton uses `sys.setprofile` and records Python `call` and `return` events
when all of these are true:

- The frame's file is under the project root.
- The file is not in ignored local infrastructure such as `.venv`, `.git`, or
  `.skeleton`.
- The callable name is public. Names beginning with `_` are ignored.

The trace identifies the module, class where practical, function or method,
caller, callee, instance identity where practical, call depth, event order,
timestamp, safe argument summaries, and safe return summaries.

## Event schema

Each line in `.skeleton/trace.jsonl` is a JSON object:

```json
{
  "schema_version": 1,
  "event_type": "call",
  "order": 0,
  "timestamp": 1782740000.0,
  "depth": 0,
  "caller": null,
  "callee": {
    "module": "app",
    "class_name": null,
    "function": "main",
    "qualified_name": "app.main",
    "file": "/project/app.py",
    "line": 10,
    "node_id": "function:app.main",
    "instance_id": null
  },
  "args": {}
}
```

Return events use the same endpoint shape and include `return_value`.

## Safety model

Skeleton records summaries, not full object contents.

- Strings are truncated.
- Containers include type, length, and a small preview.
- Objects include only class name and object id.
- Argument or mapping names containing `password`, `token`, `secret`, `key`,
  `auth`, or `credential` are redacted.

This is not a debugger replacement and not a performance profiler. It is a
runtime architecture replay tool for understanding how a codebase behaves.
