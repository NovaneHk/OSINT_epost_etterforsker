---
name: "06-nova-trace-api-client-ready"
description: "Make Nova Trace frontend API-ready without adding real backend calls."
agent: "agent"
---

# Nova Trace Step 6 — API-ready Frontend Layer

Do not add real backend calls. Make the current mock-first frontend ready for future APIs.

## Read

- `docs/nova-trace-api-contract.md`
- `docs/nova-trace-react-query-plan.md`
- `.github/instructions/nova-trace-api.instructions.md`

## Implement

- ensure all data goes through `lib/data/*` functions
- ensure query keys exist in `lib/query-keys.ts`
- ensure response shapes can match future API contracts
- add loading/empty/error UI states where missing
- keep direct raw mock imports out of pages where practical

## Do not

- do not create API routes unless explicitly required
- do not fetch real endpoints
- do not add auth
- do not add backend/database logic

## Acceptance criteria

- UI still works with mock data
- data layer can later be swapped for fetch/React Query
- no component is tightly coupled to raw mock arrays
- no build/type errors
