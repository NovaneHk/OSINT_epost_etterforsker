---
name: "Nova Trace Frontend Standards"
description: "Frontend architecture, component, Tailwind and shadcn rules for Nova Trace."
applyTo: "**/*.{ts,tsx,css,md}"
---

# Nova Trace Frontend Standards

## Component architecture

- Use server components by default.
- Use client components only for state, effects, browser APIs, charts, tables, command palette, Framer Motion, and localStorage.
- Keep `page.tsx` files thin.
- Split large pages into domain components.
- Prefer composition over prop drilling.
- Keep components readable and small.

## Styling

- Use Tailwind utility classes.
- Use CSS variables for Nova Trace tokens.
- Do not scatter raw hex values in components.
- Use `tabular-nums` for KPI values, scores, counters, durations, and table metrics.
- Use mono font for emails, domains, IDs, API keys, scores, and technical values.

## Layout

- App shell zones: sidebar, topbar, adaptive content area.
- Sidebar expanded width: 240px.
- Sidebar collapsed width: 64px.
- Topbar height: 44px.
- Content max width: 1400px.
- Desktop content padding: 32px.
- Tablet/mobile content padding: 24px or less.
- Sidebar collapse preference must persist in localStorage safely.

## Tables

Use `@tanstack/react-table` for the Leads table.

Required columns:
- checkbox
- email
- domain
- score
- source
- found date
- actions

Leads rows must support inline expansion. Do not navigate away for details in Sprint 1.

## Charts

Use Recharts.
Always wrap charts in `ResponsiveContainer`.
Chart backgrounds must be transparent.
Grid lines must be subtle.
Tooltips must match the dark Nova Trace theme.
Empty charts must show a useful empty state.

## Toasts

Use sonner.
Do not use native alerts.

## Accessibility

- Icon-only buttons require `aria-label`.
- Status requires icon + text + color.
- Keyboard users must reach every interactive control.
- Focus ring must be visible.
