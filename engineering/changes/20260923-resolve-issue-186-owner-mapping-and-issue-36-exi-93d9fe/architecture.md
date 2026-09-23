# Architecture — Resolve issue #186 owner mapping and issue #36 exit-status disposition

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The repository owns Python verification and Trust CI command-result handling, which preserve explicit nonzero return codes. It does not own the reported `if ! cmd; then code=$?; fi` shell recorder.

## Proposed behavior

Repository-local disposition only: bind the absence and mappings in `evidence/owner-mapping.md`. Do not add a recorder or alter runtime behavior.

## Components and boundaries

Audit boundary: `.grok-stack/adaptive_grok/verification.py`, `.grok-stack/adaptive_grok/python_test_runner.py`, and `trust-ci/src/adaptive_trust_ci/sandbox.py` are inspected as existing owners. The absent shell gate remains outside this repository.

## Data flow

No data flow changes. Audit output flows only into the change package evidence.

## API and event contracts

None changed; no OpenAPI, event, SQL, or Trust CI deployed-policy impact.

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

No speculative owner is created. #36 requires an external authoritative repository/path/command/maintainer link before any fix.

## Risks and mitigations

Risk: the external issue may refer to another gate. Mitigation: retain separate issue scopes and require a concrete owner and reproduction before a future implementation.
