Persisted Stage A evidence only: source HEAD `39d0f9eb27d807e72219d613c290e785a035f151`, fingerprint `b7c59b62ec6e3d29e4d09376f74bc22975bf5198767a74991570e0484b52d68c`. The complete report below is projected only by replacing the host repository prefix with `<repository-root>` and removing trailing whitespace. Actual 004 pin, final reviews and final verification remain pending; this is historical source-bound evidence, not a completion receipt.

# Independent security review — Stage A closed local checker

Result: PASS for the closed local checker adapter at the identity below. No blocking or advisory security defect was found in this bounded review. This is not acceptance of actual SQL, AC-001 completion, production/deployment approval, a full-verifier receipt, or merge authority. The production reviewed-migration registry is EMPTY. An actual reviewed Task1 pin changes the source and requires fresh delta review and qualification.

## Source and isolation

- Selected reviewer: security_reviewer, route 249e86df9131, change 20261005-task-249e86.
- Read-only candidate: <repository-root>/.review-scratch/trust-public-checker.
- Task comparison base: fd5f5fcc32358bb07c51c23881bede751e76f197. Agreed actual PR base: 326908bf6367b05b65b83818ee84a093c1e45872.
- Candidate HEAD before and after: 39d0f9eb27d807e72219d613c290e785a035f151.
- Candidate Git tree: f0fb961fd7f3a3469cc6253ace8bb508065ecd4c.
- Candidate fingerprint before and after: b7c59b62ec6e3d29e4d09376f74bc22975bf5198767a74991570e0484b52d68c.
- Status before and after: clean; no staged, unstaged, or nonignored untracked candidate files.
- Checker SHA256: a7705e636074781464b5fb5830e0de03dd7bf007b00cbf45a403162890f09be5.
- Focused test SHA256: 3d53af0d00acd1dd97d22e3c97b310d37eb3bc824065d56ec98400e90f267c6c.
- Reviewer scratch: <repository-root>/.review-scratch/security-checker-39d0f9e-9YcWvo/snapshot. Its parent is reviewer-owned, pall, mode 0700, beneath pall-owned non-sticky .review-scratch mode 0700. The nested clone has a separate .git and was created with --no-local --no-hardlinks. It began at the exact candidate HEAD with clean status and identical fingerprint. No shared Git metadata or local hardlinks were used. The intentional mutant remains only in private scratch.
- reviewed-tree-modified: no

CPU discovery was recorded before task inspection in <repository-root>/.review-scratch/security-reviewer-capacity-39d0f9e.md. Observed 14 physical cores / 28 logical online CPUs, default 22 allowed CPUs, effective inherited cpuset 0-27 and no finite applicable quota; child-only widening succeeded at 28. All executable Python probes used one process/taskset 16-19. No agents, heavy verifier, external calls, secrets, .env, credentials or production state were accessed.

## Security reasoning and code evidence

Assets are the checker admission boundary, existing architecture ownership/runtime/secret envelope, historical SQL identity and external Trust CI authority. Untrusted candidate metadata, source bytes, SQL, environment and CLI inputs must not manufacture trusted reviewed-byte authority. The registry is checked-in local workflow evidence and cannot establish deployed SQL safety or external approval.

1. Four exact public descriptors are closed at architecture_fitness.py:167-175 and 1706-1725. Equality requires the entire ID/path/version/kind/role/compatibility tuple: lifecycle projection is API/json_schema/consumer/consumer_accepts_old; profile selection is WORKER/json_schema/consumer/consumer_accepts_old; effective policy is WORKER/json_schema/bidirectional/bidirectional; attestation is WORKER/signed_payload/producer/producer_accepted_by_old. Every descriptor is version "1" under the precise engineering/contracts/schemas/<name>.v1.json path. The head must have exactly the prescribed sole owner, which already exists in the base. Schema bytes and nonempty paired source bytes must actually change. Lifecycle pairs api.py or webhooks.py; profile/effective pairs public_policy.py; attestation pairs public_runner.py. Legacy policy.py alone supplies no pairing authority.

