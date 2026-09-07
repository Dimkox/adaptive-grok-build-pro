# Inert control-flow shells must not become ambiguous-sensitive-shell or share one circuit-breaker objective

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260906-inert-control-flow-shells-must-not-become-ambigu-f88955`
Created: 2026-09-07T01:28:59+00:00
Risk: low
Complexity: standard
Domains: generic

## Problem

PreToolUse promotes any Bash command with unresolved `|`, `||`, `;`, or parentheses to synthetic `ambiguous-sensitive-shell` when `sensitive_action` is None. Inert reads such as `ls | head` and `git log --format='%h (%s)'` therefore deny. The circuit-breaker objective fingerprint for that catch-all omits command identity, so a second unrelated Bash deny in 15 minutes is treated as a rewritten same-objective retry.

## Outcome

Proven inert read shells with control-flow remain soft (allow via `evaluate_pre_tool`). Unproven or classified sensitive commands stay denied. Distinct catch-all denials with different authority shapes do not trip the objective breaker; same-shape catch-alls and classified actions stay coarse.

## Scope

### In scope

- `is_proven_inert_read_shell` in `.grok/hooks/_lib.py`
- Promotion guard in `.grok/hooks/pre_tool_use.py`
- Secret-free `authority_shape` on catch-all objective fingerprints only
- Characterization tests in `tests/test_hooks.py` and `tests/test_pre_tool_circuit_breaker.py`

### Out of scope

- `policy.py` / `_policy_legacy.py` classifier changes
- Parsing `if/then` in `_command_directory_aliases`
- Schema-3 ledger field additions
- Factory, Pulse, Trust CI, GitHub App, PostgreSQL

## Constraints

- Backward compatibility: keep the control-flow regex and existing deny tests
- Data/privacy: no raw command, argv, URLs, or secrets in the denial ledger
- Performance: bounded quote-aware split of a single command string
- Operational: hooks remain fail-open if the policy stack cannot import
