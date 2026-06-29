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
make check
```

- `make test` runs pytest with branch coverage and enforces the current coverage
  floor from `pyproject.toml`.
- `make check` runs Ruff, formatting checks, mypy strict, and tests.
- `make format` applies Ruff formatting.
- `make install-hooks` reinstalls hooks if `.git/hooks` is reset.

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
def test_behavior() -> None:
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
