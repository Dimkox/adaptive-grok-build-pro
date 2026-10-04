# Core source data review — PASS

Selected data_reviewer, route ffb3d81e031f. Scope: original-base Core database/test-fixture boundary and AC-004/AC-008/INV-001; no final release, F026/M7 successor acceptance or merge authority. No blocking data findings.

Source: <local-path> Base 63799f8760d3a55028d83ab5ff0116ececf8f7d1; before/after HEAD e8a4cd02cdc8ae047c3d8e2b88146856fc5c17c0; Git tree 3cbdd03fb6403b6597bcd4acea4029e743f04de9. Before/after canonical adaptive_grok.util.tree_fingerprint: 2f947056c276408529f450c8026b2d3b41393d441b7cbba6789cf3efb1fc5225. Both source status reads empty. reviewed-tree-modified: no

Private independent exact clean clone: <local-path>; parent and role directory verified owner pall, mode0700, non-sticky. Clone uses --local --no-hardlinks; scratch canonical fingerprint matches source above after checks. Only CPU22,23, at most2workers; no DB/full runs, agents, candidate writes or external actions. Startup measurement retained capacity.md (initial snapshot saved before task inspection in /tmp/core-data-review.VeJgQW/capacity.md, then copied privately).

## Findings and static assessment

Actual `git diff 63799f8760d3a55028d83ab5ff0116ececf8f7d1 HEAD -- factory` contains only four test files. `git diff --name-only 63799f HEAD -- factory/src factory/migrations` is empty: migration001-025 and runtime store/database logic unchanged. Read requirements, change-spec.yaml, tasks, test-plan, rollback, release-scope-ledger and delivery-topology-addendum; F durable026/M7 and G remain explicitly pending. Historical analyses in the ledger are superseded planning, not fresh acceptance.

postgres_fixture_reset.py:3-7 extracts precisely the original43-table TRUNCATE statement with RESTART IDENTITY, no CASCADE, dynamic identifiers, connect/commit/rollback or privilege operations. Both original callers retain ownership of psycopg connection/cursor transaction contexts. Execution setUp retains conditional legacy-marker kill-switch/singleton seeding; restart probe retains unconditional seeding; counter resets and M0 observation payloads remain unchanged after the extracted call. Helper failures propagate to the caller transaction boundary.

test_execution_persistence_postgres.py:250-259 accepts only StoreUnavailable directly caused by typed psycopg.errors.LockNotAvailable. Other unavailable, integrity, connection, statement timeout and unwrapped SQL errors propagate. Concurrent acceptance at5303-5343 still requires one typed ExecutionRecoveryClaim and exact five SQL effect counts=(1,1,1,1,1); a refused loser is retried only after both futures finish and must return None. Controlled-holder case positively observes pg_blocking_pids, tests zero partial effects before holder release, then one canonical effect and unchanged effects after retry. Existing production transaction/500ms test safety bounds are not widened; added observer/holder connections have explicit tighter bounded options. Existing store.py transaction exception chaining and recovery release/context code were inspected for compatibility, without runtime changes.

No migration, schema/index/backfill, production data or database role changes need rollout here. Fixture reset is test-only and targets caller-selected disposable DB. Added PostgreSQL characterization includes rollback, unlisted FK refusal and runtime-role refusal; cleanup names only its explicit test table/login. Reverting source through a PR is appropriate; no live destructive recovery proposed.

## Executable probes

Exact command in private scratch:
`taskset -c 22,23 env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:. python3 -m unittest factory.tests.test_postgres_fixture_reset.FixtureResetTests factory.tests.test_execution_persistence_postgres.RecoveryContentionAcceptanceTests -v`

Observed exit0, seven tests PASS in0.118s. Probed: immutable SQL SHA256 a67d8339b86d2af81a72d3f8e953cf29ce8bb81067f1cefe4921555a0c075de9 and43-table/no-CASCADE/cursor-only behavior; original exception identity; both real caller success/failure transaction branches and distinct seeding/payloads; direct/package helper imports; both concurrent futures finishing; narrowly typed refusal and negative error propagation. No mutants executed (not mandatory for selected data role); no mutation score claimed.

Identity commands: `git status --porcelain`; `git rev-parse HEAD HEAD^{tree}`; `PYTHONDONTWRITEBYTECODE=1 python3 -c '... from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(p))'` using candidate .grok-stack import, before/after and on scratch. Empty status and identical identities as above. Scratch reproduction and safety verified with `stat -c '%a %U %n'` and clone command.

## Evidence and limitations

Selected fields of controller full-pr-e8a4.json read with jq: status=pass, matching canonical fingerprint, factory-unit=pass, factory-postgres-exit=pass. This is controller-owned exact-state local evidence, not my independent DB run, App acceptance or human security approval. Earlier c50/failed/HB/historical evidence is not reused as fresh proof.

Unexecuted independently: real PostgreSQL lock timing/rollback/exact-once effects, FK and least-privilege behavior, restart durability, migration status, installation materialization, budgets and full verification. Assignment prohibits independent DB/full runs; actual SQL assertions were statically assessed and controller current DB gate corroborates them. Static claims above are not represented as independently executed. Two controller adversarial FIFO pthread/fork deprecation warnings are unrelated to these data paths and remain broader verification limitations. This PASS covers Core source readiness under this role, not final2.1.1 release or F/G qualification.
