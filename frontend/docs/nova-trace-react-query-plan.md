# Nova Trace React Query Plan

Sprint 1 can work without React Query if the app is purely mock-first. When API integration begins, use this plan.

## Query keys

Create `lib/query-keys.ts`:

```ts
export const queryKeys = {
  dashboard: {
    all: ["dashboard"] as const,
    metrics: () => [...queryKeys.dashboard.all, "metrics"] as const,
    trends: (range: "7d" | "30d" | "90d") =>
      [...queryKeys.dashboard.all, "trends", range] as const,
    activity: () => [...queryKeys.dashboard.all, "activity"] as const,
  },
  leads: {
    all: ["leads"] as const,
    list: (filters: LeadFilters) => [...queryKeys.leads.all, "list", filters] as const,
    detail: (id: string) => [...queryKeys.leads.all, "detail", id] as const,
  },
  sources: {
    all: ["sources"] as const,
    list: () => [...queryKeys.sources.all, "list"] as const,
    health: () => [...queryKeys.sources.all, "health"] as const,
  },
  runs: {
    all: ["runs"] as const,
    list: () => [...queryKeys.runs.all, "list"] as const,
    active: () => [...queryKeys.runs.all, "active"] as const,
    detail: (id: string) => [...queryKeys.runs.all, "detail", id] as const,
    logs: (id: string) => [...queryKeys.runs.all, "logs", id] as const,
  },
};
```

## Stale times

- Dashboard KPI: 30 seconds
- Leads list: 60 seconds
- Source health: 30 seconds
- Active runs: 0 seconds, poll every 5 seconds
- Run logs: 0 seconds, poll every 3–5 seconds while active
- Settings: 5 minutes

## Mutations

Use optimistic UI only for low-risk actions:
- mark contacted
- rename
- local notes
- UI preference

Do not use optimistic UI for:
- delete
- reset
- cancel run
- permanent export

## Structure

- query functions in `lib/api` or `lib/data`
- query keys in `lib/query-keys.ts`
- components receive data where practical
- no raw fetch logic inside visual components
