# AGENTS.md

Guidance for agents and contributors working in this repository.

## Project Direction

Skeleton is a non-invasive developer-understanding tool. It wraps existing Python
entrypoints, captures project-local execution, and turns observed runtime
relationships into an interactive architecture replay.

- The runner seam is the first product boundary. Do not require decorators or
  application-code changes in v0.
- Treat Skeleton as an architecture replay tool, not as a profiler, debugger, or
  tracing vendor SDK.
- Prefer correctness, clarity, and extensibility over clever tracing tricks.
- Keep dependencies minimal. The runtime package should remain standard-library
  only unless a dependency has a clear product reason.
- Design Skeleton as a PyPI-quality library from the start. Treat package
  metadata, typed public APIs, documentation, examples, generated assets, and
  first-run ergonomics as part of the product, not as release chores to bolt on
  later.
- Think through the full user experience, from the logo and README to CLI
  errors, schema docs, examples, and generated reports. The implementation
  should feel like a polished library, not a script collection.

## Tooling

- Use `uv` for dependency management and command execution.
- Use the Makefile as the task interface.
- Use `pytest` for tests.
- Use `mypy` in strict mode. Python in this repository must be typed.
- Use Ruff for linting, formatting, import sorting, docstring rules, and
  annotation rules.
- Keep Ruff line length at `220`; do not rewrap to 80 or 100 columns.
- Run `make check` after code changes when feasible.

## Typing And Documentation

- Every Python module should be typed. Public functions, public methods,
  dataclasses, protocols, and constructors must have explicit annotations.
- Keep `mypy --strict` passing. Do not silence type errors unless the boundary is
  genuinely untypable and the ignore is narrow, explained, and close to the
  line it affects.
- Public modules, classes, functions, methods, and dataclasses need docstrings.
  Treat docstrings as library documentation for users and contributors, not as
  filler comments.
- Private helpers should have docstrings when their behavior is non-obvious,
  security-sensitive, schema-sensitive, or part of a tricky runtime boundary.
- Prefer precise domain names over abbreviated names. Good names and types
  should make most inline comments unnecessary.
- Generated schemas, trace formats, CLI behavior, and report interactions must
  be documented when they become public or semi-public contracts.

## Code Ownership

- Treat Python as an implementation language, not as permission for procedural
  sprawl. Code should have explicit owners, narrow public methods, and boring
  dependency flow.
- Design and code in an object-oriented way where behavior has state,
  collaborators, lifecycle, policy, I/O, or invariants. Keep procedural glue
  thin and local.
- Prefer owned objects for stateful behavior, lifecycle, collaborators,
  invariants, I/O, policy decisions, validation flows, trace writes, and report
  generation boundaries.
- Do not add broad loose-function APIs. Before adding or moving a function,
  classify it as one of:
  - actor method: behavior with state, collaborators, lifecycle, policy, I/O,
    tracing, validation, or orchestration decisions
  - boundary type: dataclass, protocol, or supported record owned by a package
  - private helper: small, pure, one-module-only implementation detail
  - utility: truly generic behavior inside a bounded package-local module
  - delete: duplicated, obsolete, compatibility residue, or behavior no longer
    needed
- If a function cannot honestly stay private, pure, and local, make it part of
  an owning object instead of exporting another module-level helper.
- Prefer one primary public actor class per module. If a module grows multiple
  public classes, split it by responsibility.
- Group modules by ownership packages, not by flat technical nouns. Prefer
  package boundaries such as `runtime`, `analysis`, `safety`, `reporting`, and
  `interface` when adding new code.
- Avoid vague global `helpers.py` or `utils.py` modules. Common code should have
  a bounded owner and a precise name.
- Constructor injection is preferred over importing sibling internals when a
  component needs collaborators.
- Respect public interfaces between modules. Do not import private helpers,
  mutate another module's globals, or assemble another component's internal
  payload shape from the outside.
- Delete obsolete branches, flags, shims, aliases, and experiments during this
  early development phase. Do not add compatibility layers unless explicitly
  requested.

## Dependency Policy

- Keep the runtime package dependency-light. Add dependencies only when they
  clearly improve correctness, user experience, or maintainability enough to
  justify installation and supply-chain cost.
- Consider Pydantic deliberately for externally consumed schemas, config
  validation, or strict JSON contract validation if dataclasses plus small
  validators become insufficient.
- Do not introduce Pydantic just because a record has fields. Internal event and
  snapshot records can stay as standard-library dataclasses while the schema is
  simple and well tested.
- If Pydantic is added, document why it belongs in the public architecture,
  constrain it to the boundary that needs validation, and add tests for parsing,
  validation errors, and serialization stability.

## Runtime Boundaries

- Keep tracing, filtering, event schema, summarisation, static analysis,
  snapshot generation, reporting, and CLI orchestration as separate
  responsibilities.
- Treat `docs/design/software-design-principles.md` as product doctrine. When
  tracing or reporting behavior changes, preserve the distinction between raw
  implementation artifacts and architectural actors.
- Skeleton should promote maintainable large-Python design: explicit ownership,
  dependency inversion, ports and adapters, repositories/unit-of-work where
  persistence exists, dependency injection at composition roots, and I/O
  decoupled from business logic.
