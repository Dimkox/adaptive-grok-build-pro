# Architecture — Consolidate repository-owned remaining issue fixes into one bounded batch from current main, preserve external blockers, run one final PR verification and prepare one successor PR

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The repository contains a Trust CI policy example and a dated L5 runtime
observation. Before this slice, the example marker and prose could be read as
policy-shaped evidence without a structure assertion for the full authority
boundary; the runtime observation already contains the provider-probe limit,
but that distinction was not protected by a named structure test.

## Proposed behavior

The example declares `authority: illustrative-example-only`; README prose says
that the checked-in example cannot install approval scopes, change branch
protection, or satisfy the App-owned check. The server-mounted policy epoch
and exact App-owned Check Run are authoritative. The L5 runbook and tests
separate operator-attested/non-re-derivable provider probes from durable pilot
job evidence.

## Components and boundaries

- `trust-ci/config/policy.example.json`: illustrative configuration shape.
- `trust-ci/README.md`: repository-facing Trust CI boundary explanation.
- `engineering/runbooks/l5-runtime-observation-2026-09-15.md`: dated,
  operator-safe observation with explicit evidence limits.
- `tests/test_structure.py`: read-only assertions over those source-owned
  boundaries.
- Deployed Trust CI, external holdout, provider, host, and human approval
  systems: outside the repository change boundary.

## Data flow

No data flow changes. The structure tests read committed JSON/Markdown only;
no API, event, database, or provider call is introduced.

## API and event contracts

No API, event, OpenAPI, or async-message contract changes.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: deployed Trust CI policy/check authority remains
  external; local example and receipts are non-authoritative.
- Applicable canonical example IDs/versions: policy example schema version 1;
  no deployed epoch is claimed.
- Open or overdue debt IDs: external issue seams remain open/documented.
- Expected governance handoff or receipt impact: final local verification and
  two review receipts must bind to the final tree fingerprint.

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

- Keep this slice source-only and documentation/structure-test bounded; a new
  durable provider-observation API would exceed the evidence correction.
- Preserve external blockers #39 and #48 (and other absent seams) rather than
  creating speculative code.

## Risks and mitigations

- Risk: a reader infers deployed authority from a policy-shaped example.
  Mitigation: explicit marker, README boundary, and structure assertions.
- Risk: live probe output is treated as re-derivable durable evidence.
  Mitigation: runbook wording plus structure assertions.
- Risk: local receipts are stale after a tree edit. Mitigation: run verifier
  and reviews only after the final source/package freeze.

## Bounded implementation decision

This candidate changes only repository-owned authority wording and runtime evidence semantics. It does not modify deployed Trust CI policy, external holdouts, provider services, or user-level shell tooling. #39 and #48 remain explicitly external because no matching implementation exists in this tree.
