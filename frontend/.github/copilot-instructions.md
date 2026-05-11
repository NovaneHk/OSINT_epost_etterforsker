# Nova Trace — Repository-wide Copilot Instructions v2

You are working on Nova Trace: a premium B2B OSINT dashboard for professional lead discovery, source monitoring, automated runs, scoring, analytics, exports, and reporting.

## Product identity

Nova Trace is not a generic SaaS dashboard. It must feel like professional intelligence software for decision makers:
- precise
- dark-first
- fast
- premium
- keyboard-friendly
- data-dense without chaos
- built for B2B OSINT workflows

The user should never wonder what to do next. The interface must guide them quietly, efficiently, and one step ahead.

## Stack

Use:
- Next.js 14 App Router
- TypeScript
- Tailwind CSS
- shadcn/ui
- Framer Motion
- lucide-react
- Recharts
- @tanstack/react-table v8
- sonner
- zustand
- react-hook-form
- zod
- cmdk via shadcn/ui
- @tanstack/react-query when API-ready data fetching is introduced
- Vitest and Playwright only when tests are requested or already configured

Do not introduce alternative frameworks unless explicitly requested.

## Required reading before coding

Before implementing any Nova Trace task, read:

1. `docs/nova-trace-frontend-spec.md`
2. `docs/nova-trace-api-contract.md`
3. `docs/nova-trace-react-query-plan.md`
4. `docs/nova-trace-do-not-build.md`
5. Relevant `.github/instructions/*.instructions.md`

## Sprint discipline

Sprint 1/P1 includes:
1. Global design tokens
2. AppShell
3. Sidebar and Topbar
4. Collapsible sidebar with localStorage persistence
5. Domain types and realistic mock data
6. Dashboard with KPI cards, sparklines, trend chart, active runs, source health, recent leads, and activity feed
7. Leads page with TanStack Table, score badges, expandable rows, copy email, bulk select, and sticky bulk action bar
8. API-ready data shapes without real backend calls
9. Skeleton loading states
10. Sonner toast feedback
11. Basic test coverage where configured
12. Build/lint/typecheck cleanup

Do not build Sprint 2 or Sprint 3 before Sprint 1 passes QA.

## Hard boundaries

Do not build in Sprint 1:
- authentication
- real backend
- database
- payment/subscription logic
- full Playbooks workflow builder
- full Analytics page
- full Reports generator
- real exports
- real scraping/OSINT execution
- background jobs
- production API integration
- AG Grid
- native `alert`, `confirm`, or `prompt`

## Architecture rules

- Keep `page.tsx` files thin.
- Put layout components in `components/layout`.
- Put dashboard components in `components/dashboard`.
- Put leads components in `components/leads`.
- Put shared primitives in `components/shared`.
- Put API-ready mock adapters in `lib/data`.
- Put types in `lib/types.ts`.
- Put mock data in `lib/mock-data.ts`.
- Put constants in `lib/constants.ts`.
- Put formatters in `lib/format.ts`.
- Put query keys in `lib/query-keys.ts`.
- Use `@/` imports if already configured.
- Preserve existing repo conventions when they are sane.
- Prefer small components over monoliths.

## Theme tokens

Use Nova Trace colors:

- background: `#0F1117`
- surface: `#161B22`
- surface elevated: `#1C2128`
- border: `#30363D`
- text primary: `#F0F6FC`
- text secondary: `#8B949E`
- accent blue: `#0A84FF`
- success: `#3FB950`
- warning: `#D29922`
- danger: `#F85149`
- AI purple: `#BC8CFF`

Define these centrally. Do not scatter raw hex values across components.

## UX rules

- Status must use text + icon + color.
- Empty states must explain the state and provide a CTA.
- Loading states must use skeletons, not spinners.
- Feedback must use sonner toasts.
- Use Framer Motion subtly.
- Respect `prefers-reduced-motion`.
- Icon-only controls must have `aria-label`.
- All interactive controls must be keyboard reachable.
- Focus rings must be visible.

## Data rules

Sprint 1 uses mock data only, but all data shapes must be compatible with future API contracts.

Create realistic Norwegian/B2B mock data:
- at least 25 leads
- at least 6 sources
- at least 8 runs
- at least 2 active/running runs
- at least 30 days of chart data
- at least 15 activity events

Score bands:
- 80–100: high/success
- 50–79: medium/warning
- 0–49: low/danger

## Performance rules

- Use `ResponsiveContainer` for charts.
- Memoize TanStack columns and derived table data.
- Do not render huge lists without pagination or virtualization-ready structure.
- Keep chart components lazy-load-ready.
- Avoid unnecessary client components.
- Avoid global client wrappers around the whole app unless required.

## Validation commands

Run available commands:
- `npm run lint`
- `npm run build`
- `npm run typecheck` if available
- otherwise `npx tsc --noEmit`
- `npm run test` if available
- `npm run test:e2e` if available

If commands fail, fix them before reporting completion.

## Completion report

When finished, report:
1. Created files
2. Modified files
3. Commands run
4. Command results
5. Acceptance criteria passed
6. Known limitations
7. Remaining Sprint 2/Sprint 3 work
8. Assumptions made
