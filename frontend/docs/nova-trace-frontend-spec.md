# Nova Trace Frontend Specification v2

## Purpose

Nova Trace is a premium B2B OSINT dashboard for lead discovery, source monitoring, automated runs, lead scoring, analytics, exports, and reporting.

It must feel like professional intelligence software, not a generic SaaS tool.

## Product principle

The user should never wonder what to do next.

## Positioning

Take from:
- Linear: keyboard-first precision and clean lists
- Vercel Dashboard: dark premium shell and hierarchy
- Retool: data-driven flexibility
- Grafana: dense monitoring and live status

Nova Trace must be:
- cleaner than Retool
- more business-friendly than Grafana
- more domain-specific than Vercel
- more data-intelligent than Linear

## Design tokens

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

## Typography

- UI/body: Inter
- technical data: JetBrains Mono
- KPI numbers: 32px, 700, tabular nums
- body: 14px
- metadata: 12px
- micro labels: 11px uppercase

## Layout

- expanded sidebar: 240px
- collapsed sidebar: 64px
- topbar: 44px height
- content max width: 1400px
- desktop padding: 32px
- tablet padding: 24px

## Navigation

Main:
- Dashboard
- Leads
- Sources
- Runs
- Segments

Output:
- Exports
- Reports

Advanced:
- Playbooks
- Automation
- Monitoring

Bottom:
- Settings
- Help
- User/avatar

## Dashboard P1

Above the fold:
- KPI cards: Leads 7d, Searches 7d, Conversion rate, Exports 7d
- Trend area chart for leads over 30 days
- Active runs
- Source health

Below the fold:
- Recent leads
- Activity feed
- Quick actions

## Leads P1

Required:
- toolbar with search/filter/view/export
- TanStack table
- checkbox selection
- email copy
- domain
- score badge
- source
- found date
- actions
- expandable rows
- sticky bulk action bar

## Score rules

- 80–100 = high/success
- 50–79 = medium/warning
- 0–49 = low/danger

## Sprint 1 acceptance

- AppShell implemented
- dark tokens implemented
- sidebar collapse persists
- Dashboard works with mock data
- Leads table works with mock data
- bulk selection works
- row expansion works
- score badge works
- toasts work
- no build/lint/type errors
