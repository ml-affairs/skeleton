# PyPI Release Plan

## Status

Planning document.

Skeleton is already shaped like a PyPI package, but a public release needs a
small set of product, packaging, documentation, and governance tasks.

## Current State

Already present:

- `pyproject.toml`
- package metadata
- MIT license
- console script entrypoint: `skeleton = "skeleton.cli:main"`
- `uv` build backend
- pytest, Ruff, mypy, and coverage gate
- GitHub Actions CI
- README with badges
- contribution guide and PR template
- generated demo artifacts for local development

## Required Before First Public Release

### Package Identity

- confirm package name availability on PyPI
- confirm owner/organization account
- decide whether the import name remains `skeleton`
- add classifiers to `pyproject.toml`
- add project URLs: homepage, repository, issues, documentation
- verify the long description renders on PyPI

### Public API

- decide whether v0 is CLI-only or includes `TraceSession`
- document the stability level of Python imports
- avoid exposing `argparse.Namespace` or internal command objects as the main API
- add API docs under `docs/api/`

### Documentation

- installation from PyPI
- quickstart
- CLI reference
- output artifact reference
- trace schema
- snapshot schema
- safety and redaction model
- runtime introspection model
- realistic example project
- troubleshooting and limitations

### Release Automation

- `uv build` verification in CI
- publish workflow using PyPI trusted publishing
- TestPyPI dry run
- version bump process
- changelog or GitHub release notes
- tag naming convention

### Quality Gates

- `make check`
- `uv build`
- install wheel in a clean virtual environment
- run `skeleton --help`
- run `skeleton run` against sample project from installed wheel
- verify generated `report.html` opens and has non-empty graph data

### Security And Privacy

- document what is captured
- document what is never captured intentionally
- keep safe summarisation tests focused
- add tests for more secret-name variants
- add a security contact or `SECURITY.md`

## Nice To Have Before Wider Announcement

- public `TraceSession.run_script`
- `run-module` support
- richer example project
- hosted docs site
- report screenshot or short demo GIF
- PyCharm plugin plan linked from docs
- pytest plugin plan linked from docs

## Release Checklist

1. Update version in `pyproject.toml` and `skeleton/__init__.py`.
2. Update README installation instructions.
3. Run `make check`.
4. Run `uv build`.
5. Create a clean virtual environment.
6. Install `dist/*.whl`.
7. Run `skeleton --help`.
8. Run `skeleton run tests/fixtures/sample_project/app.py --no-open`.
9. Inspect generated artifacts.
10. Publish to TestPyPI.
11. Install from TestPyPI.
12. Publish to PyPI.
13. Create a GitHub release.

## Open Decisions

- Should v0 be published as CLI-only, or wait for a stable `TraceSession` API?
- Should docs be hosted before the first release, or is README plus `docs/`
  enough for an initial package?
- Should the package include embedded report assets later, or keep the report
  self-contained and CDN-backed for v0?
- What compatibility guarantee should be attached to `trace.jsonl` and
  `snapshot.json` schema version 1?
