# Static data integration analysis

Role: selected `data_architect`; route `8b2ee0533ba5`; September 21, 2026.

The exact issue163 candidate can be imported without a new data design change.
I found no additional data blocker in the proposed composition. The execution
persistence test file must retain the issue163 version, which includes the
issue166 prerequisite and extends its upgrade proof for022. PR173 delivery and
fresh verification of the resulting combined tree remain outstanding dependencies.
This report does not establish that PR173 has merged or that this successor has
passed verification, review, external CI, or deployment.

## Inputs and independent identity checks

- Integration manifest: `../candidates.json` and
  `issue163-prefix-integration-proposal.md` in this evidence directory.
- Issue163: `d80c5c8d8e5afe938d195401715daf5e69192a81`, inspected in
  `/home/pall/grok-projects/adaptive-grok-build-issue-163`; its worktree was clean.
- Prepared PR173 head: `23984e55560c6d559a46445061f10331ca05bcf9`.
- Shared source base: `839d3aa26bc90417424d814ee48d8b5cd3be367e`.
- Original issue166 prerequisite: `23eb62dc21a090e6bf086cbc2a568d83417b0a2e`.

All seven issue163 paths matched the manifest's SHA-256 values. In particular,
resource022 is `3bd08d907c538ab3964727fdca91eb35565821889d1999da8fcba1278613267d`;
the resolved test file is blob `069af430af09598fe70d81a17e64a20a0bd74369`,
SHA-256 `62ad6b546dc4e6c8f0a7f2b6d0023fe2178b254d97bf5282481474db797ca47b`.

Git confirms issue166 is an ancestor of issue163. Its execution persistence test
file and PR173's file have no difference; the latter is blob
`501f5203d3eb97bba19c382b47a8d45f5526ac61`. The diff from that blob to issue163
adds semantic fixtures, plan-function snapshots, the historical021 case, and022
expectations. The inherited drift and advisory contention scenarios remain.
Selecting the older PR173 block would discard coverage; no new resolution hunk
is required for the proposed candidate.

## SQL and store boundary

`factory/src/adaptive_factory/resources/` differs from prepared PR173 only by
the additive022 resource: every existing001–021 file is unchanged. I also
extracted the actual018 and022 `semantic_plan_repair` bodies with `sed` and
compared them with `diff` after reversing only `CREATE OR REPLACE` and the
plan-refusal expressions to their original `NULL` values. The comparison was
empty, exit0. This was a static text comparison, not a test or SQL invocation.

The existing offline regression in `factory/tests/test_migrations.py:887`
independently freezes the018 function hash and requires all15 substitutions,
their ordered14-reason vocabulary, both idempotency lookup arms, and exact
reversible body equality. Resource022 retains the signature, `SECURITY DEFINER`,
fixed `pg_catalog,factory` search path, PUBLIC revocation, and coordinator EXECUTE
grant. It introduces no table, index, backfill, schema payload, query predicate,
row-lock, or query-plan change. Table-volume assumptions are consequently unchanged;
the existing bounded migrator still serializes on its advisory transaction lock.

The new reader at `semantic_repair.py:108` accepts only a one-key
`repair_plan_rejection` mapping. Known reasons are fixed local vocabulary;
unrecognized values become `planning_rejected`, without echoing stored text.
Mixed envelopes, the child-refusal channel, and invalid lifecycle documents
continue to the existing corruption path. The successful lifecycle contract and
subject/verdict/cycle, child, and escalation request-binding checks are unchanged.

At `store.py:681`, both connection and transaction contexts finish before
classification. This matters: a normal SQL return from a child conflict can
retain an earlier directive insert, whereas the existing SQL exception arm
rolls that insert back. Moving classification inside the transaction would
change this behavior. The candidate explicitly tests both outcomes in
`test_postgres_integration.py:5797` and `:5826`, plus the post-context placement
in `test_semantic_repair_lifecycle.py:616`.

Deadline exhaustion remains a persisted `needs_human` escalation, not a planning
refusal. The real-server deadline scenario retains a matching successful replay
after expiry and checks the original response/timestamp, then persists/replays a
new escalation. The synchronized second-lookup tests observe an actual subject
lock wait before committing the matching or conflicting first result. They
retain the stored row and distinguish replay from `idempotency_conflict`.

