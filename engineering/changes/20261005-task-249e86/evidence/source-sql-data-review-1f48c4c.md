# Publication projection

Complete independent bounded bootstrap/expiry report below, retaining1f48c4c identity. Only host-local repository prefix is replaced and terminal blank lines normalized. Raw report remains private; no blanket SQL/launch authority is inferred.

# Spec compliance: Approved for the bounded bootstrap/expiry fix

Task quality: Approved. The reviewed delta fixes pre-installation PR ordering while preserving a bounded, unleased wait; only exact first worker-confirmed admission authorizes the original request, and canonical seven-day expiry precedes binding. No blocking defect found in this scoped review. Actual migration005 digest `19b5aa4a0400ba4fae605a0f0b89d77c448c222a20089d39ebfb86f84958cd03` is independently accepted for these source semantics. This report performs no checker registration and is not public-launch, full-branch, external Trust CI or merge approval.

## Identity and reviewed scope

- Reviewer `/root/trust_public_task1_data_reviewer`, selected data_reviewer; route46ffbe9a85c9/change20261005-task-46ffbe; generation public-pending-review-20261005.
- Exact candidate `<repository-root>/.review-scratch/trust-ci-public-pending`, branchfix/trust-ci-public-pending.
- BASE `8a2efc37bae3ddee79f7bab60d171a7fda290610`; final HEAD before/after `1f48c4ccc84192780395b18957ba8c9779e30f00`.
- Canonical candidate fingerprint before/after `6076bb69f29011b6157902f61efa888f0e72da90d1ee97961cc3cd8378963350`; Git status empty before/after.
- Raw004 and resource004 both remain `610b8fa6b759c69578bc18b007484db1c4e19cba5f613c7bd482e68badac646e`; raw005 and resource005 both `19b5aa4a0400ba4fae605a0f0b89d77c448c222a20089d39ebfb86f84958cd03`, independently verified before/after.
- Complete brief/report and all897 lines of supplied two-commit review package read once. No repeat of the previous Task1 matrix, whole original diff, or full plan. Existing applicable adaptive-delivery/data/security/verification skills and task-review template used. Seven changed files match the declared repair and shared lessons; no model or fourteen-Store-signature change.

## Strengths and concrete spec checks

- `trust-ci/sql/005_public_pending_bootstrap.sql:154` and `store.py:131` distinguish absent installation from an existing denied/mismatched identity. Valid absence creates pending revision0 with a nonzero PR epoch; it does not create installation/admission state or grant execution authority.
- `store.py:199` limits bootstrap rebinding to original pending revision0/attempts0. `:205` requires exact installation identity, non-denied revision1, and `:210` binds only generation1 with current repository admission. The preexisting PR fence check runs before this branch, preserving close/reopen/replacement/hold denial. Later installation epochs cannot revive the original request.
- `store.py:200` compares canonical creation timestamp against an inclusive seven-day deadline before admission binding, sets dead/unverified-installation-expired with no lease or consumed attempt, and preserves the normal terminal delivery identity. A late complete snapshot cannot outrun this guard.
- `005_public_pending_bootstrap.sql:4` uses a forward CREATE OR REPLACE function, fixed SECURITY DEFINER/search_path, retaining the same function signature; `:258` and `:259` reaffirm PUBLIC revoke and API/worker execute. No table/index/backfill or direct API activation privilege was added. Direct function-body comparison confirmed only CREATE OR REPLACE and the absence guard/comment differ from accepted004.
- New tests distinguish a positive executable job from mere absence of errors. Supplied role, migration, quota, replay, retry-budget and lifecycle tests are affected controls; the implementer's48-control result is readable but was not redundantly regenerated here.

## Findings

Critical: none found in scoped delta.

Important: none found in scoped delta.

Minor: implementer cleanup output reports deprecated Docker `--time` instead of `--timeout`. This is operational command noise, not a product regression; cleanup succeeded and this reviewer used Compose cleanup without that flag. No code fix is required by this observation.

