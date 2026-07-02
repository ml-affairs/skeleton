# PyPI Release Plan

## Status

Active release preparation document.

Skeleton is already shaped like a PyPI package, but a public release needs a
small set of product, packaging, documentation, and governance tasks.

## Current State

Already present:

- `pyproject.toml`
- package metadata
- MIT license
- PyPI distribution name: `skeleton-replay`
- import package: `skeleton_replay`
- console script entrypoints: `skeleton` and `skeleton-replay`
- project URLs, keywords, and classifiers
- `uv` build backend
- pytest, Ruff, mypy, and coverage gate
- GitHub Actions CI
- README with badges
- contribution guide and PR template
- generated demo artifacts for local development

## Required Before First Public Release

### Package Identity

- PyPI owner can be an individual PyPI account for v0. A PyPI organization is
  useful later for shared ownership, but it is not required to publish
  `skeleton-replay`.
- verify the long description renders on PyPI

### Public API

- v0 includes `TraceSession.run_script`
- public imports are documented in `docs/api/python-api.md`
- `argparse.Namespace` and internal command objects are not the main API

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

- `uv build` verification in release workflow
- publish workflow uses PyPI Trusted Publishing through GitHub Actions OIDC
- `v*` tag pushes trigger publishing; `workflow_dispatch` is available as a recovery path
- TestPyPI dry run
- version bump process
- changelog entry in `CHANGELOG.md`
- GitHub release notes copied from the changelog
- tag naming convention

Trusted Publishing configuration to create in PyPI:

| Field | Value |
| --- | --- |
| PyPI project | `skeleton-replay` |
| GitHub owner | `ml-affairs` |
| GitHub repository | `skeleton` |
| Workflow filename | `publish.yml` |
| Environment name | `pypi` |

If `skeleton-replay` does not exist on PyPI yet, create a pending Trusted
Publisher from the PyPI account publishing page with the same values. The first
successful publish creates the project and converts the pending publisher into a
normal publisher.

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

1. Update version in `pyproject.toml` and `skeleton_replay/__init__.py`.
2. Update `CHANGELOG.md`.
3. Update README installation instructions.
4. Run `make check`.
5. Run `uv build`.
6. Create a clean virtual environment.
7. Install `dist/*.whl`.
8. Run `skeleton --help`.
9. Run `skeleton run tests/fixtures/sample_project/app.py --no-open`.
10. Inspect generated artifacts.
11. Configure PyPI Trusted Publishing for `skeleton-replay`.
12. Publish to TestPyPI if desired.
13. Install from TestPyPI if used.
14. Push a `v*` tag to trigger `.github/workflows/publish.yml`.
15. Install from PyPI and run a smoke test.

## Open Decisions

- Should docs be hosted before the first release, or is README plus `docs/`
  enough for an initial package?
- Should the package include embedded report assets later, or keep the report
  self-contained and CDN-backed for v0?
- What compatibility guarantee should be attached to `trace.jsonl` and
  `snapshot.json` schema version 1?
