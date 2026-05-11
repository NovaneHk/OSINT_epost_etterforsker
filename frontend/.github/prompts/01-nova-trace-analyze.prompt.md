---
name: "01-nova-trace-analyze"
description: "Analyze the existing repo before implementing Nova Trace frontend."
agent: "agent"
---

# Nova Trace Step 1 — Analyze before coding

Do not write code yet.

## Read first

- `.github/copilot-instructions.md`
- `.github/instructions/*.instructions.md`
- `docs/nova-trace-frontend-spec.md`
- `docs/nova-trace-api-contract.md`
- `docs/nova-trace-react-query-plan.md`
- `docs/nova-trace-do-not-build.md`
- `package.json`
- existing `app/`, `components/`, `lib/`, `stores/`, `tailwind.config.*`, `postcss.config.*`, `tsconfig.json`, and `app/globals.css`

## Find

1. Is this Next.js 14 App Router?
2. Is TypeScript configured?
3. Is Tailwind configured?
4. Is shadcn/ui already installed?
5. Is `@/` path alias configured?
6. Which required packages are installed?
7. Which required packages are missing?
8. What existing layout/component conventions exist?
9. What validation scripts exist?
10. What files should be created?
11. What files should be modified?
12. What risks could break the build?

## Output

Return:
- current repo status
- missing dependencies
- file change plan
- Sprint 1 sequence
- risks
- commands to run before implementation
- exact first implementation step

Do not implement until the user asks you to continue.
