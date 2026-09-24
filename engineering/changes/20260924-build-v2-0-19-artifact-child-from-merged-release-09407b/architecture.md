# Architecture — Build v2.0.19 artifact child from merged release-sync 3f41be92

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The protected release-sync merge `3f41be92161fef451a2dfa7451eb458ce8f022b3` is the sealed source parent for v2.0.19. Its candidate state still marks the ZIP and sidecar absent because those bytes belong to a separate artifact-child. The published v2.0.18 tag, ZIP and sidecar remain immutable.

## Proposed behavior

Build the ZIP and sidecar twice from the exact tracked tree at the release-sync merge, compare the resulting bytes and digests, then add only that pair plus the state/documentation provenance needed to describe repository custody. Leave tag and GitHub Release publication for a later exact artifact-child merge.

## Components and boundaries

- Source parent: merged release-sync commit `3f41be92161fef451a2dfa7451eb458ce8f022b3`, tree `aed3246585fc6435463c3e3a58f1fe6a16070e6a`.
- Artifact: the two tracked package paths and their embedded manifest/source identity.
- Provenance: `PROJECT_STATE.json`, release docs, change package and coupled tests.
- Publication boundary: exact artifact-child PR head, protected merge, tag `v2.0.19` and GitHub Release are separate downstream steps.

## Data flow

`merged release-sync tree` → `private 0700 staging` → `build twice` → `byte/digest comparison` → `artifact-child PR` → `exact App-owned Trust CI check` → `protected merge` → `separate tag/Release actions`. No path writes to a service or host.

## API and event contracts

No product API, event schema or database contract changes. The package manifest and state fields are the existing release contracts.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: release-readiness, exact-SHA Trust CI, PR-only delivery.
- Applicable canonical example IDs/versions: v2.0.18 R/A/SR chain.
- Open or overdue debt IDs: operational pilot/M8/M9 remain unqualified and are outside this artifact-only change.
- Expected governance handoff or receipt impact: verification, security and release receipts bound to the artifact-child tree.

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

Preserve the two-stage R/A release chain. The ZIP digest is bound to the merged R tree; tag and GitHub Release are allowed only at the later exact merged A commit.

## Risks and mitigations

- Stale source: package only from the exact merged R commit and record its tree.
- Nondeterministic package: build twice in private 0700 staging and compare bytes/digests.
- Metadata drift: update state, docs and coupled tests in the same artifact-child PR.
- Overreach: prohibit deployment and keep external publication false until its separate grants/checks.
