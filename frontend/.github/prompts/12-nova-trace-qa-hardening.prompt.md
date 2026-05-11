---
name: "12-nova-trace-qa-hardening"
description: "Run QA, fix build/lint/type errors, and produce completion report."
agent: "agent"
---

# Nova Trace Step 12 — QA and Hardening

Perform final QA for the current sprint.

## Run commands

Run:
```bash
npm run lint
npm run build
```

If available:
```bash
npm run typecheck
npm run test
npm run test:e2e
```

If no typecheck script exists:
```bash
npx tsc --noEmit
```

## Fix

Fix every:
- TypeScript error
- build error
- lint error
- hydration warning
- invalid import
- unused import
- missing aria-label on icon-only controls
- hardcoded raw color values in components
- layout shift caused by loading states
- broken route
- broken localStorage sidebar state
- score badge inconsistency
- table selection bug
- row expansion bug

## Manual QA checklist

Verify:
- `/dashboard` loads
- `/leads` loads
- sidebar collapse works
- sidebar state persists after refresh
- active route is highlighted
- KPI cards render
- charts render in responsive containers
- Leads table renders
- bulk select works
- row expansion works
- email copy toast works
- keyboard tab navigation is usable

## Completion report

Return:
1. Created files
2. Modified files
3. Commands run and results
4. Acceptance criteria passed
5. Known limitations
6. Remaining risks
7. Next recommended Sprint 2 task
