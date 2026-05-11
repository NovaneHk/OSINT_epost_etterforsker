---
name: "Nova Trace Performance"
description: "Performance and bundle rules for Nova Trace frontend."
applyTo: "**/*.{ts,tsx}"
---

# Nova Trace Performance Instructions

## Rules

- Avoid making the whole app a client component.
- Use client components only where necessary.
- Memoize heavy derived values.
- Memoize TanStack columns.
- Keep chart components lazy-load-ready.
- Use pagination or virtualization-ready patterns for large tables.
- Use skeleton loaders with fixed dimensions.
- Avoid layout shift.
- Avoid large unnecessary dependencies.
- Do not install AG Grid for Sprint 1.
- Keep animations short and GPU-friendly.

## Targets

- LCP target: under 1.5s where realistic
- CLS target: under 0.1
- INP target: under 200ms
- Initial JS goal: under 200KB gzipped where realistic

## Report

When doing performance work, report:
- what was memoized
- what was lazy-load-ready
- what layout shifts were prevented
- what remains for later optimization
