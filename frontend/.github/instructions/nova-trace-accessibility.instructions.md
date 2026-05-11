---
name: "Nova Trace Accessibility"
description: "Accessibility rules for WCAG-friendly Nova Trace frontend."
applyTo: "**/*.{ts,tsx}"
---

# Nova Trace Accessibility Instructions

## Required

- Every icon-only button must have an `aria-label`.
- Every input must have a visible label or accessible label.
- Use semantic HTML before ARIA.
- Tables must use proper table semantics.
- Do not communicate status by color alone.
- Add text labels to status indicators.
- Keep focus outlines visible.
- Ensure dialogs, sheets, and command palette can close with Escape.
- Ensure tab order is logical.
- Respect `prefers-reduced-motion`.
- Do not make hover-only information critical.

## Avoid

- Do not use `div` as a button.
- Do not remove outlines without an accessible replacement.
- Do not make tiny click targets on mobile.