- The report should preserve runtime ownership visually. Modules are outer
  shells. Runtime object instances live inside modules. Module-level public
  functions live inside modules. Public instance methods live inside the object
  instance observed at runtime. Class definitions are type metadata, not graph
  boxes, unless a future feature deliberately models class objects as runtime
  actors.
- Replay should be evidence-progressive. Do not show the whole static graph at
  time zero. As the user steps through events, reveal only the modules,
  instances, functions, methods, and call/return edges that have been observed up
  to that event. Stepping backward should hide future evidence again.
- Replay metrics should be time-aware. Fan-in, fan-out, call count, edge width,
  node size, first_seen, and last_seen should reflect the current replay
  position, not only the final snapshot totals.
- Entrypoint, service, repository, adapter, port, and external resource should
  be treated as roles or boundary concepts first. Create graph nodes for them
  only when runtime evidence shows a concrete actor or resource.
- I/O should become first-class architecture evidence. Databases, filesystems,
  HTTP services, queues, caches, model providers, clocks, randomness, and
  environment access should eventually be depicted as external resources or
  adapters rather than hidden inside generic method-call edges.
- Report design should help users spot useful patterns and smells: clean
  application-service orchestration, rich domain objects, explicit repositories,
  clear adapter boundaries, hidden I/O in domain logic, high fan-in/fan-out, and
  accidental coupling.
- Treat traceability as Skeleton's product moat. Runtime data should support
  three audiences: humans stepping through an interactive visual replay,
  developers reading concise workflow explanations, and LLMs consuming
  structured text/JSON evidence without guessing from raw events.
- Keep Skeleton's category boundary explicit. Static and multi-modal knowledge
  graph tools are useful references, but Skeleton's source of truth is observed
  runtime behavior. Do not turn Skeleton into a generic repository knowledge
  graph builder before runtime trace, replay, query, and scenario explanation
  are excellent.
- Future query features may become Cypher-like graph interactions, but v0 should
  first keep node, edge, event, and narrative outputs clean enough that such a
  query layer can be added deliberately.
- Keep the event schema simple, documented, and append-friendly.
- Capture summaries of values, not object contents.
- Redact likely secrets and avoid logging huge values.
- Trace only project-local modules by default. Do not pull third-party libraries
  into the architecture graph unless the user opts in with filters.
- Public architecture calls are public functions and methods. Private/internal
  names beginning with `_` should stay out of the v0 runtime graph.

## Documentation

- Keep setup and repository overview in `README.md`.
- Keep contribution workflow in `CONTRIBUTING.md` when that workflow needs more
  than this file.
- Keep GitHub workflow files under `.github/`.
- Keep current behavior documentation under `docs/` once it grows beyond the
  README.
- Keep planning, roadmap, phase work, handoffs, and future work under
  `project/`.
- Record meaningful architecture decisions as numbered ADRs under
  `docs/architecture/` using: `# Title`, `## Status`, `## Context`,
  `## Decision`, `## Consequences`.
- Use Mermaid diagrams when they clarify request flows, state transitions,
  package boundaries, or trace/snapshot/report relationships.
- Build beautiful, user-oriented library docs before PyPI release. At minimum,
  docs should cover installation, quickstart, CLI usage, trace schema, snapshot
  schema, report behavior, safety/redaction model, examples, and extension
  points.
- Document design intent, not just APIs. Design docs should explain why visual
  replay, step-through interaction, LLM-readable workflow text, and future graph
  query interactions belong together.
- Keep examples realistic and runnable. Prefer examples that demonstrate the
  non-invasive runner workflow rather than decorator-based instrumentation.
- Brand assets such as logos, screenshots, and report previews should be treated
  as product artifacts. Keep source assets in predictable docs or project
  locations and avoid broken image links in package-facing docs.

## CLI And Product Aesthetics

- The CLI should feel smart, modern, and calm. Use color, spacing, and symbols
  to clarify phases, outcomes, paths, and next actions.
- Emojis and symbols are welcome when they improve scanning, but do not flood
  output. Prefer a few stable status marks over decorative noise.
- Keep CLI output TTY-aware. Provide a no-color path for logs, CI, tests, and
  users who set `NO_COLOR`.
- Error messages should be direct and actionable. Summaries should make the
  generated artifacts and next step obvious.
- Interactive report UX should feel like an architecture workbench: visual map,
  event step-through, node metadata, safe examples, and eventually structured
  workflow narration.

## Verification

- Practice TDD by default for behavior changes: failing or characterization
  test first, implementation second, passing test third.
- Run targeted `pytest` commands while developing narrow behavior.
- Run `make check` before handoff when feasible.
- Run `git diff --check` before PR handoff.
- If a command cannot run because of sandbox or machine constraints, report the
  exact command and failure mode.
- Mirror package ownership under `tests/` where practical.
- Use pytest for all tests.
- Use class-based pytest organization. Test modules should contain focused
  `Test...` classes with test methods inside them, rather than loose top-level
  test functions.
- Structure tests with explicit `# Given`, `# When`, and `# Then` comments so
  intent and behavior boundaries are obvious during review.
- Keep shared test doubles and helpers under `tests/helpers/` when they become
  necessary.
- Add `__init__.py` to test directories only when they need to be importable
  packages.
