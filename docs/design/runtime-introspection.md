# Runtime Introspection

## Status

Draft.

## Why Skeleton Can Work Without Decorators

Skeleton relies on Python runtime introspection rather than application
instrumentation. The target application does not need decorators because Python
already exposes function entry, function return, stack frames, module globals,
local variables, code metadata, and object identity while the program runs.

The important idea is simple:

> Skeleton watches real runtime calls and then projects them into an architecture
> model.

It does not infer everything from static source. Static analysis is used for
light context, such as approximate LOC and known symbols. Runtime events are the
source of truth for the replay.

## The Runtime Hook

Skeleton installs a profile callback with `sys.setprofile()`.

Python calls that callback when the interpreter observes events such as:

- `call`: Python is entering a function or method.
- `return`: Python is returning from a function or method.
- `c_call`: Python is about to call selected C-level functions such as
  `print`, `open`, or `sqlite3.connect`.
- `c_return` / `c_exception`: a selected C-level resource call has completed or
  raised.

Each callback receives a frame object. Skeleton handles normal Python
`call`/`return` events for project-local public functions and methods. It also
handles a narrow allow-list of C-level resource calls only when project-local
code is already active on the trace stack. That makes I/O visible without
turning the report into a standard-library or third-party dependency trace.

This hook is standard library Python. It is the same family of runtime machinery
used by profilers and debuggers, but Skeleton uses it for architectural evidence
rather than timing.

## The Frame Object

A frame is Python's live execution record for a function call. Skeleton reads a
small, controlled set of fields:

- `frame.f_code`: code metadata for the running function.
- `frame.f_code.co_filename`: source file path.
- `frame.f_code.co_name`: function name.
- `frame.f_code.co_firstlineno`: first line of the function.
- `frame.f_globals["__name__"]`: module name when available.
- `frame.f_locals`: local variables for the call.

This is enough to build an endpoint:

```text
module: service
class: Greeter
function: greet
qualified name: service.Greeter.greet
file: /project/service.py
line: 5
```

The frame is also how Skeleton reads arguments. It uses `inspect.getargvalues()`
to map argument names to live values, then immediately passes those values
through the safe summariser.

## How Instance Identity Is Found

Python instance methods are ordinary functions called with the instance as the
first argument. By convention that argument is named `self`.

When a profiled frame contains `self` in `frame.f_locals`, Skeleton treats the
call as an instance method:

```python
instance = frame.f_locals["self"]
class_name = type(instance).__name__
instance_id = f"{module}.{class_name}@0x{id(instance):x}"
```

That is the mechanism behind report labels such as:

```text
service.Greeter@0x104e950a0
```

This is not a persistent object id. It is a run-local identity for one Python
process. The same logical object in another run will have a different `id()`.
That is acceptable for v0 because replay explains one observed execution.

Class methods are handled separately. If a frame has `cls` and `inspect.isclass`
confirms it is a class object, Skeleton can record a class name, but there is no
instance id because no object instance handled the call.

## Why Classes Are Metadata In The Report

A class definition describes a type. A runtime instance does the work.

For architecture replay, Skeleton therefore treats:

- module as an ownership shell
- object instance as the runtime actor
- method as behavior observed on that instance
- class name as metadata attached to the instance and method

This avoids showing both `Greeter` and `Greeter@0x...` as competing actors. The
graph should answer "what object handled this call?" before it answers "where
was the class defined?"

The snapshot may still contain class nodes because static metadata is useful for
schemas, future comparisons, and documentation. The report projection is more
opinionated: it shows runtime actors first.

## How Caller And Callee Are Connected

The profile callback receives one event at a time, so Skeleton maintains a
simple stack of traced endpoints:

- On `call`, the top of the stack is the caller, and the new frame is the
  callee.
- On `return`, Skeleton pops the returning endpoint and the new top of the stack
  is the caller receiving the return value.

That produces two complementary edges in the report:

- call edge: caller to callee
- return edge: callee back to caller

The return edge is useful because it shows where control and summarized values
flow back during replay.

## How The Runner Is Non-Invasive

Skeleton runs a target script with `runpy.run_path()` and temporarily adjusts:

- `sys.argv`, so the script sees its normal command-line arguments
- `sys.path`, so local imports resolve as they would for a direct script run
- `sys.setprofile`, so only the wrapped execution is traced

After the target run, Skeleton restores `sys.argv`, `sys.path`, and removes the
profile callback.

This is the first non-invasive seam. The user runs:

```bash
python -m skeleton_replay run path/to/script.py
```

The application source remains unchanged.

## Why Third-Party Code Is Not Traced By Default

The profile hook can see a lot of Python calls. Without filtering, a report would
quickly become a dependency trace rather than an application architecture map.

Skeleton filters by:

- project root
- include patterns
- exclude patterns
- public names only
- ignored local infrastructure such as `.venv`, `.git`, and `.skeleton`

