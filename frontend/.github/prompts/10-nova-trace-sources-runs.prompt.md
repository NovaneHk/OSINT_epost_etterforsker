---
name: "10-nova-trace-sources-runs"
description: "Implement Sources and Runs pages for Nova Trace Sprint 2."
agent: "agent"
---

# Nova Trace Step 10 — Sources and Runs P2

Only run after Dashboard, Leads, and Command Palette are stable.

## Sources page

Create:
- source cards grid
- health indicators
- response time
- last checked timestamp
- total leads produced
- enabled/disabled state
- edit source slide-over
- test source mock action

## Runs page

Create:
- active runs section
- run history table
- progress bars
- status badges
- run detail log panel
- mock new run slide-over

## Rules

- mock data only
- slide-over, not full-page navigation, for edit flows
- status must use text + icon + color
- no native alert/confirm/prompt

## Acceptance criteria

- `/sources` and `/runs` look production-grade
- interactions are mock but believable
- no build/type errors
