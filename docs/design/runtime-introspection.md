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

Each callback receives a frame object. The current implementation handles only
`call` and `return` events because Skeleton is an architecture replay tool, not a
line-by-line debugger or performance profiler.

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
python -m skeleton run path/to/script.py
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

## Important Limitations

Skeleton should be honest about what this mechanism can and cannot know.

- `id()` is process-local and not stable across runs.
- Calls implemented in C or native extensions do not expose the same Python
  frames as normal Python functions.
- Dynamic dispatch is observed only when it happens. A class may define many
  methods, but the report should show the methods this run actually used.
- Static imports and runtime calls are different facts. A module can import
  something without calling it.
- Private methods are intentionally ignored in v0, so the replay is an
  architectural path, not a complete execution log.
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
