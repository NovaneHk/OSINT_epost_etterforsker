# Nova Trace — Copilot Execution Pack v2 / 95+

Dette er en forbedret VS Code/GitHub Copilot-pakke for å bygge Nova Trace frontend på en kontrollert, testbar og skalerbar måte.

## Hva er forbedret fra v1?

v1 var sterk på P1-bygging. v2 løfter pakken mot 95+ ved å legge til:

1. API-kontrakter og fremtidig backend-klarhet
2. React Query/query-key plan
3. Teststrategi med Vitest og Playwright
4. Performance-budget og hardening-prompt
5. Copilot setup steps workflow
6. Sprint 1 GitHub issue-mal
7. Devil's advocate review-prompt
8. Mer presis “do not build”-styring
9. Mer detaljert P2/P3-roadmap
10. Acceptance matrix som kan brukes som kontrollskjema

## Filstruktur

```txt
.github/
  copilot-instructions.md
  workflows/
    copilot-setup-steps.yml
  ISSUE_TEMPLATE/
    nova-trace-sprint1.md
  instructions/
    nova-trace-frontend.instructions.md
    nova-trace-accessibility.instructions.md
    nova-trace-testing.instructions.md
    nova-trace-api.instructions.md
    nova-trace-performance.instructions.md
  prompts/
    01-nova-trace-analyze.prompt.md
    02-nova-trace-shell.prompt.md
    03-nova-trace-data-model.prompt.md
    04-nova-trace-dashboard.prompt.md
    05-nova-trace-leads.prompt.md
    06-nova-trace-api-client-ready.prompt.md
    07-nova-trace-tests.prompt.md
    08-nova-trace-performance-hardening.prompt.md
    09-nova-trace-command-palette.prompt.md
    10-nova-trace-sources-runs.prompt.md
    11-nova-trace-analytics-reports.prompt.md
    12-nova-trace-qa-hardening.prompt.md
    13-nova-trace-devil-advocate-review.prompt.md
docs/
  nova-trace-frontend-spec.md
  nova-trace-api-contract.md
  nova-trace-react-query-plan.md
  nova-trace-testing-strategy.md
  nova-trace-performance-budget.md
  nova-trace-p2-p3-roadmap.md
  nova-trace-acceptance-matrix.md
  nova-trace-do-not-build.md
  nova-trace-sprint1-issue.md
scripts/
  nova-trace-qa-checklist.md
  validate-nova-trace.md
AGENTS.md
```

## Bruk i VS Code

1. Pakk ZIP-en ut i prosjektroten.
2. Åpne prosjektet i VS Code.
3. Åpne Copilot Chat i Agent mode.
4. Kjør:

```txt
/01-nova-trace-analyze
```

5. Når analyse er ferdig, kjør i rekkefølge:

```txt
/02-nova-trace-shell
/03-nova-trace-data-model
/04-nova-trace-dashboard
/05-nova-trace-leads
/06-nova-trace-api-client-ready
/07-nova-trace-tests
/08-nova-trace-performance-hardening
/12-nova-trace-qa-hardening
/13-nova-trace-devil-advocate-review
```

## Streng regel

Ikke kjør hele produktet i én prompt. Det er sånn man får en nydelig frontend med bærende konstruksjon laget av våt knekkebrød.
