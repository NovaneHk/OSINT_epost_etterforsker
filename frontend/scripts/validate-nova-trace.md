# Validation commands

Run from project root:

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

If Playwright exists:

```bash
npx playwright test
```

If Vitest exists:

```bash
npx vitest run
```
