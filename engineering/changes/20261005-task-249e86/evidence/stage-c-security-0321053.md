# Historical complete scoped review at0321053

Only the host repository prefix is projected as `<repository>`; all commands, results, identities and limitations retained. Reviewed executable bytes are unchanged by coordinator persistence. This report is not a final verification receipt.

# Stage C independent scoped security review

Result: PASS for the affected fixed004+005 checker membership/pin delta and same-scope workflow refresh. No security finding identified. This verdict does not qualify SQL semantics, the full public source/bindings, external App CI, merge or launch.

Generation: public-checker-stagec-security-20261005. Selected security_reviewer, route249e86df9131/change20261005-task-249e86.

## Identity and read-only boundary

Candidate <repository>/.review-scratch/trust-public-checker. Product delta f39547221c2e6226c704745816ad911ac501ca35..efc92cbc39b0e380d4ff318bf497e5c70e3382a3; current frozen workflow HEAD0321053c9eae202d4433fc6278ee9b8b7a195923. Actual PR base remains326908bf6367b05b65b83818ee84a093c1e45872.

Candidate HEAD before/after0321053c9eae202d4433fc6278ee9b8b7a195923; Git tree657bc8a2308b809dbc6a2528bd5cb92c0af055c0; canonical fingerprint before/afterae94088ebc787e3d2dcb976cea12183a18eeb90235a014c675e67859d4f48b7f. Git status clean before/after. Checker SHA256cd88e3676f5beea2e78f859d290e9b71742a6524b49f4edf31f9c9e5416840c2; tests SHA2566626561440b23f36a7a0f7191cf5cc22a9ec8d9cb6bae090d560400e154a4019.

Fresh private scratch <repository>/.review-scratch/security-stage-c-0321053-2LL4EU/snapshot. Parent ownerpall/mode0700 beneath trusted pall-owned non-sticky0700 .review-scratch. Independent clone used --no-local --no-hardlinks and has separate Git metadata. Clone initial HEAD/status/fingerprint exactly matched candidate. Tests used temporary fixture repositories under private parent; the intentional mutant remains only in private snapshot. No candidate writes/restores/artifact generation or Git/index/runtime/receipt mutation.

reviewed-tree-modified: no

Startup capacity was remeasured before task inspection and recorded in <repository>/.review-scratch/security-stage-c-capacity-0321053.md at2026-10-05T05:25:08Z. Physical14/online logical28, default affinity22, effective inherited cpuset0-27, no finite applicable cgroup ancestor quota; child-only widening succeeded28. Review used one process at a time on CPUs16-17, at most2CPUs. No subagents, full suite/verifier, PG, external operations, credentials, keys or .env.

## Security assessment and code evidence

Read complete supplied stage-c-product.diff, forward-implementer-efc92cb.md, forward-005-pin-provenance.md and source-sql-data-review-1f48c4c.md. Read exact efc92cb..0321053 gate refresh. The product delta is limited to fixed005 registration, fixed primary/mirror membership, a corresponding closed synthetic test, and bounded typed scope/memory prose. The frozen workflow successor adds only the attributed implementer report and refreshed local gate records. Actual-base changed inventory remains checker/tests/memory/this workflow package; no Trust CI runtime/SQL/loader/schema, factory/runtime, architecture rule, selector or deployed trust material is included.

At architecture_fitness.py:162-174, separate literal maps contain exactly two primary paths:

- trust-ci/sql/004_public_admission.sql -> rawSHA256610b8fa6b759c69578bc18b007484db1c4e19cba5f613c7bd482e68badac646e; mirror trust-ci/src/adaptive_trust_ci/resources/004_public_admission.sql.
- trust-ci/sql/005_public_pending_bootstrap.sql -> rawSHA25619b5aa4a0400ba4fae605a0f0b89d77c448c222a20089d39ebfb86f84958cd03; mirror trust-ci/src/adaptive_trust_ci/resources/005_public_pending_bootstrap.sql.

Old004 aliases are retained. Phase recognition at1234 selects only fixed primary/mirror map keys, not raw-digest registry keys or generic numeric names. Returning the exact Path stem preserves distinct version4/version5 identity. The byte branch at1378-1390 selects the corresponding fixed mirror and still requires exact Trust CI policy, immutable history, original primary prefix/phase set, per-path registered digest, sole derived mirror and byte identity. Unknown006 cannot become admitted merely by supplying a matching registry key/hash. A004 digest at005 does not match005's pinned digest. Unknown SQL inventory, immutable history, unique/contiguous versions, bounded inventory/work/reads and generic phase analyzer are unchanged. Caller/env/CLI interfaces were not modified.

Successful byte compatibility remains explicitly named and disclosed as "not semantic phase proof" at1473-1478. No parser capability or semantic SQL authority is asserted. Provenance binds005 to independently reviewed immutable source1f48c4ccc84192780395b18957ba8c9779e30f00, reported source fingerprint6076bb69f29011b6157902f61efa888f0e72da90d1ee97961cc3cd8378963350. I independently hashed raw and packaged Git blobs at that exact SHA; both match19b5. The separate source data report accepts its scoped bootstrap/expiry semantics and reports three PG controls/two killed guard mutants; those historical source executions were read and attributed, not rerun or promoted into this review.

