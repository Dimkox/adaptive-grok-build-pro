# Architecture — Implement the Factory v1.5 PR2 decision persistence contour on current main: transplant the five existing decision persistence commits from the isolated branch, resolve bounded API and data persistence conflicts, preserve behavior and tests, and deliver the isolated candidate

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Merged PR230 supplies canonical context contracts but no durable factual decision journal. The PR2 commits sit on an obsolete PR1 parent.

## Proposed behavior

Replay only those five commits onto current main. Migration 023 adds an append-only decision table and a fenced transition function that commits phase state, event, audit, command result and one supported decision together.

## Components and boundaries

- `DecisionRecordV1` plus its v1 JSON Schema: broad structural contract with narrower mandatory Python admission.
- Factory service/store: optional typed decision seam; HTTP `/v1/transitions` remains unchanged.
- PostgreSQL migration 023: runtime SELECT plus private function-mediated append, no raw mutation privilege.
- Persistence currently admits built-in state-transition records, empty evidence and unavailable context/profile digests.

## Data flow

Validated request and decision → fenced service transition → one PostgreSQL transaction → state/event/audit/command result/decision append → exact replay by request and decision digests.

## API and event contracts

No OpenAPI meaning changes. DecisionRecordV1 is a new JSON Schema sidecar with no authorization or external-effect semantics. Remote ingestion/read/export requires a later versioned API.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Applicable canonical example IDs/versions:
- Open or overdue debt IDs:
- Expected governance handoff or receipt impact:

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

- Preserve the bounded durable state-decision slice; do not inflate it into full U2/U3.
- Keep schema structural and Python admission semantic, with executable parity tests.
- Migration 023 is forward-only after application; never edit or down-migrate it.
- Keep Factory tests and the exact root discovery shim in one 800000-byte union
  budget; the recalibration is bounded to the measured migration-023 contour and
  retains the existing line, AST-complexity and error-severity guards.

## Risks and mitigations

- Schema/runtime drift: dependency-free schema parity plus semantic-only rejection cases.
- Restart loss: seed and verify exact digest/cardinality across two PostgreSQL restarts.
- Old-base contamination: replay exactly `fa49dc35..5c06cc14` onto `01b089fc` and compare patch IDs/diff inventory.
- Rollback mismatch: retain schema-23-capable code and disable the optional seam, or restore a separate compatible database.
- Governance rollback: revert the 800000-byte policy and its dependent PR2 test
  contour together; reverting only the policy recreates a known deterministic gate failure.