2. Normalization removes only the admitted descriptor and its owner's public_contracts membership (1726-1733). The comparison then preserves all non-node model content, node identities and every node property except repository_paths (1751-1756). Thus edges, trust domains, old contracts, owner, runtime, secret memberships and other node attributes are retained by equality. Source memberships are separately checked rather than hidden by normalization.

3. The new worker exception (1768-1776) is confined to NODE-TRUST-CI-WORKER, type worker, TD-TRUST-CI-EXECUTION, Trust CI operators, container runtime, additions only, and the seven exact filenames defined at 161-165. Old paths cannot disappear. Changed membership paths must be canonical, non-wildcard changed Python source bytes (1744-1750); new registrations cannot expand a pre-existing prefix owner; ownership transfer remains only the pre-existing exact store.py correction (1792-1816). This change does not grant broad worker type/domain admission. The surrounding existing control-node metadata exception remains present and was not newly generalized.

4. Unknown descriptors/schemas are not removed; arbitrary worker paths do not satisfy the new extension; any nonqualified implementation path alongside Trust CI remains a separation failure at 1843-1876. Candidate diff inventory against the actual PR base consists of the checker, focused tests, decisions.md and the 14-file local change package. It contains no Trust CI runtime/loader/SQL/schema implementation, architecture rule data, factory runtime, selector or deployed trust material.

5. The production registry is literally {} (158), with no environment, CLI or caller digest authority added. Exact 004 primary identity is counted as version 4 even when denied (1220-1222). Approval at 1366-1376 requires the exact historical policy identity, immutable history, exact trust-ci/sql prefix, unchanged required phase set, exact primary path and registry digest, sole exact packaged mirror and byte equality. The approved case is explicitly named reviewed_trust_ci_migration_byte_compatibility and says "not semantic phase proof" (1457-1463). No generic numbered-SQL fallback was added.

6. Unknown .sql inventory now records unsupported status (1330-1334). Existing immutability/deletion checks, unique/contiguous numeric versions, aggregate planning/work/read-byte limits and generic phase analyzer remain around the reviewed-byte branch (1268-1455). The special branch bypasses semantic statement analysis by design; raw-byte compatibility must not be represented as SQL semantic proof or statement-level analysis of actual004. The registry is empty here, so no such production exception currently succeeds.

These are static assessments. Except for the explicitly executed claims below, behavioral claims in this section are unexecuted by this reviewer. The implementer's larger matrix is historical implementer observation, not independent execution by me.

## Executed probes

All tool execution used explicit candidate workdir; probe commands cd only into reviewer scratch. Snapshot creation:

```bash
taskset -c 16-19 bash -c 'set -eu; review_private=$(mktemp -d <repository-root>/.review-scratch/security-checker-39d0f9e-XXXXXX); chmod 0700 "$review_private"; git clone --quiet --no-local --no-hardlinks --single-branch --branch fix/trust-public-local-checker <repository-root>/.review-scratch/trust-public-checker "$review_private/snapshot"; printf "%s\n" "$review_private"; git -c core.optionalLocks=false -C "$review_private/snapshot" rev-parse HEAD; git -c core.optionalLocks=false -C "$review_private/snapshot" status --porcelain=v1 --untracked-files=all; stat -c "%a %U %n" "$review_private" "$review_private/snapshot"; git -c core.optionalLocks=false -C "$review_private/snapshot" rev-parse --git-common-dir; git -c core.optionalLocks=false -C <repository-root>/.review-scratch/trust-public-checker rev-parse --git-common-dir'
```

Exit 0; new private parent 0700, exact HEAD 39d0f9e, clean clone. Both .git paths resolve within their distinct clone directories. Clone fingerprint equaled the candidate fingerprint before mutation.

Baseline risk probe:

