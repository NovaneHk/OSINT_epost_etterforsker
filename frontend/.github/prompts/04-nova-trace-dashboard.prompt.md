---
name: "04-nova-trace-dashboard"
description: "Build the Nova Trace Dashboard P1 view."
agent: "agent"
---

# Nova Trace Step 4 — Dashboard P1

Build the Sprint 1 dashboard.

## Create components

- `components/dashboard/kpi-card.tsx`
- `components/dashboard/dashboard-trend-chart.tsx`
- `components/dashboard/active-runs-table.tsx`
- `components/dashboard/source-health-grid.tsx`
- `components/dashboard/recent-leads.tsx`
- `components/dashboard/activity-feed.tsx`
- `components/dashboard/quick-actions.tsx`
- `components/shared/metric-delta.tsx`
- `components/shared/status-badge.tsx`
- `components/shared/empty-state.tsx`
- `components/shared/skeleton-block.tsx`

## Dashboard content

Above the fold:
1. KPI row:
   - Leads 7d
   - Searches 7d
   - Conversion rate
   - Exports 7d

Each KPI card:
- uppercase label
- large metric value
- delta vs previous period
- up/down/neutral icon
- sparkline
- icon

2. Main trend chart:
- Leads over 30 days
- AreaChart
- ResponsiveContainer
- dark tooltip
- subtle grid

3. Active runs:
- run id
- status
- progress
- started time
- ETA

4. Source health:
- source name
- health status
- response time
- last checked
- total leads

Below the fold:
- recent leads
- activity feed
- quick actions

## Acceptance criteria

- `/dashboard` looks premium
- No backend calls
- All chart containers are responsive
- Empty states exist
- No TypeScript errors
