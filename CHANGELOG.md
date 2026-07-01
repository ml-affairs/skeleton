# Changelog

All notable changes to Skeleton are documented in this file.

The format follows the spirit of Keep a Changelog, and versions follow
Semantic Versioning while the project is public-alpha software.

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