```bash
taskset -c 16-19 bash -c 'set -eu; cd <repository-root>/.review-scratch/security-checker-39d0f9e-9YcWvo/snapshot; export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 TMPDIR=<repository-root>/.review-scratch/security-checker-39d0f9e-9YcWvo; python3 -c "import sys; from pathlib import Path; sys.path.insert(0, chr(46)+chr(103)+chr(114)+chr(111)+chr(107)+chr(45)+chr(115)+chr(116)+chr(97)+chr(99)+chr(107)); from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))"; python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_unreviewed_public_migration_cannot_accept_runtime_digest_authority tests.test_architecture_fitness.ArchitectureFitnessTests.test_public_metadata_requires_changed_schema_and_exact_paired_source_bytes'
```

Exit 0, Ran 2 tests in 11.055s, OK. The first executes synthetic004 refusal with both environment digest variables set; caller expected_digest rejection; real CLI rejection of --expected-migration-digest. The second executes unchanged-schema and unchanged-exact-source pairing refusal with a changed unrelated legacy policy.py making separation applicable. These fixtures are synthetic and create no real migration approval.

Mutation M1: in private snapshot only, replace `and digest == _REVIEWED_TRUST_CI_MIGRATIONS.get(item.path)` with `and digest is not None`. This intentionally discards reviewed-hash authority while retaining the other exact path/mirror requirements.

```bash
taskset -c 16-19 bash -c 'cd <repository-root>/.review-scratch/security-checker-39d0f9e-9YcWvo/snapshot; export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 TMPDIR=<repository-root>/.review-scratch/security-checker-39d0f9e-9YcWvo; python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_unreviewed_public_migration_cannot_accept_runtime_digest_authority'
```

Exit 1, Ran 1 test in 3.169s, FAILED: assertNotEqual(result.status, "pass") saw 'pass' == 'pass', findings (). M1 KILLED. No mutants survived; no global mutation-score claim is made. This demonstrates the negative guard detects removal of registry authority; it does not establish every metadata or SQL invariant.

Candidate-only checks: `git -c core.optionalLocks=false diff --check fd5f5fcc32358bb07c51c23881bede751e76f197 HEAD` exited 0; `sha256sum .grok-stack/adaptive_grok/architecture_fitness.py tests/test_architecture_fitness.py` matched the identities above. Actual-base `git diff --name-status 326908bf6367b05b65b83818ee84a093c1e45872 HEAD` showed only the 17 scoped files. Before and after `git status --porcelain=v1 --untracked-files=all` had no output, and `git rev-parse HEAD` remained exact39d0f9e.

Final fingerprint command:

```bash
PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 taskset -c 16-19 python3 -c 'import sys; from pathlib import Path; sys.path.insert(0,".grok-stack"); from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))'
```

Exit 0; b7c59b62ec6e3d29e4d09376f74bc22975bf5198767a74991570e0484b52d68c both before and after review.

## Limitations and outstanding authority

No actual004 bytes or independent actual SQL review exist in this contour. Actual PostgreSQL syntax/function bodies, additivity/destructiveness, privileges, roles/grants, quotas, concurrency/linearization, locking, query plans, bounded cleanup, recovery, migration loader plan/status behavior and deployment compatibility are unexecuted and unapproved here. The special raw-byte branch does not prove these claims.

The complete descriptor positive/negative matrix, worker source matrix, SQL drift/history/version/resource-limit matrix and existing control-node correction matrix were inspected but not rerun; code/test/data reviewers and final frozen verifier cover their selected scopes separately. No preliminary or full verifier was run by this reviewer. External policy epoch, holdout validation, App-owned exact-head check, protected branch requirements and signed human approvals were neither queried nor simulated. Local recorded source-scope consent is not an external signed security approval.

Before AC-001 or delivery can be qualified, independently review frozen actual Task1 SQL, hand its source identity and raw digest to the single writer, review the subsequent pin delta against its new identity, persist all selected independent reports, freeze, and run the final full PR gate plus the external exact-head Trust CI/required approval path. This report cannot be reused as approval of different pin bytes or a changed candidate.

Reviewer work is complete and stopped. The coordinator owns persistence of this private report and any later receipts.
