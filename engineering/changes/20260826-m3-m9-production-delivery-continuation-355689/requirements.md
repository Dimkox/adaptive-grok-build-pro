# Requirements — M3-M9 production delivery continuation

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] M3 strict schemas, bounded loader, lifecycle, conflict, example/debt semantics, exact handoff, architecture fitness, receipts, installer behavior, and docs pass their focused tests.
- [ ] Agent-authored governance can remain only a candidate; activation requires independent review and explicit human governance approval.
- [ ] M3 emits no factory runtime, provider execution, systemd, credential, network, Trust CI mutation, or external write capability.
- [ ] Final M3 evidence binds the same exact fingerprint across verifier and code/test/security/release reviews.
- [ ] M4 cannot start unless the M1/M2/M3 handoff contracts and required external authority evidence are current.
- [ ] M9 remains a later separate milestone: exact merged SHA, signed manifest, deterministic preview/staging checks, explicit canary abort thresholds, exercised rollback, and human production promotion.

## Failure and edge cases

- Missing binding spec, unknown contract versions, duplicate IDs, unsafe paths, symlinks, read mutation, stale evidence, ambiguous lifecycle transitions, or conflicting active rules fail closed.
- Uncommitted M3 candidate files are treated as untrusted work until tests, review, and commits establish provenance.

## Non-functional requirements

- Security: no agent self-activation, no secrets/raw reasoning, no autonomous external or production writes.
- Reliability: deterministic canonical digests, exact-SHA handoff, forward-fix rollback, stale receipt invalidation.
- Performance: explicit document/node/depth/record/evidence bounds from the M3 plan.
- Observability: structured governance findings and exact digests; later milestones add correlated queue/lease/cost/canary metrics.