This keeps the graph focused on project-local architecture.

## How Resource Boundaries Are Seen

Some important architecture evidence does not appear as a project-local Python
frame. `print()`, `open()`, SQLite connection methods, and many socket
operations cross into C-level runtime code. Skeleton watches selected
`c_call`/`c_return` profile events while a traced project-local function or
method is active.

The resource classifier is deliberately small. It can currently emit endpoint
types such as:

```text
resource.stdout
resource.filesystem
resource.database
external.service
```

Filesystem, stdout, and database endpoints are typed as `resource` with a
category such as `stdout`, `file`, or `db`; the report projects them as external
I/O cylinders. Network endpoints are typed as `external_service` with category
`network`; the report projects them as diamonds because external services are
architectural collaborators, not resource cylinders. The specific operation,
such as `print`, `mkdir`, or `connect`, stays in the safe event evidence. The
caller remains the project-local actor, for example:

```text
order_repository.SqliteOrderRepository.save -> resource.database
notification_adapter.ConsoleNotifier.announce -> resource.stdout
payment_gateway.PaymentGatewayClient.charge -> external.service
```

This distinction matters: local application methods keep their own architectural
identity, while external resources become explicit boundary evidence.

## Safety Boundaries

The frame gives access to live values. Skeleton deliberately does not serialize
those values.

Instead it records summaries:

- primitives are copied in small form
- strings are truncated
- containers include type, length, and a small preview
- objects include class name and object id only
- likely secret names are redacted

The raw objects are discarded after summarisation.

## Structured Return Aggregation

Some applications materialize many small metadata dictionaries during setup or
inspection. In the raw trace these are still ordinary call and return events,
and `trace.jsonl` keeps them in chronological order.

The snapshot, workflow narrative, and HTML report add a presentation layer over
those raw events. When the same callable repeatedly returns compatible safe
dictionary previews with mostly scalar values, Skeleton emits
`structured_return_groups` in `snapshot.json`. The detection model is generic:
it uses observed return shape, key overlap, scalar summaries, repeated records,
and low call complexity. Names such as `payload`, `to_dict`, `metadata`, or
`schema` are weak hints only; an arbitrary function name can still group when
the observed data matches, and a `payload()` method with real child calls or
resource behavior stays in the normal graph.

Groups can promote semantic fields such as `name`, `id`, `key`, `kind`, `type`,
`lane`, `owner`, `role`, `stage`, `event_type`, and `active` when those keys are
present in safe previews. Optional `pyproject.toml` settings can tune record
thresholds, key overlap, labels, and row display fields without requiring
application decorators or trace-schema changes.

```toml
[tool.skeleton.structured_returns]
enabled = true
min_records = 3
min_key_overlap = 0.75
collapse_by_default = true
label_fields = ["name", "id", "key", "kind", "type", "lane", "owner", "role", "stage", "event_type"]

[tool.skeleton.structured_returns.groups]
"*.PromptContextLaneBoundary.payload" = "Prompt context lane catalog"

[tool.skeleton.display_labels]
"*.PromptContextLaneBoundary" = "{lane}"
```

The report renders these derived groups as cards and tables by default, with
expandable raw event evidence. Exported trace windows include overlapping
structured-return groups so LLM and debugging review get both the concise table
and the exact call/return evidence. This keeps catalog or manifest
materialization from dominating the primary architecture graph with repeated
instance-method labels, while preserving exact raw event order, caller/callee
names, timestamps, arguments, return summaries, and object ids for debugging.

Structured return groups should be read as derived presentation evidence, not
data loss and not necessarily workflow actions.

## Important Limitations

Skeleton should be honest about what this mechanism can and cannot know.

- `id()` is process-local and not stable across runs.
- Calls implemented in C or native extensions do not expose the same Python
  frames as normal Python functions. Skeleton only captures the small resource
  allow-list described above.
- Dynamic dispatch is observed only when it happens. A class may define many
  methods, but the report should show the methods this run actually used.
- Static imports and runtime calls are different facts. A module can import
  something without calling it.
- Private/internal methods are captured, marked as internal, and can be hidden
  in the report to focus on public interfaces.
- Async functions, generators, descriptors, monkey patching, and metaprogramming
  can produce surprising frame shapes. Skeleton should improve these cases with
  tests as they become product requirements.

## Product Implication

This runtime seam is the reason Skeleton can become an architecture replay tool
rather than a decorator framework.

The tool can watch existing code, summarize evidence safely, and then build:

- a chronological trace
- a graph snapshot
- an LLM-readable workflow explanation
- an interactive report where runtime actors appear as they are observed

The long-term product challenge is not collecting every possible runtime fact.
It is projecting the facts into concepts that developers can reason about:
modules, instances, public methods, call direction, return direction, ownership,
boundary roles, and external resources.
