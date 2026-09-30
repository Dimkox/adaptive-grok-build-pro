# Requirements — Factory Linux installer from Liqvera prototype

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Tampered, unsafe, mismatched, incomplete, or extra archive entries are rejected before target mutation.
- [ ] Unsupported host/profile, unsafe root, occupied port, missing resource, or missing daemon capability fails read-only with guidance.
- [ ] A verified candidate is staged under an immutable digest identity and `current` switches atomically only after health succeeds.
- [ ] Interrupted/failed candidates preserve the prior active release and can be reconciled without blind migration replay.
- [ ] Update/reversal fails closed without backup and schema-compatibility evidence; no down migration runs.
- [ ] Default removal stops runtime but preserves configuration, logs, backups, and volumes; destructive purge needs an exact bound token.
- [ ] Existing source installer behavior and factory/L5/Trust-CI boundaries remain intact.

## Failure and edge cases

- Traversal, symlink/hardlink/special entries, duplicate paths, same-key/different-content replay, stale pointers, partial state, and secret-bearing output.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: confined roots, no implicit privilege or package-manager actions, exact digest verification.
- Reliability: lock, durable state, atomic writes/pointer, idempotency, reconciliation.
- Performance: finite file/count/byte/time limits.
- Observability: operation ID, phase, candidate/prior identities, health/backup/compatibility status.
