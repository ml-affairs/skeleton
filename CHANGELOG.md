# Changelog

All notable changes to Skeleton are documented in this file.

The format follows the spirit of Keep a Changelog, and versions follow
Semantic Versioning while the project is public-alpha software.

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
