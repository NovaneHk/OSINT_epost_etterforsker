---
name: "08-nova-trace-performance-hardening"
description: "Improve Nova Trace performance without changing product scope."
agent: "agent"
---

# Nova Trace Step 8 — Performance Hardening

Improve performance for Sprint 1 without changing product scope.

## Read

- `docs/nova-trace-performance-budget.md`
- `.github/instructions/nova-trace-performance.instructions.md`

## Check and improve

- avoid whole-app client component
- memoize TanStack table columns
- memoize derived filtered data
- ensure charts use ResponsiveContainer
- keep chart components lazy-load-ready
- reduce unnecessary re-renders
- prevent layout shifts with fixed skeleton dimensions
- ensure sidebar localStorage does not cause hydration warnings
- avoid raw giant components

## Do not

- do not add new product features
- do not install heavy dependencies
- do not rewrite everything

## Acceptance criteria

- build still passes
- typecheck still passes
- components remain readable
- table interactions feel fast
- no obvious layout shift