The four named contract descriptors, worker envelope and source-separation machinery are unchanged in this delta. Stage A/Stage B reports remain historical at their own identities. No metadata matrix was repeated. Refreshed local gates cover the same separate checker PR with bounded004+005 identities; text explicitly excludes semantic migration approval, loader/deployment changes and merge authority. Branch/PR transport still requires an exact bound action/resource grant. Local gates and this review cannot alter deployed server policy, App identity, holdout, trust stores or branch protection.

These are static source assessments except for the precisely executed claims below.

## Executed controls and mutation

Snapshot creation, explicit candidate workdir:

```bash
taskset -c 16-17 bash -c 'set -eu; review_private=$(mktemp -d <repository>/.review-scratch/security-stage-c-0321053-XXXXXX); chmod 0700 "$review_private"; git clone --quiet --no-local --no-hardlinks --single-branch --branch fix/trust-public-local-checker <repository>/.review-scratch/trust-public-checker "$review_private/snapshot"; printf "%s\n" "$review_private"; git -c core.optionalLocks=false -C "$review_private/snapshot" rev-parse HEAD; git -c core.optionalLocks=false -C "$review_private/snapshot" status --porcelain=v1 --untracked-files=all; stat -c "%a %U %n" "$review_private"'
```

Exit0; exact frozen HEAD, clean clone, private parent0700.

Independent source005 digest observation:

```bash
taskset -c 16-17 bash -c 'set -eu; for p in trust-ci/sql/005_public_pending_bootstrap.sql trust-ci/src/adaptive_trust_ci/resources/005_public_pending_bootstrap.sql; do printf "%s " "$p"; git -c core.optionalLocks=false -C <repository>/.review-scratch/trust-ci-public-pending show 1f48c4ccc84192780395b18957ba8c9779e30f00:"$p" | sha256sum; done'
```

Exit0; both exact blobs19b5aa4a0400ba4fae605a0f0b89d77c448c222a20089d39ebfb86f84958cd03. This checks immutable raw identity, not SQL semantics.

New bounded synthetic control:

```bash
taskset -c 16-17 bash -c 'set -eu; cd <repository>/.review-scratch/security-stage-c-0321053-2LL4EU/snapshot; export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 TMPDIR=<repository>/.review-scratch/security-stage-c-0321053-2LL4EU PYTHONPATH=.grok-stack; python3 -c "from pathlib import Path; from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))"; python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_synthetic_forward_registry_keeps_membership_separate_from_digest_keys'
```

Exit0; fingerprint matchedae94088e; one test/two subcases5.116s,OK,zero skips. Synthetic004+005 with privately patched synthetic digests passes (non-vacuous positive); adding matching raw/resource006 bytes and a matching006 digest registry key is still denied, with migration phase cannot be derived. This checks fixed path membership independently of digest keys, not production digest authority or SQL safety.

M1: add only one unknown006 primary-to-mirror row to _PUBLIC_MIGRATION_MIRRORS in private snapshot. The test already patches an unknown006 digest row in its negative subcase. This semantic mutant intentionally turns fixed membership into a broader allowed inventory without changing any other policy/history/mirror condition.

```bash
taskset -c 16-17 bash -c 'cd <repository>/.review-scratch/security-stage-c-0321053-2LL4EU/snapshot; export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 TMPDIR=<repository>/.review-scratch/security-stage-c-0321053-2LL4EU; python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_synthetic_forward_registry_keeps_membership_separate_from_digest_keys'
```

Exit1; one test5.205s; inject_unknown=True failed at assertNotEqual(result.status,"pass") because result was pass/findings(). M1 KILLED. No survivors/inconclusive mutants; no universal mutation-score claim. The test catches exactly the intended forbidden membership widening; candidate source was unchanged.

Read-only inventory/check commands: `git diff --name-status f39547221c2e6226c704745816ad911ac501ca35 HEAD`; `git diff --name-only 326908bf6367b05b65b83818ee84a093c1e45872 HEAD`; `git diff --check f39547221c2e6226c704745816ad911ac501ca35 HEAD` (exit0/no output); `git rev-parse HEAD^{tree}` and sha256sum checker/tests (identities above). Final candidate HEAD/status remained exact/clean. Fingerprint before/after:

```bash
PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 taskset -c 16-17 python3 -c 'import sys; from pathlib import Path; sys.path.insert(0,".grok-stack"); from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))'
```

Exit0, ae94088ebc787e3d2dcb976cea12183a18eeb90235a014c675e67859d4f48b7f both times.

## Unexecuted claims and STOP

No old schema/worker/source-separation matrix, broad SQL drift/history/version/resource-limit matrix, caller/env/CLI suite, actual004+005 byte chain/forward-only full matrix or full verifier was rerun. Unchanged claims were statically inspected; previous executable reports remain attributed to their original identities. The single current synthetic control/mutant proves its named membership property only.

SQL/function semantics, actual PostgreSQL privilege/role/lock/transaction behavior, first-epoch bootstrap, seven-day expiry, lazy reclamation/physical cleanup, quotas/concurrency, production query planning, persistent PR-history hold recovery, broad UPDATE API retirement and operational migration/rollback are unexecuted here. Source005's scoped review is separate; compatible005-aware source/migrator/forward recovery remain necessary after any authorized application. Complete public Task3–5 bindings, final full local qualification, external exact-head App/holdout check and any required signed approvals remain separate. No local report is deployed trust or merge authority.

STOP. Coordinator owns report persistence/new freeze, final gate and separately delegated transport. This review is stale if affected source or identity changes; historical reports cannot approve different SQL pins.
