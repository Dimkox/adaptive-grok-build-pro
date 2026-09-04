# M3 final release review

Status: **PASS — READY_FOR_FINAL_VERIFICATION**

- Role: route-selected independent `release_reviewer`
- Reviewed product SHA: `512ac3f2690d5489b5cf83020952dd9b685c2c37`
- Reviewed exact M2 stacked base: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Scope: release documentation, milestone boundaries, rollback, evidence topology, and compact repository status checks; no broad test suite or `grok_verify` was rerun

## Verdict

No blocking release-readiness finding remains for the M3 source candidate. It is ready for the planned report-inclusive final verification pass, but it is not ready to merge, publish, deploy, or promote to production.

## Release truth and identity

- `VERSION` is `2.0.12`, matching the README title and current-state identity.
- The README accurately describes M3 as a local source candidate and leaves final verification/receipts, PR delivery, the App-owned exact-SHA check, signed approvals, merge, and deployment pending.
- The README inventory graph is complete: 16 core nodes, 120 unique undirected `---` edges, no missing pair and no duplicate pair.
- `DARK_FACTORY_ROADMAP.md` does not overstate milestone completion. M3 checked items are explicitly source behavior only; authority-dependent candidate/example work remains open. M4 through M9 implementation work remains unchecked and dependency ordered.

## Scope and milestone boundary

- Git confirms the requested M2 base is the merge base of the reviewed product SHA.
- The M2-to-M3 tree adds governance contracts, bounded validation, receipt/architecture integration, installer distribution, tests, plans, and documentation. It adds no `factory/` runtime, provider adapter, new systemd unit, PostgreSQL control plane, credential handling, network client, autonomous external write, deployment, or production mutation capability.
- Existing `trust-ci/systemd/` files predate this M3 diff and are not changed by it. The M4 control-plane and provider-neutral factory files present in this branch are plans/specification only.
- The installer delivers the governance engine, CLI, and four schemas, while `TARGET_OWNED_GOVERNANCE` prevents all three mutable registry indexes from entering the managed payload.

## Package, rollout, and rollback

- The active route and durable package agree on route `35568941ae59`, change `20260826-m3-m9-production-delivery-continuation-355689`, high-risk AI/security scope, one `ai_implementer`, and four independent final reviewers. Their route snapshots differ only in the historical `updated_at` field.
- Acceptance criteria and tasks correctly leave the exact-fingerprint evidence gate open. `release.md` permits only a stacked M3 pull request after final local evidence; it does not claim a release or deployment.
- Rollback is forward-only: close the candidate PR or add a bounded revert before merge; after merge use a reviewed revert/forward-fix PR, preserve evidence, rotate affected governance digests, and renew all stale exact-fingerprint evidence. M3 has no database migration or production data recovery action.
- M4 may start only after the M1/M2/M3 handoffs, external Trust CI evidence, signed scopes, and M3 merge are current. M9 remains a later separately reviewed delivery milestone with signed artifacts, preview/staging checks, canary abort thresholds, exercised recovery, and human-owned production promotion.

## Review and fingerprint alignment

The three materialized peer reports all review product SHA `512ac3f2690d5489b5cf83020952dd9b685c2c37`:

- `m3-code-review.md`: PASS;
- `m3-test-review.md`: PASS;
- `m3-security-review.md`: PASS.

This release review inspects that same product SHA. The peer reports correctly treat earlier broad verification and coverage as historical rather than reusable final evidence. Their compact checks cover the repaired provenance, exact-head, schema-freeze, lifecycle, receipt, installer, and boundary risks without pretending that final verification has already happened.

The intended evidence topology is release-coherent and must be followed exactly:

1. Materialize all four final reports.
2. Have the sole write owner commit only the reports and truthful package/status updates.
3. On that clean report-inclusive HEAD, run exactly one final `python3 scripts/grok_verify.py --mode pr`.
4. Record `code_review`, `test_review`, `security_review`, and `release_review` receipts without changing the repository tree, so all five receipts bind one unchanged fingerprint.

The current `grok_status.py` gaps are expected before that sequence: verification is stale and all four final receipts are missing. Any tracked or untracked repository change after the final verifier makes the local evidence stale and requires renewal.

## External release boundary

Local PASS reports and receipts remain preflight evidence only. M3 merge eligibility still requires a pull request whose exact head SHA receives the App-owned `adaptive-trust-ci/verified@<policy-sha12>` check and every required independently signed approval scope under branch protection. Merge, tag, publication, deployment, and production promotion remain human-owned separately authorized actions.
