Task1 fix1 historical source evidence: HEAD `bacb5346a95d25166e1f7c597b3f91bd5935c234`, fingerprint `1410ef8f89b3cb621c40be1ccb0ae8af4860a813d14af4dd2b09b4244bf68145`. Scoped D1/D2 repair independently Approved; raw/mirror004 `610b8fa6b759c69578bc18b007484db1c4e19cba5f613c7bd482e68badac646e`. This is not full branch verification or merge/launch authority. Complete report is projected only by repository host-prefix replacement and trailing-whitespace removal.

# Spec compliance: Approved for Task1 fix round1

Task quality: Approved within the scoped D1/D2 repair and affected claims. Both original important findings are resolved on the reviewed candidate. No new blocking issue was found in the fix delta. This is independent task-level data/spec/code-quality review, not a full branch review, verification receipt, SQL registry write, public-launch approval or merge authority.

## Exact reviewed identity

- Reviewer `/root/trust_public_task1_data_reviewer`, selected data_reviewer; route46ffbe9a85c9; change20261005-task-46ffbe; generation public-task1-reviewfix1-20261005.
- Candidate `<repository-root>/.review-scratch/trust-ci-public`.
- Fix comparison base `adeb6ceda8b019eb1579657bcdec784022f36210`; HEAD before/after `bacb5346a95d25166e1f7c597b3f91bd5935c234`.
- Canonical fingerprint before/after `1410ef8f89b3cb621c40be1ccb0ae8af4860a813d14af4dd2b09b4244bf68145`. Git status empty before/after.
- Actual raw004 and packaged004 SHA256 independently checked before/after: `610b8fa6b759c69578bc18b007484db1c4e19cba5f613c7bd482e68badac646e`, byte-identical.
- Read complete fix-round1 report and all1,433 lines of supplied fix review package once, in contiguous chunks. Did not reread original whole-task diff or plan, crawl unrelated code, or rerun reported suites. All seven declared fix files have relevant hunks. Existing skills and original review remain context; no new skill-imposed gate was invented.

## Strengths and old finding disposition

D1 CLOSED. `public_models.py:303` binds an admission copy to returned intent claims without making the copy itself authoritative. `store.py:174`, `:220`, `:283` recheck the canonical stored lease/request and current durable PR revision. `store.py:314` extends that fence to job claim/ownership, preserving installation generation and isolation from other PRs. Closing intent is terminal denied; unbound trusted enqueue cannot bypass an existing fence. `store.py:438` deliberately allows cleanup of an exact old reservation after the PR fence advances, while still requiring the cleanup fence and positive cleanup confirmation.

Actual PG independent positive control first enqueued a valid `admission.for_intent(leased)` request and replayed it idempotently. API-role close then cancelled that job. Reusing the SAME previously valid bound admission failed with the exact `stale public PR intent fence` error during both enqueue and completion; public claim returned None. Thus this does not pass merely because an obsolete unbound API call was rejected. Removing only the new ownership PR-fence guard made that probe fail, proving it exercises the repaired safety property.

D2 CLOSED. `store.py:827` now loads active AND unexpired quota rows for relevant accounts, plus exact repository keys needed by live bindings/intents/input and rows of the exact lifecycle reconciliation installation. It does not truncate live quota inventory or erase history. The exact reconciliation installation remains bounded by the existing snapshot/pruning contract.

Actual PG independent probe retained103 historical rows under other installation IDs of the same account and held locks on an expired/inactive row, expired/active row and fresh/inactive row. Current exact admission lookup succeeded under250ms lock_timeout; all104 total rows including the live admission remained. Removing the active/expiry predicate alone reproduced the original lock timeout, proving the control is sensitive to the repair. The implementer's expanded source regression additionally exercises enqueue/claim and live cross-installation quota; its readable execution evidence was not repeated.

