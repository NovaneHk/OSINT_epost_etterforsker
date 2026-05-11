---
name: "09-nova-trace-command-palette"
description: "Implement Nova Trace command palette for Sprint 2."
agent: "agent"
---

# Nova Trace Step 9 — Command Palette P2

Only run this after Sprint 1 passes QA.

## Goal

Implement a cmdk-based command palette using shadcn/ui command components.

## Requirements

- Open with `Cmd/Ctrl + K`
- Add global search trigger in Topbar
- Escape closes without side effects
- Arrow keys navigate results
- Enter activates selected result
- Recent commands/searches can be local only

## Groups

Navigation:
- Dashboard
- Leads
- Sources
- Runs
- Analytics
- Reports
- Settings

Actions:
- New run
- Export report
- Import CSV
- Show shortcut help

Search:
- leads by email
- leads by domain
- runs by ID
- sources by name

## Acceptance criteria

- command palette opens globally
- keyboard only works
- accessible dialog/command primitives
- no build/type errors
