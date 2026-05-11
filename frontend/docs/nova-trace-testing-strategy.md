# Nova Trace Testing Strategy

## Goal

Prevent Copilot from producing a beautiful demo that breaks under basic usage.

## Unit tests

Use Vitest if available.

Prioritize:
- `getScoreBand(score)`
- `formatDate`
- `formatRelativeTime`
- `formatPercent`
- `queryKeys`
- sidebar localStorage helper
- filtering logic for leads

## Component tests

If React Testing Library exists:
- `ScoreBadge`
- `MetricDelta`
- `StatusBadge`
- `EmptyState`

## E2E tests

Use Playwright if available.

Critical smoke tests:
1. `/dashboard` loads
2. `/leads` loads
3. sidebar can collapse
4. sidebar state persists after reload
5. leads table renders
6. a lead row can expand
7. selecting rows shows bulk bar
8. copy email triggers toast

## If no tests exist

Do not install a heavy test stack automatically unless requested.
Instead:
- extract pure helpers
- create this strategy
- prepare code for easy tests
- report recommended commands

## Recommended future commands

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
npm install -D @playwright/test
```
