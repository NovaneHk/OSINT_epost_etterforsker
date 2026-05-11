---
name: "05-nova-trace-leads"
description: "Build the Nova Trace Leads P1 workbench."
agent: "agent"
---

# Nova Trace Step 5 — Leads Page P1

Build the Sprint 1 Leads workbench.

## Create components

- `components/leads/leads-page-client.tsx`
- `components/leads/lead-table.tsx`
- `components/leads/lead-toolbar.tsx`
- `components/leads/lead-row-details.tsx`
- `components/leads/score-badge.tsx`
- `components/leads/bulk-action-bar.tsx`
- `components/leads/lead-status-badge.tsx`

## Table

Use `@tanstack/react-table`.

Columns:
1. checkbox
2. email
3. domain
4. score
5. source
6. found date
7. actions

## Interactions

- Search/filter within table
- Select row
- Select all visible rows
- Sticky bulk action bar
- Inline row expansion
- Copy email with toast
- Mock mark contacted/export/reject toasts

## Expanded details

Show:
- company/domain summary
- WHOIS data
- validation history
- source history
- timestamps
- actions

## Acceptance criteria

- `/leads` works
- table has realistic data
- bulk selection works
- row expansion works
- score badges are correct
- copy email toast works
- no native alert/confirm/prompt
