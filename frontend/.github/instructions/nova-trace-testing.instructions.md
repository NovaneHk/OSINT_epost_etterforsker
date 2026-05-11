---
name: "Nova Trace Testing and QA"
description: "Build, lint, typecheck and test expectations for Nova Trace."
applyTo: "**/*.{ts,tsx,js,jsx,json,md}"
---

# Nova Trace Testing and QA

Before reporting completion, run available validation commands.

## Commands

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

## Test priorities

If Vitest exists or is added:
- test score band calculation
- test format helpers
- test query key factory
- test sidebar storage helper if extracted

If Playwright exists or is added:
- smoke test `/dashboard`
- smoke test `/leads`
- test sidebar collapse persistence
- test lead row expansion
- test email copy toast if clipboard mocking is practical

## Fix before completion

- TypeScript errors
- lint errors
- build errors
- hydration warnings
- unused imports
- invalid imports
- missing aria-labels
- hardcoded raw color values in components
- layout shift from loading states
- uncontrolled table bugs
