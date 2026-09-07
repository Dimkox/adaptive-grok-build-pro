# Architecture — Inert control-flow shells must not become ambiguous-sensitive-shell or share one circuit-breaker objective

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`_command_directory_aliases` marks raw `|/;/()` as `command.control-flow: <ambiguous>`. PreToolUse then assigns `ambiguous-sensitive-shell` whenever `sensitive_action` is None. Objective fingerprints for that action ignore command shape.

## Proposed behavior

Keep the control-flow regex. Add `is_proven_inert_read_shell` and withhold the synthetic action only when every unit is a closed inert read. Shape catch-all objectives with sorted authority-token presence plus optional `dynamic`. Classified actions stay coarse. Exact fingerprints stay byte-for-byte.

## Components and boundaries

- NODE-LOCAL-ROUTE-POLICY: `.grok/hooks/_lib.py`, `.grok/hooks/pre_tool_use.py`
- NODE-LOCAL-VERIFIER: hook tests only
- Out of domain: `adaptive_grok.policy`, factory, Pulse, Trust CI

## Data flow

Bash → root_context (still ambiguous) → sensitive_action → promotion exemption if proven inert → evaluate_pre_tool on session root. Denials record schema-3 evidence; catch-all objectives include `authority_shape` in the hash material only.

## API and event contracts

No public API change. Denial ledger schema_version remains 3 with no new keys.

## Governance context

- Applicable rule IDs:
- Applicable canonical example IDs/versions:
- Open or overdue debt IDs:
- Expected governance handoff or receipt impact:

## Bitrix-specific impact

- Modules/events/agents/components affected: none
- Cache and managed cache impact: none
- Installation/update/uninstall impact: none
- Core modification: forbidden unless explicitly approved.

## Decisions

1. Promotion exemption, not a root-resolution exemption.
2. Closed positive proof next to `_command_directory_aliases`.
3. Shape only `ambiguous-sensitive-shell`.

## Risks and mitigations

- Proof too wide: closed allowlist and unknown-executable fail-closed.
- Empty-shape collapse of unknown dispatchers: acceptable vs global catch-all.
- Residual over-deny of `git --no-pager log` and nested `bash -lc` with `;`: accepted.
