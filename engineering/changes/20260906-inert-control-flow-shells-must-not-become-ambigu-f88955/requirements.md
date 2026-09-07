# Requirements — Inert control-flow shells must not become ambiguous-sensitive-shell or share one circuit-breaker objective

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Given a Bash inert read with `|`, `||`, `;`, or argument parentheses, when PreToolUse runs, then the decision is allow and the synthetic catch-all is not assigned.
- [ ] Given unproven control-flow (`eval`, `if/then git push`, `xargs git`, `git "$ACTION"`), when PreToolUse runs, then deny remains `ambiguous-sensitive-shell` or the classified action.
- [ ] Given two catch-all denials with different authority shapes in one session, when the second is recorded, then the objective breaker text is absent and each objective count is 1.
- [ ] Given two catch-all denials with the same authority shape, when the second is recorded, then the objective breaker fires and the exact-repeat text does not.
- [ ] Given two classified `external-write` curl POSTs, when the second is recorded, then the objective breaker fires.

## Failure and edge cases

- Unbalanced quotes, unfinished escapes, CDPATH, nested shells, unknown executables, and command-position dynamics fail closed (unproven).
- Empty unit after a proven `cd`/`pushd` skip is inert; empty command after unwrap is not.
- Ledger must not contain raw command text or secrets.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: fail closed on unproven shells; do not persist commands
- Reliability: existing deny tests unchanged
- Performance: single-command parse
- Observability: schema 3 ledger unchanged