## Independent executable controls

Fresh private directory `<repository-root>/.review-scratch/data-review-pending-uNztI7`; trusted parent and reviewer directory0700,pall,non-sticky. No prior mutant snapshot reused. Commands:

```bash
git clone --no-local --no-hardlinks --no-checkout <repository-root>/.review-scratch/trust-ci-public-pending <repository-root>/.review-scratch/data-review-pending-uNztI7/snapshot
git checkout --detach 1f48c4ccc84192780395b18957ba8c9779e30f00
```

Snapshot initially clean and fingerprint-identical to candidate. All shell executions used explicit candidate or private-snapshot workdir. Reproducer `pg_probe.py` and `compose-review.yaml` reside in this private directory, outside candidate. Source/tests/sql and probe were mounted read-only into a unique disposable project from the exact private snapshot. No source mutations preceded baseline; subsequent mutants affect only that snapshot.

Every Compose call used this exact prefix from private snapshot:

```bash
env TRUST_CI_POSTGRES_IMAGE=postgres:17.6-bookworm@sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3 TRUST_CI_PYTHON_BASE_IMAGE=python:3.12-slim-bookworm@sha256:54c85f3c47607a77f32adec749d3c81d1348bf25833671f512b26a9b6d778cb3 TRUST_CI_TEST_BUILD_TAG=trust-ci-public-task1-test:20261005 docker compose --env-file /dev/null --project-name trustpublic-datareview-pending-unzti7 -f trust-ci/compose.test.yaml -f <repository-root>/.review-scratch/data-review-pending-uNztI7/compose-review.yaml
```

Baseline suffix `up --no-build --abort-on-container-exit --exit-code-from postgres-integration postgres-integration`; override command `python3 /tmp/pg_probe.py`. Actual packaged migrations001–005 applied by the disposable migrator. API-role ingress and worker-role claim/completion/enqueue exercised, with script asserting disposable hostname/database before operation. Result:3 tests OK,1.684s,exit0,zero skips.

- `PendingReviewProbe.test_valid_bootstrap_reaches_one_exact_job`: API-created original pending tuple is statuspending/revision0/PRrevision1/attempts0; a worker cannot claim it before lifecycle; actual installation-table count stays0. While first lifecycle is leased, PR remains unleased. After complete first snapshot, the same intent ID leases at revision1/attempt1, binds through admission.for_intent, creates one job with duplicate enqueue free, completes, and that exact job is publicly claimable. This is a non-vacuous positive authority path.
- `PendingReviewProbe.test_later_installation_epoch_cannot_bind_original`: first-created plus second lifecycle yields valid current worker-confirmed revision2 admission. Original revision0 intent is nevertheless denied/attempts0, and replay remains free with the same ID. No accidental denial due to missing current admission explains the result.
- `PendingReviewProbe.test_deadline_precedes_late_valid_first_snapshot`: original remains pending/attempts0 one second before deadline. First lifecycle is then validly completed AT the seven-day deadline; current admission exists. Original is still dead/unverified-installation-expired/attempts0/no lease, replay free, actual jobs-table count0. This proves expiry ordering against a positive late-admission precondition.

## Bounded mutation evidence

M1: private store.py guard `state['revision'] == 1` changed to `>= 1`, with rebound revision set to `state['revision']`; this is one semantic mutant accepting any current first-confirmed generation. Exact suffix:

```bash
run --rm --no-deps postgres-integration python3 /tmp/pg_probe.py PendingReviewProbe.test_later_installation_epoch_cannot_bind_original
```

Observed one FAIL,0.639s,exit1: unexpected leased original PublicWebhookIntent at revision2/attempt1. M1 KILLED. It tests the exact-first-installation-epoch boundary, with fresh verified admission available.

M1 restored, then M2 disabled only deadline guard using `if False and now >= item.created_at + timedelta(days=7):`. Exact suffix:

```bash
run --rm --no-deps postgres-integration python3 /tmp/pg_probe.py PendingReviewProbe.test_deadline_precedes_late_valid_first_snapshot
```

