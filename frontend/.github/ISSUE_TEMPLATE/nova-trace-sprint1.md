---
name: Nova Trace Sprint 1 Frontend
about: Assign this issue to GitHub Copilot coding agent to build Sprint 1.
title: "Build Nova Trace Sprint 1 frontend shell, dashboard and leads workbench"
labels: ["copilot", "frontend", "nova-trace", "sprint-1"]
assignees: ""
---

## Goal

Build Nova Trace Sprint 1 frontend using the repository instructions and prompt files.

## Required reading

- `.github/copilot-instructions.md`
- `docs/nova-trace-frontend-spec.md`
- `docs/nova-trace-api-contract.md`
- `docs/nova-trace-react-query-plan.md`
- `docs/nova-trace-do-not-build.md`

## Scope

Build only:

1. Nova Trace dark-first design tokens
2. AppShell
3. Sidebar and Topbar
4. Collapsible sidebar with localStorage persistence
5. TypeScript domain types
6. Mock data
7. Dashboard P1
8. Leads P1
9. API-ready data layer shape
10. QA hardening

## Out of scope

Do not build:
- auth
- backend
- database
- billing
- full analytics
- full reports
- full Playbooks workflow builder
- real scraping/OSINT execution

## Acceptance criteria

- `/dashboard` works
- `/leads` works
- sidebar collapse persists after refresh
- dashboard KPI cards render
- trend chart renders
- source health renders
- active runs render
- leads table renders
- bulk select works
- lead row expansion works
- email copy toast works
- score badge bands are correct
- lint/build/typecheck pass

## Validation

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

## Completion report

Report:
- files created
- files modified
- validation commands and results
- acceptance criteria status
- known limitations
- next recommended task
