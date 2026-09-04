# Architecture — M6 bounded semantic validation on exact M5 85cd434

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Exact M5 `85cd4343143915ce9342634e7fe81886b6394871` provides the complete M4 control plane plus disabled-by-default bounded execution, immutable workspace results, migrations `001`-`017`, disjoint runtime/attestor capabilities, atomic terminalization, and factual restart recovery. It has no integrated semantic verdict or repair lifecycle.

## Proposed behavior

Add M6 as a narrowing layer over immutable M5 results. A coordinator publishes an exact semantic subject, an independent validator submits typed evidence, and an adjudicator recomputes a deterministic verdict. A repair verdict may reserve one exact child proposal for cycles one through three; unsafe or fourth-cycle input escalates without child creation.

## Components and boundaries

- `semantic_contracts.py`: closed canonical value objects and digest domains.
- `semantic_bridge.py`: exact M5 result-to-subject and execution binding derivation.
- `semantic_adjudication.py`: deterministic verdict computation from typed evidence.
- `semantic_repair.py`: bounded repair policy and exact child directive construction.
- Migration `018`: append-only semantic facts, three disjoint capability roles, narrow security-definer functions, fixed metrics, and exact lookup indexes.
- Existing model/store/service/API/server/admin/settings layers receive additive semantic seams; all M5 behavior remains authoritative.

## Data flow

M5 workspace result and frozen authority -> semantic subject -> validator assignment -> typed findings and coverage -> deterministic verdict -> pass, `needs_human`, or bounded repair directive -> reserved repair broker -> ordinary M5 intake with exact parent lineage. No semantic component edits a workspace or invokes a provider.

## API and event contracts

Seven JSON Schemas are enrolled as closed version-1 contracts. Six authenticated semantic operations are added to the existing control contract: publish/get subject, create assignment, submit evidence, adjudicate subject, and get verdict. Existing M4 control and M5 execution contracts are unchanged.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: architecture ownership, contract compatibility, capability isolation, data immutability, bounded AI evidence, and migration sequencing.
- Applicable canonical example IDs/versions: canonical M6 final semantic source at `2d2360cd6f2a19ad3328d468073a52927691b112`.
- Open or overdue debt IDs: none introduced within the bounded source scope.
- Expected governance handoff or receipt impact: later exact-head verification and route-selected reviews must bind the final descendant of `85cd434`; canonical receipts do not transfer.

## Bitrix-specific impact

- Modules/events/agents/components affected: not applicable.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: additive unpublished migration only; no activation authorized.
- Core modification: forbidden unless explicitly approved.

## Decisions

- Current M5 is the merge skeleton; canonical M6 is semantic source only.
- Canonical SQL body is preserved byte-for-byte and renamed from `014` to `018`.
- The stricter invariant from either milestone wins at every overlapping seam.
- No provider-specific behavior or additional service is introduced.

## Risks and mitigations

- Lineage or capability confusion: exact cross-binding and disjoint role validation fail closed.
- Partial semantic outcomes: append-only facts and one-verdict/one-child uniqueness provide atomic replay.
- Repair loops: cycles are closed to 1-3; the fourth request persists escalation only.
- Migration drift: immutable prior bytes, checksum discovery, transactional application, and schema-17 rollback evidence.
