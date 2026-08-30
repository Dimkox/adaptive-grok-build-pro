# Documentation analysis — production-only human authorization

Route: `75aa6daa89b1`
Role: `docs_researcher` (read-only except this report)
Decision supplied by the user: after a safe migration, interactive human authorization occurs only at production promotion; pull-request/change validation remains automatic and exact-SHA/App-owned.

## Binding documentation constraints

- `AGENTS.md` and `README.md` make the deployed GitHub App Check Run `adaptive-trust-ci/verified@<policy-sha12>` on the exact PR head SHA the merge authority. The new flow must not weaken the exact-SHA checkout, external holdout, source-mutation detection, signed attestation, App identity binding, or branch protection.
- Human private keys remain outside the repository, CI host, API/worker checkout, and agent environment. The production endpoint may verify an Ed25519 envelope using API-mounted public keys; agents still must not create, read, request, submit, or simulate the human private key or signature.
- The deployed policy, holdout, images, PostgreSQL, trust store, keys, and branch protection are outside the PR trust domain. Repository `policy.example.json` documents the intended next policy but cannot itself switch the live gate.
- `README.md` has a mandatory current-state section and complete core-node graph. Keep the promotion endpoint inside the existing Trust API and its durable records inside the existing Postgres node unless a genuinely separate deployed component is introduced; that avoids falsely adding a new core service/node. If a new node is added, it needs `---` edges to every existing core node.
- Historical specs are evidence of the old design and should not be silently rewritten as if they always described the new contract. Add a dated supersession note or a new ADR/spec, then update operator/current-state documents.

## Contract and migration conventions to preserve

- Signed payloads are immutable, canonical-JSON dataclasses with explicit `schema_version`; unknown versions fail closed. Define a distinct `PromotionPayloadV1`/`PromotionEnvelopeV1`, not a semantic extension of PR-bound `ApprovalPayload` v1.
- V1 must state exact field syntax and semantics: `promotion_id`, repository, exact merged commit SHA (current repository convention is 40 lowercase hex), artifact SHA-256 (64 lowercase hex), target environment, policy digest/epoch, actor, key ID, nonce, `issued_at`, `expires_at`, optional bounded reason, and signature over canonical payload only. Do not call a branch, PR head, tag, mutable image tag, or local tree fingerprint an "exact merged commit/artifact".
- Document server-side verification order and stable HTTP outcomes: malformed/unsupported version; unknown/revoked/wrong-scope key; signature failure; future/expired/excess-TTL envelope; policy-epoch mismatch; commit not proven merged; artifact mismatch; unauthorized environment; duplicate `promotion_id`/nonce or exact replay; durable-state failure. All authorization failures are fail-closed and must not mutate production.
- `POST /promotions` needs an explicit idempotency contract. A nonce/promotion ID is single-use globally (or under a precisely documented namespace); replay is rejected atomically in PostgreSQL. State whether a retry of the byte-identical accepted request returns the original record or `409`; tests and runbook must use the same rule.
- Audit events are completed business facts with a versioned payload, not internal steps. Specify event names and fields for accepted/rejected promotion, actor/key ID, repository/commit/artifact/environment/policy epoch, correlation ID, reason code, timestamp; exclude signatures, private material, bearer tokens, and unbounded request bodies.
- PostgreSQL migrations are packaged, contiguous, checksum-locked files named `NNN_lowercase_name.sql`, applied transactionally under the migrator advisory lock. Every deployment copy under `trust-ci/sql/` must byte-match the corresponding packaged file under `trust-ci/src/adaptive_trust_ci/resources/` (current `001`–`003` pairs match). Additive schema/index changes should be forward-compatible; never edit an applied migration.
- Document unique constraints/indexes supporting promotion ID/nonce replay rejection and lookup/reconciliation, foreign-key/delete behavior, retention, expected volume, and role grants. API/worker/migrator/backup least-privilege separation must remain truthful after the new table/API writes.

## Existing text that conflicts with the approved policy

These describe interactive PR approvals and must be superseded only after the production gate is deployed, proven, and the live policy/branch-protection epoch is migrated:

