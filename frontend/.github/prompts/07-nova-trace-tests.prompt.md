---
name: "07-nova-trace-tests"
description: "Add or improve tests for Nova Trace Sprint 1."
agent: "agent"
---

# Nova Trace Step 7 — Tests

Add tests only if the project already has a test setup or if adding a minimal setup is safe and scoped.

## Read

- `docs/nova-trace-testing-strategy.md`
- `.github/instructions/nova-trace-testing.instructions.md`
- `package.json`

## If Vitest exists

Add unit tests for:
- score band calculation
- format helpers
- query keys
- sidebar storage helper if extracted

## If Playwright exists

Add e2e/smoke tests for:
- `/dashboard` loads
- `/leads` loads
- sidebar collapse persists
- lead row expansion works
- bulk select works

## If no test framework exists

Do not force a heavy setup without user approval.
Instead:
- create `docs/nova-trace-testing-strategy.md` if missing
- improve pure helper extraction to make future tests easy
- report recommended install commands

## Acceptance criteria

- existing tests pass
- no build/lint/type errors
- new tests are scoped and stable
