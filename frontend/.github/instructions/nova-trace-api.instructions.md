---
name: "Nova Trace API Readiness"
description: "Future API contract and React Query readiness rules for Nova Trace."
applyTo: "**/*.{ts,tsx}"
---

# Nova Trace API Readiness

Sprint 1 must use mock data only, but the frontend should be shaped to make backend integration simple.

## Rules

- Keep domain types in `lib/types.ts`.
- Keep mock data in `lib/mock-data.ts`.
- Keep query keys in `lib/query-keys.ts`.
- If creating data access functions, put them in `lib/data/`.
- Do not call real APIs in Sprint 1.
- Shape mock responses like documented API responses.
- Include loading, empty, and error states even when data is mocked.
- Avoid tightly coupling components to mock arrays.

## Future endpoints

Use the documented future API contract in `docs/nova-trace-api-contract.md`.

## React Query

When React Query is introduced:
- use stable query keys
- keep query functions separate from UI
- use stale times according to `docs/nova-trace-react-query-plan.md`
- do not put fetch logic directly inside components
