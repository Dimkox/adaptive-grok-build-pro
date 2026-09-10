# Data architecture: M7 durable observation lookup

Route `18ea639b9d02`; base `64378d2`; design only, pending the named scope/design gate. Read the repository-explorer and architect reports, migrations 001/014/015/018, capability stores and restart-probe source. No product edit, test, database/service access, network call or secret access occurred.

## Existing data constraints

- `018_semantic_validation_bridge.sql:49` already binds a semantic subject to task/run/fence, repository, packet/manifest/result/terminal digests and exact base/input/result SHAs. Its verdict table allows one immutable verdict per subject (`:117`).
- `014_execution_plane.sql:64` gives one workspace result per run, with composite run/task and packet/run FKs. Use this chain and `semantic_execution_material` (`018:356`), not `tasks.current_run_id`: finalization clears the live lease pointer.
- Existing SQL capabilities use NOLOGIN/NOINHERIT roles, SECURITY DEFINER functions with a fixed search path, denied direct writes and immutable-record triggers. M7 should follow these patterns without granting runtime membership in observation roles.

## Minimal additive schema proposal

Add migration `019_m7_durable_evidence.sql`; five small relations keep producer identity, business outcome, technical check, current context and command replay separate. No changes to prior migrations or V1 bodies; no historical trust backfill.

| Relation | Exact keys and bounded payload |
| --- | --- |
| `factory.m7_bundles` | PK `bundle_digest`; unique registration identity through commands. Persist canonical V1 bundle body, repository, task/run/fence/generation, intent digest, profile digest, workspace-result digest, subject digest and verdict digest. FK `(run_id,task_id)` to runs; FKs to accepted-intent digest, result, subject and verdict with RESTRICT deletion. |
| `factory.m7_outcome_observations` | PK `observation_digest`; UNIQUE `(source_id,source_event_id)` and `(source_id,stream_key,source_revision)`. FK bundle digest; outcome digest/body nullable as a pair, decision `accepted/rejected/unknown/revoked`, source-authentication receipt digest, previous-observation digest, source time, database receipt time and optional superseded observation. A partial historic claim must not be coerced into complete `ShadowOutcomeV1`. |
| `factory.m7_check_observations` | PK `observation_digest`; same source-event/revision uniqueness. Bind repository/PR/base/head, App ID, epoch check name, policy digest, holdout binding when actually authenticated, job/check-run/attestation IDs, signed-envelope digest, conclusion, provenance receipt, source time, DB receipt time and externally bounded expiry. FK bundle digest if collected for a bundle; do not imply task acceptance. |
| `factory.m7_context_observations` | PK `observation_digest`; same source-event/revision uniqueness. Per repository/PR and authenticated context stream: current base/head/App/check-name/policy/holdout context digest, active/revoked/unavailable state, source-authentication receipt, previous observation, receipt time and expiry. This records observed current context independently of old successful checks. |
| `factory.m7_command_results` | PK `(source_id,operation,idempotency_key)`; canonical request digest, resource digest and bounded deterministic response. Insert atomically with the resource; identical replay returns original result, differing body is an integrity conflict. |

Every digest/identifier/body has a closed shape and byte limit matching existing conventions; canonical JSON and domain-separated hashes are recomputed in checked SQL functions and reparsed in Python. Deny UPDATE/DELETE on evidence and commands; represent revocation/supersession as new facts. Nullable authenticity/holdout fields mean unresolved evidence, never implicit validity.

Registration must verify all duplicated scalar values against the persisted completed writer-result/intent/semantic chain in one transaction. A pair of individually valid FKs does not prove their cross-binding: explicitly compare verdict.subject, subject.result, result.run/task, intent.repository/generation and every digest/SHA/profile value. Preserve input head versus produced head.

## Indexes and bounded lookup

- Bundle index `(repository_id,task_id,run_id,profile_digest,bundle_digest)`; direct bundle PK lookup remains the normal path. Do not impose one bundle per run: profiles or legitimately distinct canonical bundles must not collide.
- Outcome index `(bundle_digest,source_id,source_revision DESC,observation_digest)`; source stream key binds bundle and decision scope. Technical index `(repository_id,pr_number,base_sha,head_sha,policy_digest,source_id,source_revision DESC)` plus source-event uniqueness. Include App/check/holdout in comparison even if filtered after this narrow index lookup.
- Context index `(repository_id,pr_number,source_id,source_revision DESC)`; resolve the latest trusted context before comparing the requested epoch. Never select an old context by the caller's desired policy digest and call it current.
- Keep history reads optional and paginated; exact lookup fetches one bundle and a bounded set of configured-source heads. No JSONB-wide scans, unbounded artifact aggregation or dynamic timestamp predicates in partial indexes. Measure EXPLAIN plans with representative multi-repository fixtures before claiming scalability; no production volume is established yet.

