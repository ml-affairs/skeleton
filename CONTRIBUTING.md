# Contributing

Skeleton is a typed Python package for replayable architecture tracing. Keep
changes small, tested, and aligned with the non-invasive runner model.

## Setup

Use `uv` and the Makefile:

```bash
make setup
```

`make setup` creates `.venv`, syncs all dependency groups, and installs the
pre-commit and commit-message hooks.

## Daily Workflow

```bash
make sync
make test
make test-cov
make check
make where
make demo-no-open
```

- `make test` runs pytest without the coverage gate, which keeps targeted local
  test runs useful.
- `make test-cov` runs the full pytest suite with branch coverage and enforces
  the current coverage floor.
- `make check` runs Ruff, formatting checks, mypy strict, and tests.
- `make where` prints the stable demo report path, pytest temp root, and package
  default output root.
- `make format` applies Ruff formatting.
- `make install-hooks` reinstalls hooks if `.git/hooks` is reset.
- `make demo` writes a visible report to `tests/dev/.temp/skeleton-demo/` and
  opens it. Use `make demo-no-open` when you only need the files.

Local artifacts are intentionally repo-local during development:

- Stable report UI work: `tests/dev/.temp/skeleton-demo/report.html`
- Pytest `tmp_path` output: `tests/dev/.temp/pytest/`
- End-user CLI default: target-local `.skeleton/<target>/latest/` directories unless `--out-dir`, `SKELETON_OUT_DIR`, or `SKELETON_HOME` is set.

## Code Style

- Python code must be typed and pass `mypy --strict`.
- Public modules, classes, functions, methods, and dataclasses need docstrings.
- Prefer object-owned behavior over loose module-level functions.
- Group modules by ownership package, such as `runtime`, `analysis`, `safety`,
  `reporting`, and `interface`.
- Keep runtime dependencies minimal. Add dependencies only when they clearly
  improve correctness or user experience.

## Tests

Use pytest. Structure tests with explicit comments:

```python
class TestComponentBehavior:
    def test_behavior(self) -> None:
        # Given
        ...

        # When
        ...

        # Then
        ...
```

Behavior changes need focused tests. Regressions need characterization tests
that would fail before the fix.

## Commits

Semantic commit messages are enforced by gitlint:

```text
feat(cli): add replay command
fix(runtime): ignore private calls
docs(readme): explain workflow output
```

## Pull Requests

Before opening a PR:

```bash
make check
git diff --check
```

Use the pull request template. Include the exact commands you ran, what changed,
what must remain true, and any follow-up work intentionally deferred.
