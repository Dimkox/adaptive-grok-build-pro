# Architecture — Fix governance and architecture Git input hardening: explicit repository object binding, controlled Git environment, filter-free committed reads and pinned bounded regular-file projections.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Architecture already has a controlled bounded Git runner and regular-file guards; governance's private Git reader inherits the environment and buffers output before applying a cap. Fixed projection inputs are read through mutable names twice. Current governance authority topology is descriptor-pinned and must be preserved.

## Proposed behavior

Resolve the worktree registration before Git operations, validate its natural root relationship, registered linked-worktree backlink and common-directory relationship, then invoke bounded Git with explicit directory/worktree flags and the controlled environment. Pin registration identities before reading; refuse common-directory redirection for ordinary repositories and require the canonical common/worktrees relationship for linked roots. Full native object IDs must identify existing commits; raw cat-file blob reads never run filters. Governance refuses configured filters before status can execute clean drivers and keeps clean/current-HEAD checks.

Projection snapshots reuse existing pinned regular-file helpers, retain descriptors and observed content, share the recorder byte budget, and recheck identity/content/root immediately before the CLI emits. Handoff rechecks authority and consumed bytes independently of status, which can hide assume-unchanged paths.

## Components and boundaries

Only architecture_diff.py, governance.py, scripts/grok_governance.py and tests/test_governance.py change as product. A/D helper consumers retain signatures and batching. No API/schema/runtime/deployed policy edits.

## Data flow

Validated root/registration -> controlled explicit Git invocation -> exact native commit -> regular raw blob -> existing governance validation -> final authority/consumed-input recheck -> frozen v1 handoff. Fixed Markdown files -> pinned bounded snapshot -> merge/digest in memory -> final snapshot recheck -> unchanged CLI JSON shape.

## API and event contracts

No new event/HTTP contract. New optional helper parameters preserve callers. SHA-256 architecture objects are supported; GovernanceHandoffV1 remains SHA-1-only and explicitly refuses SHA-256 rather than changing its schema.

## Governance context

Canonical governance JSON is repository evidence and cannot confer externally verified activation or acceptance. No independently verified rule authority channel exists in M3, so active repository claims are not effective.

- No registry/debt/example bytes change. Handoff and local receipts retain their existing shapes and never authorize merge.

## Bitrix-specific impact

- Not applicable to this generic repository contour.
- Core modification: forbidden unless explicitly approved.

## Decisions

Preserve current stronger topology and clean/current-head gates; do not copy the historical draft's relaxed dirty-state behavior. Reuse the bounded runner and authority reader rather than replacing them. Snapshot-backed check-projections compares the same observation as project.

## Risks and mitigations

More Git validation adds bounded local subprocesses; batching remains intact. Linked roots require matching registration/backlink/common-directory and unsupported unregistered Git pointers fail closed. Direct character-device node creation is not exercised by an unprivileged fixture; device symlinks, FIFOs and an actual /dev/null descriptor supplied to the pinned reader are refused. Independent controller verification and review assess aggregate compatibility.
