# Changelog

All notable changes to Skeleton are documented in this file.

The format follows the spirit of Keep a Changelog, and versions follow
Semantic Versioning while the project is public-alpha software.

## Unreleased

## [0.10.0] - 2026-07-20

### Added

- Added public `trace(...)` and `TraceSession.trace(...)` context managers for tracing in-process callables while still generating the full Skeleton artifact set.
- Added the `skeleton_trace` pytest fixture so scenario tests can trace code with active fixtures and monkeypatches.
- Callable traces now default artifacts to `<project-root>/.skeleton/<label>/latest/` when no explicit output directory is configured.

## [0.9.0] - 2026-07-17

### Added

- Added stable trace call identifiers and callable-kind metadata so IDE integrations can pair call/return events and distinguish module functions, instance methods, class methods, and static methods.

## [0.8.0] - 2026-07-08

### Added

- Added a stable `window.SkeletonReplay` report selection bridge so IDEs can
  follow the current replay event with source file, line, module, function, and
  caller/callee endpoint metadata.

## [0.7.0] - 2026-07-07

### Added

- `session.json` artifact for IDEs and automation tools, recording the command,
  invocation, target, generated artifact paths, metrics, exit status, and target
  error for each CLI or Python API run.

## [0.6.1] - 2026-07-06

### Changed

- Replay controls now keep the collapse button on the main control row, place typed Start/End trace-window fields beside the replay buttons, and use a wider dock for the denser control set.

### Fixed

- The HTML report now pans to compact selected callables or instances instead of large module/package owner shells, preventing the graph from appearing blank when replaying module-level helper call chains.

## [0.6.0] - 2026-07-06

### Added

- Derived trace roles in `snapshot.json` for entrypoints, system-under-test frames, test harnesses, test utilities, import/setup calls, and roots whose caller is outside the selected trace boundary.

### Changed

- Default artifact placement is now target-local and collision-aware: `skeleton run` writes under `<script-parent>/.skeleton/<script-stem>/latest/`, while `skeleton pytest` preserves file, node id, and parametrized-node identity under `<test-dir>/.skeleton/.../latest/`; explicit `--out-dir`, `SKELETON_OUT_DIR`, and `SKELETON_HOME` still take precedence.
- The HTML report now starts replay at the inferred scenario entrypoint when available, groups pre-entrypoint setup events in a collapsed section, and renders harness/setup/test utility frames with subdued role styling instead of adding another hide toggle.
- The HTML replay dock can now be collapsed, and trace-window Start/End event numbers can be typed directly instead of only adjusted with draggable handles.
- `workflow.md` now includes setup-before-entrypoint summaries and trace-role context for actors and events.

### Fixed

- Hidden private return/helper events now retain the nearest visible caller-chain anchor in the report and show a concise note instead of leaving the graph without an obvious current focus.

## [0.5.0] - 2026-07-06

### Added

- `skeleton pytest` for tracing existing pytest sessions and selected test nodes.
- `TraceSession.run_pytest()` for generating replay artifacts from pytest scenarios through the Python API.

### Changed

- `skeleton pytest` and `TraceSession.run_pytest()` now default artifacts to `<selected-test-directory>/.skeleton` when a test path is provided, while `--out-dir` and `SKELETON_OUT_DIR` still take precedence.
- Private/internal project callables are now traced, marked with `visibility: "private"` in snapshots, rendered with dashed outlines, and hideable in the HTML report.

### Fixed

- Pytest artifact generation now still writes an empty `trace.jsonl` plus derived artifacts when pytest tracing fails before `RuntimeTracer` starts.

## [0.4.0] - 2026-07-02

### Added

- Structured return aggregation in `snapshot.json` for repeated compatible dictionary-like return records.
- Report and workflow rendering for structured-return groups as semantic tables with raw event expansion.
- Configurable structured-return tuning and display-label templates through `pyproject.toml`.
- Concise graph hover cards for latest edge and instance evidence.
- Shared artifact-generation pipeline for CLI and Python API report outputs.

### Changed

- The report collapses low-complexity structured-return calls by default while preserving raw trace events.
- Instance labels prefer semantic record identity when derived from structured returns, with technical `Class@0x...` identity retained underneath.

## [0.3.0] - 2026-07-02

### Added

- Architecture quality artifacts: `quality.json` for machines and `architecture_quality.md` for humans and LLMs.
- Compact report quality signals for runtime hotspots, high fan-out workflows, broad module surfaces, large modules, and external boundary evidence.
- Floating replay controls that can be moved on the architecture plane.
- Trace execution window selector with left and right handles for isolating a period of interest.
- Export selected trace-window JSON from the report, including exact events, related nodes/edges, quality evidence, and an LLM-readable note.
- Module treemap overlay with rectangles sized by observed module touches in the selected trace window and colored by fan-out/activity.
- Treemap hover details explaining the metrics behind each rectangle's size, color, and active state.
- Hide/show controls for both the module treemap and graph legend.

### Changed

- Replay stepping, graph visibility, time-aware metrics, and the module treemap now respect the selected trace execution window.
- The report side panel stays focused on actor details, current event explanation, and trace evidence while replay navigation lives on the graph plane.
- Root-level module, package, and resource placement better avoids overlap as entities appear during replay.

## [0.2.0] - 2026-07-01

### Added

- Runtime boundary evidence for stdout, filesystem, SQLite, and basic network socket calls while project-local code is active.
- Interactive report rendering for I/O resources as cylinders and external services as diamond-shaped actors.
- Progressive replay improvements for resource calls, return edges, node placement, and time-aware graph metrics.
- Foldable report side panel so the architecture map can use more horizontal space during replay.
- Fixture projects and report tests for orchestrated flows and I/O boundary visualization.

### Changed

- Network calls are now represented as `external_service` endpoints instead of I/O resource cylinders.
- Report documentation now distinguishes external services from local resources and keeps raw trace JSON as audit evidence.

## [0.1.3] - 2026-06-30

### Fixed

- Restore the main image-rich README as the PyPI long description now that images use full GitHub raw URLs.

## [0.1.2] - 2026-06-30

### Fixed

- Use a PyPI-specific long description without image tags so the package page does not show broken README images.

## [0.1.1] - 2026-06-30

### Fixed

- Use absolute GitHub raw image URLs in the README so images render correctly on PyPI.

## [0.1.0] - 2026-06-30

### Added

- Initial `skeleton-replay` PyPI package metadata.
- `skeleton` and `skeleton-replay` console commands.
- `python -m skeleton_replay run <script> [args...]` entrypoint.
- Non-invasive runtime tracing for project-local public Python calls.
- Safe argument and return-value summaries with secret redaction.
- `trace.jsonl`, `snapshot.json`, `workflow.md`, and `report.html` artifact generation.
- Interactive dark-theme architecture replay report.
- Public `TraceSession` Python API.
- Static module scanning for basic LOC, class, function, and import metadata.
- README, API docs, design docs, contribution guide, and PyPI release plan.
- GitHub Actions CI and PyPI Trusted Publishing workflow.

### Notes

- Skeleton is an architecture replay tool, not a profiler.
- v0.1.0 traces script execution. Callable, pytest, module, IDE, and web-request integrations are planned as later seams.
- The trace and snapshot schemas are intentionally compact and may evolve while `schema_version` remains documented.
