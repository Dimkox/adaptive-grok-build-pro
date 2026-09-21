# Issue #163 implementation checkpoint

The selected `data_implementer` owns these edits. Coordinator-owned handoff files,
route, Git HEAD and operational authority are unchanged. No commit, push,
deployment or production SQL has been performed.

## Measured RED

The exact 14-method offline command in `implementation-red.json` ran on the
unmodified product at source HEAD `1eef8ecc1f3cdc5e397f47814cf65de14360e0c1`.
It returned exit 1 at 2026-09-21T09:09:55Z: 14 tests in 0.082 s, 47 assertion failures,
zero errors, 1.117176 s wall time. The absent reader/resource 022, misclassified
refusals and raw JSON decoder exception account for those failures. Successful
result, request-binding, escalation and service propagation characterization
controls passed. The CPU lane was released immediately afterward.

## Implemented candidate; full verification pending

- `semantic_repair.py`: independent exact-single-key plan refusal reader, 14
  producer reasons plus the fixed `planning_rejected` fallback.
- `store.py`: narrow malformed-JSON corruption handling and bounded refusal/NULL
  classification after the existing database context exits, before the unchanged
  lifecycle parser and all unchanged binding checks.
- Resource 022: complete original plan function with only CREATE OR REPLACE and
  fifteen named refusal-expression substitutions; exact original signature,
  predicates, lock, deadline escalation, exception arm and grants retained.
- Offline regression tests pin 001–021 identities, the frozen 018 function hash,
  whole-body reversible equality, ordered vocabulary, both replay arms, reader
  separation, exception causes, successful bindings and post-transaction behavior.
- Disposable PostgreSQL definitions cover reachable early refusals, prior/handoff/
  lineage failures, normal directive/child conflicts, exception rollback, both
  observed second-lookup races, a real 20-second deadline and persisted/replayed
  lifecycle results. Controlled invalid stored child fixtures obey actual table
  constraints; the write-failure test adds and removes only its own extra CHECK.
- Current-prefix tests use real 001–021 resources and ledger before applying 022,
  snapshot both functions and populated semantic success/escalation rows, retain
  drift/contention/retry coverage, and keep an explicit historical 020→021 case.

Offline GREEN passed 46 tests in 0.132 s, exit 0, wall 1.116933 s at 09:22:00Z. The first
focused PostgreSQL run passed 11 of 12 tests in 73.122 s; the deadline fixture failed
before planning SQL because its inherited execution stages totalled 390 seconds
while the task allowed 20. The fixture now explicitly uses four 5-second stages
for that case; its default and all production timeouts are unchanged. The sole
failed scenario then passed in 21.503 s, exit 0, wall 36.766830 s at 09:25:23Z; bound
disposable preflight and two real PostgreSQL restart/recovery probes also passed.

This is combined focused evidence, not a claim that the original 12-test command
passed unchanged. Product modules/resource 022 and the 46 offline tests stayed
unchanged after their passing run. Full route verification and independent
reviews remain coordinator-owned pending work; no full verifier ran here. The
CPU lane was released after the corrected deadline run.

Exact outputs and SHA-256 values are preserved in JSON-escaped transcripts next
to their numeric command/time/exit records. Raw logs remain in the task cache.
This preserves original traceback whitespace without introducing trailing-space
failures in the repository's diff check. `implementation-candidate.json` names
the exact seven candidate file hashes and the scope of evidence above.

## Pending runtime limits and recovery

`execution_material_missing` is not constructible through the valid fixture's
referential bindings; invalid baseline risk and NULL manifest deadlines are
rejected by typed producers. These branches retain frozen whole-body/site proof;
no production constraint is disabled to manufacture reachability. This is a
bounded fixture limitation, not a claim that arbitrary owner-corrupted storage
can never reach those guards.

Successful deadline behavior uses server time and a watchdog; no production
freshness/statement/lock timeout was widened. Both idempotency lookup outcomes,
normal-return persistence, exception rollback, populated 022 upgrade/replay,
advisory contention/retry and historical 021 replacement passed their focused
runtime cases. Migration rollout must coordinate package/database readiness;
recovery after applying 022 requires a later forward migration, preserving the
immutable ledger and compatible reader. No operational execution is authorized
by this evidence record.

## Coordinator handoff

The source is ready for the coordinator's full route verification followed by
the selected independent code/test/data reviewers. No local receipt, external
CI conclusion, merge, issue closure or deployment is implied by this report.
Keep the existing 166 prerequisite and do not edit any applied migration to
recover a later operational failure.

Shared-memory mistake to record: the new short-deadline fixture initially reused
a 390-second execution plan, so the contract correctly rejected construction
before the target branch. Matching the test stages to the task budget fixed the
fixture without changing product bounds.

Shared-memory decision to record: the complete reversible function-text proof
passed together with immutable historical hashes and real prefix upgrades.
That combination protects predicate, replay and transaction behavior while
allowing a separate bounded refusal channel.