## Transactions, replay and invalidation

Register using READ COMMITTED and a task-row share lock against concurrent cancellation/supersession, then validate immutable result/subject/verdict rows. Existing completed-run identity remains readable without a lease. Check current task generation/state again in each observation snapshot; never rewrite historical acceptance after a task becomes ineligible.

Serialize append operations per authenticated `(source_id,stream_key)` with transaction-scoped advisory locks (consistent order), then require the expected predecessor and a strictly newer authenticated source revision. Unique constraints are the final duplicate guard; a delayed older event cannot become current merely because its database receipt timestamp is newer. A local sequence is ordering bookkeeping, not proof that external events are fresh. If the source cannot prove ordering/current context, report unavailable instead of inventing revisions.

Lookup should be a single bounded SQL STABLE query returning one MVCC snapshot and DB-observed time. Alternatively use an explicit read-only REPEATABLE READ transaction solely for lookup; do not change existing READ COMMITTED mutation functions. Check receipt/source future skew, expiry with database time, revocation and latest context. A concurrent invalidation produces a snapshot valid only at its stated observation point, never a reusable permission token.

Base/head/policy/App/check-name/holdout replacement, missing source authentication, expired/revoked context, stale generation, outcome revocation or database outage returns a specific unavailable reason. Compare against independently observed current context rather than caller declarations. Store expiry as the tighter of authenticated source validity and configured maximum observation age; caller `now` cannot extend it. Database restart preserves source revisions, duplicates, expiry and revocations; no stale cache fallback.

## Capability and trust boundary

Propose separate NOLOGIN/NOINHERIT capabilities `factory_m7_registry`, `factory_m7_outcome_observer`, `factory_m7_check_observer`, `factory_m7_reader`. Registry resolves existing producers only; outcome observer appends business claims; check observer appends technical/current-context claims; reader only calls bounded lookup. Revoke direct table/sequence access and PUBLIC function execution; capability functions use `search_path=pg_catalog,factory`. Runtime receives none of the write capabilities.

Repository/source scopes must derive from externally configured authenticated principals, not a request's `source_id`; enforce scope at the checked function boundary. Default capabilities remain absent. Trusted acceptance acquisition and authenticated deployed-context acquisition are explicit future integration dependencies: persisted imported JSON remains an observation claim. Neither a dedicated DB role nor a successful insert authenticates a human decision or establishes current deployed Trust CI policy by itself.

The output is an additive digest-bound preflight observation only. Keep `ReadyForPrBundleV1`, M7/M8 availability false, V1 recommendations, L2 ceiling and M9 behavior unchanged. Revocations and full positive synthetic fixtures must never activate providers or authorize promotion, merge or delivery.

## Future validation and operations

- Add real PostgreSQL tests alongside `test_execution_persistence_postgres.py`: cross-FK substitution, canonical-body tampering, duplicate/collision, concurrent equal and conflicting appends, out-of-order events, source/repository scope and direct SQL privilege denial. Race task supersession and context replacement against registration/lookup and assert snapshot semantics.
- Extend the isolated `postgres_restart_probe.py` using its exact-container checks: persist a completed-run bundle after lease clearing, unknown/accepted fixture observations, source revision, revocation and replay response; restart PostgreSQL and recreate stores; verify exact digest/cardinality preservation and no revoked/stale result revival. Include an interrupted uncommitted append and an expired observation across restart.
- Add migration inventory/checksum/role-grant tests; empty additive tables need no backfill. Short metadata locks and role creation still need the named migration/external-write gate before live execution. Roll back by disabling capability injection; retain append-only evidence and migration history.
- Record bounded counters for lookup outcome/reason, stale/missing-source observations, replay/conflict, append latency and query time; no customer body logging. Reconciliation is an explicit bounded diagnostic, never an automatic authenticity upgrade.

Memory fact: durable currentness needs its own latest authenticated context stream; indexing old successful checks by requested policy cannot detect policy replacement. Immutable completed task/run/result bindings survive lease clearing, while imported or incomplete outcomes remain observations with unknown authority.
