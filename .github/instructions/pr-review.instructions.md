---
applyTo: "**"
---

# Skeleton PR Review Instructions

Use these instructions when reviewing pull requests in this repository.

Skeleton is a non-invasive architecture replay tool for Python applications.
Review changes as runner, tracing, schema, safety, and report behavior. Prioritize
correctness, architectural boundaries, privacy, user-visible behavior, and tests
over style-only suggestions.

## Review Priorities

Lead with actionable findings. Focus on bugs, regressions, missing tests, unsafe
boundaries, or PR-template gaps. Avoid broad praise, speculative rewrites, and
low-value nits.

Order findings by severity:

- P0/P1: privacy leaks, broken runner startup, corrupt trace/snapshot output,
  unsafe filesystem writes, or major user-visible report breakage.
- P2: user-visible correctness issues, broken schema contracts, missing
  validation, untested behavior changes, misleading report metadata, or tracing
  third-party libraries by default.
- P3: maintainability, bounded performance issues, confusing control flow,
  incomplete docs, or small reliability improvements.

When possible, cite exact files and lines and explain the user-visible or
architectural consequence. If a concern is only a possible improvement, mark it
as such instead of presenting it as a defect.

## Repository Rules To Enforce

Review against `AGENTS.md` as the repository-level contract. In particular:

- Preserve the non-invasive runner boundary. Do not require decorators or
  application-code changes for v0 behavior.
- Keep tracing, filtering, event schema, summarisation, static analysis,
  snapshot generation, reporting, and CLI orchestration separate.
- Behavior changes need focused tests, preferably characterization tests for
  regressions.
- Use `uv`, the Makefile, pytest, Ruff, and mypy. Do not suggest parallel
  tooling already covered by these tools without a concrete requirement.
- Keep dependencies minimal, especially for the runtime package.

## Runtime And Schema Boundaries

For tracer, event, snapshot, and report changes, check that:

- Only project-local modules are traced by default.
- Public architecture calls remain public functions and methods.
- Private/internal names beginning with `_` stay out of the v0 runtime graph.
- Safe summaries are used instead of full object contents.
- Sensitive names such as password, token, secret, key, auth, and credential are
  redacted.
- Huge strings, bytes, containers, or arbitrary object attributes are not dumped.
- Schema changes are intentional, documented, and covered by tests.
- Target scripts can still receive argv and run without source changes.

Flag changes that blur ownership, add hidden global state, bypass filters, make
the report depend on non-generated local assets, or treat profiling metrics as
the product goal.

## Documentation And PR Template

Every PR should satisfy `.github/PULL_REQUEST_TEMPLATE.md`.

Check for:

- A concrete summary.
- Exactly one selected change type.
- Exactly one selected risk level.
- Clear "Why This PR Exists" and "What Changed" sections.
- Explicit invariants under "What Must Remain True".
- Evidence listing tests and exact commands.
- Review guidance for the risky files first.
- Rollback notes.
- Follow-up PRs when scope is intentionally deferred.
- Linked issues using `Closes #...`, `Fixes #...`, or a clear non-closing reference.

Quality checks for the PR body:

- The selected change type and risk level must match the actual blast radius.
- "What Must Remain True" should name concrete invariants, not generic reassurance.
- Evidence should include exact commands and any intentionally skipped checks
  with reasons.
- Review guidance should point reviewers at the riskiest files first and explain
  what does not need re-review.
- Follow-ups should separate required deferred work from optional ideas.
- Rollback notes should describe the smallest practical revert path for the
  delivered unit.

## Testing Expectations

Behavior changes need tests. Regressions need characterization tests that fail
before the fix and pass after it.

Prefer focused tests for:

- runner argument handling and project-root filtering
- trace event schema shape
- redaction and safe value summarisation
- include/exclude filters and private-name filtering
- snapshot node/edge metrics
- report generation and replay metadata
- filesystem output paths and overwrite behavior

Do not accept "test suite passes" as enough when a new behavior path has no
direct coverage.

## Good Review Comments

A useful comment should include:

- the concrete behavior that can fail
- why it matters to a user, runtime boundary, privacy model, or documented contract
- the smallest practical fix direction
- whether a test is missing

Avoid comments that:

- propose broad abstractions before a second implementation exists
- mix unrelated refactors into a correctness fix
- request new dependencies without a concrete reason
- treat local-only output as permission to skip privacy boundaries
