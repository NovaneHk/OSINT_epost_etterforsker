---
name: "02-nova-trace-shell"
description: "Implement Nova Trace design tokens, AppShell, Sidebar and Topbar."
agent: "agent"
---

# Nova Trace Step 2 — Shell and Design Tokens

Implement the Sprint 1 application shell.

## Create or update

- `app/globals.css`
- `app/layout.tsx`
- `components/layout/app-shell.tsx`
- `components/layout/sidebar.tsx`
- `components/layout/topbar.tsx`
- `components/layout/nav-item.tsx`
- `stores/app-shell-store.ts` or a safe localStorage helper
- placeholder route pages if missing:
  - `app/dashboard/page.tsx`
  - `app/leads/page.tsx`
  - `app/sources/page.tsx`
  - `app/runs/page.tsx`
  - `app/analytics/page.tsx`
  - `app/reports/page.tsx`
  - `app/playbooks/page.tsx`
  - `app/settings/page.tsx`

## Requirements

- Dark-first Nova Trace tokens
- Sidebar expanded: 240px
- Sidebar collapsed: 64px
- Topbar height: 44px
- Content max width: 1400px
- Desktop padding: 32px
- Active route highlighting
- localStorage persistence without hydration warnings
- lucide-react icons
- accessible labels
- visible focus states

## Acceptance criteria

- App loads without build errors
- Sidebar collapses and expands
- Sidebar preference survives refresh
- Active route is visually clear
- Dashboard and Leads render inside AppShell
