# Release plan — production-only human approvals

## Deployment

Keep M2–M9 stacked and unmerged while all local and isolated automated evidence is produced. Freeze one final integration PR and artifact input set; no external migration, service rollout, approval or policy change occurs before the final production go/no-go.

The single final ceremony is ordered: automated-green exact PR head; human old-policy approval for that PR; deterministic merge; authoritative merged-commit/artifact attestation; human `promotion:production` envelope; atomic consume and exact-artifact deploy; successful deployment evidence; activation and proof of the new no-interactive-change-validation policy epoch. The two cryptographic envelopes are sequential actions in one human gate/session.

Repository changes do not execute that ceremony. Operators record exact base/head/merged SHAs, image/artifact digests, migration checksums, old/new policy digests and App check identities, promotion/operation/audit IDs, command results and rollback evidence.

## Feature flags / staged local proof

Independent switches default off for merge ingestion, exact-SHA validation, promotion acceptance and consumption, plus a global kill switch. Tests progress through `off -> shadow -> deny-only -> enforced` against ephemeral/local dependencies; production remains unchanged until the final ceremony.

## Metrics and alerts

Monitor pending merge age, reconciliation lag, validation outcomes, accepted/rejected/replay/expired counts, consume latency, dependency errors, accepted-without-consume, consumed-without-terminal-event and audit failures.

## Go/no-go criteria

- All P0 evidence and five route reviews pass on one fingerprint.
- Ephemeral migration, roles, query plans, restart/restore, local shadow/deny-only and rollback drills pass.
- Final integration PR and deployment artifact inputs are immutable and automated-green.
- The human explicitly starts the one final ceremony; there are no earlier human/chat gates.
- New App-owned epoch check is observed after successful deploy and before protection replacement.
- No-go on mutable provenance/artifact, missing audit, replay, key exposure or weakened automated controls.

In `change-spec.yaml`, `release` is the existing contract alias for this sole final production-boundary ceremony. Ordinary change validation has no manual `release` gate; runtime authorization uses `promotion:production` immediately before consume/deploy.

The executable M2–M9 sequence, command-level evidence, producer-consumer preflight, and final exact-fingerprint review handoff are maintained in `docs/superpowers/plans/2026-08-30-production-only-human-approvals.md`.
