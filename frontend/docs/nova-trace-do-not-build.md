# Nova Trace Do Not Build List

This file exists to prevent scope explosion.

## Never build in Sprint 1

- authentication
- login/register
- real backend
- database schema
- Prisma
- payment/subscription logic
- billing
- real scraping
- real OSINT execution
- job queues
- background workers
- full analytics page
- full reports generator
- real PDF export
- real Excel export
- full Playbooks workflow engine
- AG Grid
- native browser alert/confirm/prompt
- admin panel unrelated to Sprint 1
- marketing landing page

## Avoid unless already present

- adding a new state library
- adding a new chart library
- adding a new table library
- adding heavy dependencies
- converting the whole app to client components
- rewriting existing working structure

## Allowed in Sprint 1

- mock data
- API-ready data functions
- query keys
- domain types
- dashboard UI
- leads workbench UI
- sidebar/topbar
- skeleton states
- sonner toasts
- basic tests if safe
