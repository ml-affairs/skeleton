## Summary

Short description of the change in 2-4 sentences.

## Change Type

Choose one and delete the other options:

- [ ] Tests / coverage only
- [ ] Pure refactor
- [ ] Small behavior change
- [ ] New feature increment
- [ ] High-risk runtime/schema change

## Risk Level

Choose one and delete the other options:

- [ ] Low: cosmetic, documentation, or local test-only change
- [ ] Medium: bounded logic or behavior change
- [ ] High: trace schema, filesystem output, privacy, or integration-sensitive change

Selected risk level:

## Why This PR Exists

- What pain or need does this PR address?
- Why is this the right incremental step now?

## What Changed

- ...
- ...
- ...

## What Must Remain True

- Existing scripts can run under Skeleton without application-code changes.
- Third-party libraries are not traced by default.
- Sensitive values are redacted or summarized safely.
- Generated trace and snapshot schema changes are intentional and documented.

## Decomposition / Sequence

- [ ] This is the smallest useful unit for this decision.
- [ ] If this is a behavior change, related test coverage was added or updated.
- [ ] If this change depends on follow-up work, follow-ups are listed clearly below.

## Evidence

- Tests added / updated:
  - ...
- Static analysis / checks:
  - ...
- Manual verification:
  - ...

## Review Guidance

- Review this first:
  - ...
- Reviewers should focus on:
  - ...
- Reviewers do not need to re-check:
  - ...

## Rollback

- Smallest practical revert path:
  - ...

## Follow-Up PRs

- ...

## Required Command Checklist

- [ ] `make check`
- [ ] `git diff --check`

## Link to issue(s)

- Closes #
