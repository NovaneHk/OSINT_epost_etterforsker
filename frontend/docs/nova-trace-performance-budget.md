# Nova Trace Performance Budget

## Targets

- LCP: under 1.5s where realistic
- CLS: under 0.1
- INP: under 200ms
- initial JS target: under 200KB gzipped where realistic
- table interactions: under 100ms perceived response

## Rules

- Do not make root layout a client component unless necessary.
- Keep AppShell client boundary as small as possible.
- Memoize TanStack columns.
- Memoize filtered/sorted table data.
- Use pagination or virtualization-ready structure for large lead sets.
- Use `ResponsiveContainer` for Recharts.
- Keep chart components lazy-load-ready.
- Avoid loading P2/P3 charts on Dashboard.
- Use fixed-size skeletons to avoid layout shift.
- Avoid slow decorative animations.
- Respect `prefers-reduced-motion`.

## Chart strategy

Sprint 1:
- Recharts AreaChart for dashboard trend
- Recharts LineChart or minimal SVG for sparklines
- No heavy analytics charts yet

Sprint 3:
- lazy-load analytics charts if bundle grows

## Table strategy

Sprint 1:
- 25–100 mock rows
- TanStack table
- memoized columns
- client-side filtering

Future:
- server-side pagination
- virtualization if rows exceed 500
- debounced search
