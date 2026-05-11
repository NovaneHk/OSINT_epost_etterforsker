---
name: "03-nova-trace-data-model"
description: "Create TypeScript domain types, mock data, query keys and API-ready data adapters."
agent: "agent"
---

# Nova Trace Step 3 — Types, Mock Data and API-ready Data Layer

Create the domain model, query keys, mock data and data access layer.

## Create

- `lib/types.ts`
- `lib/mock-data.ts`
- `lib/format.ts`
- `lib/constants.ts`
- `lib/query-keys.ts`
- `lib/data/dashboard.ts`
- `lib/data/leads.ts`
- `lib/data/sources.ts`
- `lib/data/runs.ts`

## Required types

- `Lead`
- `Source`
- `Run`
- `DashboardMetric`
- `ActivityEvent`
- `ScoreBand`
- `SourceHealth`
- `RunStatus`
- API response wrapper types:
  - `ApiSuccess<T>`
  - `ApiError`
  - `PaginatedResponse<T>`

## Mock requirements

- at least 25 leads
- at least 6 sources
- at least 8 runs
- at least 2 active/running runs
- 30 days of chart data
- at least 15 activity events
- realistic Norwegian/B2B names/domains/emails

## Query keys

Create stable query keys for:
- dashboard metrics
- dashboard chart
- leads list
- lead detail
- sources
- source health
- runs
- active runs

## Acceptance criteria

- Components can import data through data functions, not raw arrays only
- No backend calls
- Shapes match `docs/nova-trace-api-contract.md`
- No TypeScript errors