Full-retention seam statically accepted under the coordinator's explicit bounded ruling: `004_public_admission.sql:39` provides unique indexed exceptional-delivery lookup; canonical identity/digest/projection checks precede mutation; `:226` promotes an exceptional predecessor into normal retained history when space permits; `:237` preserves a persistent exact-PR hold when history cannot be retained; `:303` stores at most one exceptional marker in that PR row rather than overwriting an unresolved predecessor. The ordinary fence updates retain existing marker/hold fields. Open/reopen cannot silently clear the hold, and the direct enqueue path cannot bypass it. Memory and SQL implement the same stated transitions. Unlimited replay history or a working hold-recovery mechanism is not claimed.

## Issues

Critical: none found in the scoped delta.

Important: none outstanding from this scoped repair. Original D1/D2 rejection and old7334 digest remain historical; they are not relabelled as passing.

Minor/new recommendations: none required for this task. Production-volume query planning remains unmeasured and must not be described as a completed scalability qualification.

## Private snapshot and resources

Capacity was remeasured and recorded before route/diff inspection at2026-10-05T04:15:10Z; complete commands/results are in adjacent `capacity.md`. Host14 physical/28 online logical CPUs; initial affinity22; bounded child-only widening verified0–27; actual cgroupv2 membership and ancestor limits had no finite quota. Parent separately reserved CPUs4–5; PostgreSQL1CPU/cpuset4, probe1CPU/cpuset5. No subagents or other reviewer PG project.

Trusted parent `<repository-root>/.review-scratch` and new reviewer directory `<repository-root>/.review-scratch/data-review-fix1-5pOIJi` were owner pall,0700,non-sticky. Fresh snapshot commands:

```bash
git clone --no-local --no-hardlinks --no-checkout <repository-root>/.review-scratch/trust-ci-public <repository-root>/.review-scratch/data-review-fix1-5pOIJi/snapshot
git checkout --detach bacb5346a95d25166e1f7c597b3f91bd5935c234
```

Every execution gave explicit candidate or private-snapshot workdir. Initial snapshot status/fingerprint matched candidate exactly. The previous review snapshot with its cleanup mutant was never reused. The new snapshot was unchanged for baseline, then deliberately mutated privately for each probe; M1 was restored before M2. M2 remains only in private snapshot. Candidate was never edited or restored.

## Exact executed controls and mutations

Reproducer `<repository-root>/.review-scratch/data-review-fix1-5pOIJi/pg_probe.py`; override adjacent `compose-review.yaml`. Source/tests/sql and reviewer script are mounted read-only from the new exact private snapshot. Existing checked-in compose.test.yaml unchanged; existing test image used only with exact source mounts, not claimed as a rebuilt release artifact. Script verifies DSN hostname postgres-test and database trust_ci_test before migration; fixture credentials are synthetic. No .env, key, live deployed container or production database access occurred.

All commands below used this exact prefix from private snapshot:

```bash
env TRUST_CI_POSTGRES_IMAGE=postgres:17.6-bookworm@sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3 TRUST_CI_PYTHON_BASE_IMAGE=python:3.12-slim-bookworm@sha256:54c85f3c47607a77f32adec749d3c81d1348bf25833671f512b26a9b6d778cb3 TRUST_CI_TEST_BUILD_TAG=trust-ci-public-task1-test:20261005 docker compose --env-file /dev/null --project-name trustpublic-datareview-fix1-5poiji -f trust-ci/compose.test.yaml -f <repository-root>/.review-scratch/data-review-fix1-5pOIJi/compose-review.yaml
```