- `trust-ci/README.md`, **Human security approvals**, currently documents PR/base/head/scope approvals submitted to `/approvals` and exact-SHA requeue.
- `engineering/runbooks/trust-ci-rollout.md`, proof step 9, currently requires a `trust-ci/**` diff to enter `action_required`/`needs_approval`.
- `trust-ci/config/policy.example.json` currently maps governance, database, and production path globs to `approval_rules`.
- `README.md` currently says change validation "checks signed human approval scopes" and that the human owns production promotion without documenting a production promotion envelope.
- `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md` and `2026-08-24-m0-live-trust-authority.md`, plus their plan documents and `GROK_BUILD_HANDOFF.md`, freeze/history-record PR approval behavior. Mark those sections superseded for current operation; retain their historical facts.
- `DARK_FACTORY_ROADMAP.md` has M0 acceptance items for protected-path `needs_approval`. Preserve them as historical M0 proof, but update the current roadmap dependency/current-state wording so they are not interpreted as the desired post-migration pipeline.
- `AGENTS.md` repeatedly treats signed approvals as part of merge trust. It needs a narrowly reviewed contract update distinguishing automatic change validation from human-signed production promotion. Keep its bans on key access/signing by agents and its explicit approval requirement for destructive migrations/irreversible production actions.

`engineering/runbooks/protected-control-plane-write.md` describes repository-local delegated grants for local protected-path edits, not Trust CI interactive approvals. Do not conflate or delete that mechanism unless local hook policy is separately changed.

## Exact documents to update

1. Add a new ADR under `engineering/adr/` (the directory is currently empty except `.gitkeep`) recording the two-phase trust model, why PR approvals are removed, immutable promotion contract, boundaries, and migration/rollback decision.
2. Fully populate this change package: `brief.md`, `requirements.md`, `architecture.md`, `test-plan.md`, `release.md`, `rollback.md`, `tasks.md`, and `change-spec.yaml`. They are mostly generated placeholders now and cannot support implementation or approval.
3. Update `trust-ci/README.md` with `POST /promotions`, the V1 envelope and error/idempotency semantics, public-key-only verification boundary, audit/retention, CLI/operator flow, backup/recovery, and a clear statement that `/approvals` is legacy/disabled for change validation after cutover.
4. Update `engineering/runbooks/trust-ci-rollout.md` with shadow deployment, migration status, PostgreSQL concurrency/replay proof, production no-op/canary proof, policy-epoch switch, branch-protection verification, and the order for disabling PR approval rules. Add a dedicated production-promotion runbook if operational detail would overload this file.
5. Update `trust-ci/config/policy.example.json` only after the gate is ready: no change-validation path may require an interactive scope; production target/key/TTL/epoch controls must be separately named rather than expressed as changed-file globs.
6. Update `README.md` current state/components/version wording and graph only to match the final tree. Preserve the exact App-owned PR-check statement and explicitly say human authorization is evaluated at production promotion, not PR validation.
7. Update `AGENTS.md`, `START_HERE.md`, `QUICKSTART.md`, `GROK_BUILD_HANDOFF.md`, and applicable roadmap current-state/dependency text so no live instruction tells agents to wait for a PR approval. Keep historical activation reports factually dated.
8. If Trust CI service identity changes, update `trust-ci/pyproject.toml`, `trust-ci/src/adaptive_trust_ci/__init__.py`, API version, image defaults/docs together. Do not confuse Trust CI `2.1.0` with root product `2.0.12`.

## Truthful staged rollout and rollback wording

- Phase A: deploy additive schema and endpoint while existing PR approval rules remain active; verify health, migration checksums, key/trust-store readiness, audit events, atomic replay rejection, backups, and a non-mutating production-target dry run.
- Phase B: prove a real human-created V1 envelope authorizes only its exact merged commit + artifact digest + environment + deployed policy epoch and that all mismatches/replays fail closed. This is the named `migration_or_external_write_approval`; no agent signs or submits it.
- Phase C: deploy a new server policy epoch with empty/no interactive change-validation approval rules, observe the new App-owned exact-SHA check on a disposable PR, then update branch protection to that exact check name/App ID. Never remove the old required check before the new one is observed.
- Rollback before Phase C: revert service image; additive unused tables may remain. Rollback after Phase C: restore the previous reviewed image/policy epoch and old exact App-owned required check in the documented safe order. Production promotion must fail closed while the endpoint, database, trust store, artifact verifier, merge-proof provider, or active policy epoch is unavailable; rollback must never mean accepting unsigned/manual agent assertions.
- The release document must not claim that repository changes deployed the policy or production gate. Record exact operator evidence separately: image digests, migration registry/checksums, policy digest/check name, branch-protection App ID, promotion audit record, restore/replay drill, and rollback command/results.

## Documentation go/no-go

No-go if any current operator document still requires a PR human approval after cutover, if `/approvals` and `/promotions` are ambiguously interchangeable, if a promotion can reference an unmerged/mutable artifact, if policy removal precedes proven production authorization, or if docs imply an agent/repository possesses the signing key. Go only when API/event/data contracts, phased migration, rollback ordering, and exact live evidence are all documented and mutually consistent.
