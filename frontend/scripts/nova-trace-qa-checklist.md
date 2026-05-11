# Nova Trace QA Checklist v2

## Build

- [ ] `npm run lint` passes
- [ ] `npm run build` passes
- [ ] `npm run typecheck` or `npx tsc --noEmit` passes
- [ ] no hydration warnings
- [ ] no unused imports
- [ ] no invalid imports

## Layout

- [ ] `/dashboard` loads
- [ ] `/leads` loads
- [ ] AppShell wraps pages
- [ ] Sidebar expanded width is 240px
- [ ] Sidebar collapsed width is 64px
- [ ] Sidebar preference persists after refresh
- [ ] Topbar height is stable
- [ ] Content area does not overflow unexpectedly

## Dashboard

- [ ] 4 KPI cards render
- [ ] KPI cards include label, value, delta, icon, sparkline
- [ ] Trend chart is responsive
- [ ] Active runs render
- [ ] Source health grid renders
- [ ] Recent leads render
- [ ] Activity feed renders
- [ ] Empty state exists when mock data is empty

## Leads

- [ ] Toolbar renders
- [ ] Search works
- [ ] Table renders at least 25 leads
- [ ] Score badges use correct band colors and text
- [ ] Select row works
- [ ] Select all visible works
- [ ] Bulk action bar appears
- [ ] Row expansion works
- [ ] Email copy works
- [ ] Sonner toast appears after copy

## API-readiness

- [ ] data functions exist
- [ ] query keys exist
- [ ] mock data shapes match future API contract
- [ ] components are not tightly coupled to raw mock arrays

## Accessibility

- [ ] Icon-only buttons have aria-label
- [ ] Focus ring visible
- [ ] Keyboard tab navigation works
- [ ] Escape closes dialogs/palettes when present
- [ ] Status is not color-only
- [ ] Reduced motion respected

## Performance

- [ ] no whole-app unnecessary client boundary
- [ ] table columns memoized
- [ ] chart containers responsive
- [ ] skeletons have stable dimensions
- [ ] no obvious layout shift

## Design

- [ ] no raw hex colors scattered in components
- [ ] dark-first identity feels premium
- [ ] cards have consistent borders and spacing
- [ ] typography uses tabular numbers for metrics
- [ ] tables use mono font for email/domain/score