1. Baseline suffix `up --no-build --abort-on-container-exit --exit-code-from postgres-integration postgres-integration`. Override command `python3 /tmp/pg_probe.py`. Two controls ran: `DataReviewFixProbe.test_bound_positive_before_close_then_stale_enqueue_and_complete_denied` and `DataReviewFixProbe.test_dormant_same_account_rows_not_locked`. Both OK,1.094s,exit0,zero skips. Diagnostic output confirmed canonical bound positive enqueue/idempotency before close, exact PR-fence denial after close, and103 retained dormant rows with no blocking/deletion.
2. M1 private mutation at `store.py:219`: prefix the `_intent_owned` current-PR guard with `False and`, leaving all canonical admission/owner/request/expiry checks intact. Suffix `run --rm --no-deps postgres-integration python3 /tmp/pg_probe.py DataReviewFixProbe.test_bound_positive_before_close_then_stale_enqueue_and_complete_denied`. Positive control still succeeded; expected stale-PR RuntimeError was not raised. One FAIL,0.619s,exit1. M1 KILLED. Exact repair property tested: a formerly valid bound callback must lose enqueue authority at close.
3. Restore M1. M2 private mutation at `store.py:828`: replace only `(payload ->> 'active')::boolean AND (payload ->> 'expires_at')::timestamptz > %s` with `%s::timestamptz IS NOT NULL`, preserving account/exact-key/reconciliation predicates and parameter order. Suffix `run --rm --no-deps postgres-integration python3 /tmp/pg_probe.py DataReviewFixProbe.test_dormant_same_account_rows_not_locked`. One ERROR,0.745s,exit1: psycopg LockNotAvailable, context `while locking tuple (0,2) in relation "trust_ci_public_admissions"` at queryline827. M2 KILLED. Exact repair property tested: irrelevant dormant same-account history is not locked.
4. Suffix `down --volumes --remove-orphans`,exit0. Only exact reviewer-owned project containers, network and disposable test-data volume were removed. Test data intentionally discarded; no user recovery required. CPU reservation released to coordinator.

Two selected mutants, two killed; no survivors/inconclusive mutants. This is bounded sensitivity evidence, not a universal mutation score.

Identity commands before/after on explicit candidate workdir: `git rev-parse HEAD`; `git status --porcelain=v1`; `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack python3 -c 'from pathlib import Path; from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))'`; `sha256sum trust-ci/sql/004_public_admission.sql trust-ci/src/adaptive_trust_ci/resources/004_public_admission.sql`. All return exact identities above.

reviewed-tree-modified: no

## Limitations and unexecuted claims

- Static acceptance of exceptional-marker promotion/unique delivery replay/persistent hold is not a new reviewer-executed saturation test. The implementer's final12PG and strengthened2PG evidence was read completely and remains attributed to that report. This review deliberately did not repeat those suites. Full retention cross-PR conflict handling, reopen/synchronize, forged nested leases, old-reservation cleanup, and role grants are statically reviewed/covered by supplied evidence, not independently re-executed here.
- A persistent `pr-replay-history-incomplete` hold has no recovery endpoint in Task1. Future approved lifecycle/storage recovery must reconstruct/verify history before reopening; neither more ledger space nor an ordinary event automatically restores authorization. This is a disclosed fail-closed limitation under the explicit ruling.
- Query planner work/production volume, full quotas/fairness/concurrency, actual restart recovery, all legacy behavior, and runtime executor600s/2CPU/1GiB enforcement were not measured in this re-review. No full verifier, wheel build, external Trust CI, production migration/rollback, registry pin or launch approval performed.
- SQL004 remains a source draft here. Historical001–003, legacy model signatures and signing/check policy remain outside this repair. Once004 is operationally applied/pinned, use a forward migration; the rejected7334 draft is not a safe runtime downgrade because final public records/sidecars changed.
- Old broad-UPDATE API retirement remains required before public launch. Task2 must use the canonical bound leased-intent enqueue path, then complete; a trusted internal direct-enqueue fixture seam is not webhook authorization.
- Learning for coordinator: prove a negative fence test with a positive bound-authority control first; otherwise an API-shape rejection can hide a surviving race. Combining that positive control with targeted guard mutations demonstrated the intended failure boundary.

STOP. Scoped D1/D2 fix accepted; coordinator owns report persistence, final freeze, remaining selected reviews, qualifying verification and any separately authorized exact-digest registry action.