Observed one FAIL,0.729s,exit1: expired original unexpectedly leased at revision1/attempt1 at its deadline. M2 KILLED. It tests expiry before late first-admission binding. M2 remains in the private snapshot only. No universal mutation score claimed; no surviving/inconclusive mutants.

One private patch attempt had hunks out of source order and failed validation before applying; the corrected patch was ordered by source and applied before M2 execution. No test was run on an ambiguous partial mutation and no candidate file was involved.

Cleanup exact suffix `down --volumes --remove-orphans`,exit0: removed only trustpublic-datareview-pending-unzti7 containers, network and disposable data volume. Temporary fixture data intentionally discarded and not recoverable; source/probe/report retained. No deployed resources or user data accessed. CPU reservation released.

## Source checks, resource evidence and limits

Function replacement comparison, explicit candidate workdir:

```bash
diff -u <(sed -n '/^CREATE FUNCTION trust_ci_record_public_delivery/,/^\$\$;/p' trust-ci/sql/004_public_admission.sql) <(sed -n '/^CREATE OR REPLACE FUNCTION trust_ci_record_public_delivery/,/^\$\$;/p' trust-ci/sql/005_public_pending_bootstrap.sql)
```

Observed exactly two hunks: CREATE→CREATE OR REPLACE, and absent-installation guard/comment. No other ingress-function logic delta. The expected diff output is not claimed as exit0 equality.

Before/after source checks: `git rev-parse HEAD`; `git status --porcelain=v1`; `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack python3 -c 'from pathlib import Path; from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))'`; `sha256sum` on raw/resource004 and005. Exact identities reported above.

reviewed-tree-modified: no

- Startup capacity recorded in adjacentcapacity.md at2026-10-05T05:01:13Z before route/diff reading:14physical/28online logical, initial22CPUaffinity, child-only widening verified0–27, actual cgroupv2 hierarchy and no finite ancestorquota. Private PG1CPU/cpuset4 and probe1CPU/cpuset5 total2CPU within parent allocation. No subagents/full suite/CPU-heavy unrelated work.
- Static/unexecuted by this reviewer: full role privilege matrix, numeric malformed ingress variants, account/global quota exhaustion, all removal/reinstall/close/reopen/hold combinations, three-attempt limits, restart recovery, full legacy suite, production query planning and transactional migration lock duration. Supplied48-control/22.643s evidence covers its named subset; it was read completely, not promoted into a new reviewer run.
- Existing quoted tests/review evidence from earlierTask1 and intermediate commits remains historical. No cached pass or previous SQL digest substitutes for this exact-source scoped verdict.
- Expiry applies only to original pending unleased revision0/attempts0 bootstrap and is lazy on worker claim. Slots remain charged until a worker reaches them; no independent periodic cleanup service, eager ingress expiration, or new schema was introduced. Terminal dedup follows existing retention, not unlimited delivery-history retention.
- Current worker must support bootstrap binding/expiry when API starts storing revision0 work. Keep005-aware migrator after application; rollback closes admission/claims and uses compatible source/forward recovery, not checksum rewrites or downgrade to old behavior. No production migration or rollback executed.
- Actual GitHub/HMAC authentication, out-of-order remote facts, Task2 adapter, executor limits, launch readiness, final verification and external exact-head Trust CI are outside this source review. Store projections are assumed authenticated by the downstream trusted adapter. API receives no authority merely because missing installation now waits.
- Checker registry005 must be an exact separately authorized registration against the accepted digest; this report does not create it. No App, keys, .env, policy, deployment, push, PR, receipt or protected-branch write performed.
- Learning for coordinator persistence: positive verified-admission preconditions distinguish a real epoch/expiry denial from incidental absence of authority; both private guard mutants demonstrated those specific boundaries.

STOP. Scoped source semantics and exact005 bytes accepted; remaining integration/checker/verification actions stay with coordinator under their separate authority.