## Prefix preservation and migration behavior

The proposal accurately describes the inspected fixture:

- `create_populated_current_prefix` applies actual001–014 and actual subsequent
  packaged SQL through the previous version, with authentic name/hash ledger
  rows, then admits real execution and semantic success/escalation records.
  It does not fabricate an already-migrated ledger.
- The current path is001–021 to022. The historical test passes the actual first21
  packaged resources to the real migrator, preserving the020 to021 transition
  after022 becomes current.
- Before either replacement, the relevant function's NULL behavior is observed
  through the coordinator role. Afterward, it must emit the named input refusal.
- Snapshots cover both child and plan function OID, owner, sorted ACL,
  `SECURITY DEFINER`, search path, definition, and effective EXECUTE rights for
  coordinator, validator, adjudicator, and runtime roles. Only the designated
  function body may differ. Nonempty fixtures retain exact complete before/after
  equality for all16 sampled execution/semantic tables, including command
  results, directives, child proposals, and escalations.
- Existing ledger name/hash/version/timestamp values remain exactly equal;
  only the final real migration row is added. Reapplication returns an empty
  tuple and must leave the complete snapshot unchanged.
- Real recorded-ledger drift must fail without mutation. Advisory contention
  observes a blocked backend, then tests release-to-success and timeout-to-
  rollback followed by retry. The code retains5-second DB bounds, a12-second
  join, a15-second elapsed ceiling, and cleanup scoped to a unique application
  identity. It does not infer a function invocation holds an ACCESS EXCLUSIVE
  migration lock.

The larger fixture legitimately changes the old assertion of exactly one row
per execution table to nonempty rows. Exact full row equality before and after
the migration remains, so that adjustment does not weaken data-preservation
evidence. The other two candidates do not touch factory SQL or these fixture
paths according to `candidates.json`.

## Remaining dependencies and evidence limits

1. Wait for actual PR173 delivery and compare its merged product bytes with the
   named prerequisite. A changed prerequisite requires this resolution to be
   reconsidered. Preserve the exact issue163 file and all seven manifest hashes
   unless a newly reproduced defect justifies returning work to the sole writer.
2. Run the complete combined verification after import, including real PostgreSQL
   historical/current prefix, drift, contention/retry, permission, deadline,
   exception, and both second-lookup scenarios. Obtain every review selected by
   the new route afterward. Candidate reports and this static analysis are not
   current-tree verification receipts.
3. Keep previous evidence truthful: the first12-scenario focused PG command had
   one fixture error; its corrected deadline scenario passed separately. The
   earlier full gate was overall FAIL because of architecture/governance, even
   though its PostgreSQL section passed. These records must not become an
   asserted successful combined gate.
4. Do not claim runtime coverage of every reason. Existing referential/typed
   producers prevent the chosen valid fixtures from reaching
   `execution_material_missing`, invalid baseline risk, and NULL deadlines.
   Their preservation is supported by frozen body/site proof; the documented
   limitation remains. No need to disable production constraints to manufacture
   reachability for this representation-only change.
5. Source delivery does not apply022. `store.py:1325` requires the database
   migration version to equal the packaged migration count; readers accepting
   legacy NULL do not make an old/new rolling deployment readiness-compatible.
   Any later authorized rollout needs coordinated drain/update, prefix/hash and
   readiness readback, and bounded stop/retry on timeout or drift. After022 is
   committed, recovery requires a later forward migration and a compatible
   package. Reverting source alone or deleting ledger rows is not recovery.

Observable scope is the bounded store-level refusal reason, preserved lifecycle
results, readiness, and migration outcome. The public API still emits its fixed
409 `store_conflict` response (`api.py:384`); this change does not add reason text
to HTTP responses or new metrics. No production readiness, latency, data-volume,
or post-deployment success claim follows from this report.

## Work performed

Only Git/text reads, SHA-256 calculations, and the static function-body comparison
were performed. No tests, lint, compilation, product imports, Docker, migrations,
network mutation, receipts, commits, or source edits were executed. The sole
write is this report. Coordinator memory fact: preserve the issue163 test blob
when adopting PR173, because it retains both the historical021 replacement proof
and the current022 upgrade contract without changing immutable SQL.
