# Independent code review — PASS with non-blocking minor findings

Route b258608f2ced; change 20261004-task-b25860; reviewer code_reviewer. Reviewed the complete 39-file base-to-HEAD change, requirements, architecture, tasks, controller analysis, complete implementation report, selected reviewer/security/verification instructions, current handoff and relevant surrounding contracts, M7 bridge and release helper. No critical or important findings. This is bounded local review evidence, not merge authorization, external Trust CI success or release-publication evidence.

## Source identity and isolation

- Candidate: `<repository-root>/.review-scratch/m8-one-task-autonomy`.
- Agreed base: `2a8e3839a469b3e05da167e9d8a807bf18e6adbf`.
- Before and after HEAD: `1861e28c8108708f9e85f6e6e78df767f6eb8fa9`.
- Before and after `adaptive_grok.util.tree_fingerprint`: `b4e616f01a67b4fb83dc4e38a50d378e0a9140273b5ca5e5a73e39327609f183`.
- Before and after `git status --porcelain=v1`: empty.
- Private scratch: `<repository-root>/.review-scratch/code-review-9ZBmhA/repo`, created with `git clone --quiet --no-hardlinks <repository-root>/.review-scratch/m8-one-task-autonomy <repository-root>/.review-scratch/code-review-9ZBmhA/repo`. Parent `.review-scratch` and reviewer directory are owned by pall, mode0700, non-sticky. Clean candidate required no dirty/untracked source overlay; cloned HEAD and source fingerprint match exactly. Scratch origin was set to `https://github.com/Dimkox/adaptive-grok-build-pro.git` locally to exercise actual repository identity without any network operation. Ignored runtime was newly generated only in scratch.
- Every candidate command used `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1`. Candidate runtime/index/source/branch/HEAD were not written; no bytecode generated there. Mutations and restores used apply_patch exclusively in the private clone.
- reviewed-tree-modified: no

Own startup discovery was recorded in sibling `capacity.md` before route/source inspection:14physical/28online logical CPUs, process22/affinity0,1,8-27; cgroup2 session2050 under user1000/user.slice, effective cpuset0-27, every applicable ancestor unlimited CPU quota. Child-only taskset widening verified28. Tests used `taskset -c 0-3`, one test process at a time; no child agents or full verifier.

## Strengths and plan alignment

The canonical M7 path changes only constructor/parser/schema minimum from30to1; its currentness_available and external_acceptance_available remain false. New owner evidence is explicitly distinct, binds actual Liqvera/factory source identities and preserves unknown telemetry as null. There is no invented empirical cohort, producer receipt or security approval.

The CLI calls the real persisted consumer across processes. Activation is L1 only; L2 is a ceiling; the action allowlist contains local_read/local_test; all outcomes carry external_authority=false. Each admission recomputes repository/clone/source/profile bindings and checks case/policy/expiry/revocation. Runtime traversal uses descriptor-relative no-follow operations and restrictive directory permissions; activation is exclusive-create and revocation is a policy-scoped tombstone. Source changes do not silently reuse activation. CLI performs no arbitrary command or provider execution.

Version/README/architecture inventory and current continuation identify2.2.0 while preserving v2.1.1 published identity and historical cleanup facts. Release-helper modification is limited to sourcing ZIP/checksum from dist instead of copying them into source packages. No M9 runtime, deployed Trust CI, Actions, protected-branch, key or production changes are present.

## Minor findings

1. `factory/src/adaptive_factory/owner_autonomy.py:190`: extreme valid ISO timestamps can overflow `issued_at + timedelta(hours=1)`. In scratch activation.json, retain all valid bindings and set issued_at=`9999-12-31T23:00:00Z`, expires_at=`9999-12-31T23:59:59.999999Z`; `python3 scripts/grok_m8.py admit --action local_test` exits1 with `OverflowError: date value out of range` and no JSON. Expected malformed/future evidence behavior is structured denied/L0. This remains fail-closed, requires externally edited local state, and cannot arise from normal current activation, so it is non-blocking robustness, not authority escalation. A bounded fix is comparing the positive duration `expires_at - issued_at` against one hour, or translating overflow into ContractError; add a targeted consumer regression.

2. `factory/tests/test_owner_autonomy.py:130`: the synthetic subprocess CLI fixture inherits the checked-in policy's2026-11-04 expiry while CLI reads real wall time. Its positive activation assertion will then fail for policy expiration rather than a regression. Use a future bounded fixture expiry derived for the synthetic CLI checkout, preserving explicit fixed-clock expiry unit tests. This is a future fixture-maintenance limitation, not evidence that today's policy should ignore its expiration. Static observation only; future wall-clock execution was not performed.

Release-wording judgment requested by coordinator: README/current-state repeatedly and explicitly call v2.1.1 a pre-publication snapshot, and CHANGELOG dates2.2.0 as source candidate. These are honest source-time records and do not assert an already-published2.2.0. Retain that temporal framing and make actual GitHub Release metadata authoritative; do not rewrite tested source after publication and reuse old gates. Neutral source-version wording would reduce reader friction but is not a release-blocking correctness defect in this reviewed snapshot.

## Executed claims and mutation evidence

For all scratch Python commands, environment was `GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1`. Let C denote the exact command:

`PYTHONPATH=factory/src:.:.grok-stack taskset -c 0-3 python3 -m unittest factory.tests.test_owner_autonomy.OwnerAutonomyTests.test_cli_full_lifecycle_rechecks_actual_current_source_and_missing_inputs`

Working directory was the private scratch repo above. This is one bounded existing lifecycle test, not the writer's whole suite. Unmodified C passed1test in1.207s; after restoring all source mutants C passed1test in1.183s. It invokes real CLI status, activate, local_test, provider_call, changed tracked source, revoke and missing-policy scenarios in separate processes.

| Claim / isolated mutant | Exact command | Observed result | Outcome |
|---|---|---|---|
| Current source binding enforced; replace `if actual != expected:` with `if False:` | C | exit1, line152: `'admitted' != 'binding_mismatch'`;1test,1failure | killed |
| Revocation enforced; `_revoked` returnsFalse after reading present tombstone instead ofTrue | C | exit1, line155: `'admitted' != 'revoked'`;1test,1failure | killed |
| External action refused; replace `if action not in policy.allowed_actions:` with `if False:` | C | exit1, line148: provider_call exit0 != expected2;1test,1failure | killed |
| Real clean clone missing activation | `python3 scripts/grok_m8.py status` | JSON allowedfalse/L0/reasonactivation_missing | control passed |
| Real clean clone activation/admission | `python3 scripts/grok_m8.py activate`; `python3 scripts/grok_m8.py admit --action local_test` | JSON allowedtrue/L1/reasonsactive,admitted; external_authorityfalse | control passed |
| Real clone external action | `python3 scripts/grok_m8.py admit --action merge` | JSON allowedfalse/L0/reasonaction_not_authorized | control passed |
| Change only persisted profile_digest to64 lowercase d characters | `python3 scripts/grok_m8.py admit --action local_test` | exit2, JSON allowedfalse/L0/reasonbinding_mismatch | input mutant killed |
| Restore profile; set activation issued/expires to2026-10-04T00:00:00Z/01:00:00Z | same admit command | exit2, JSON allowedfalse/L0/reasonactivation_expired | input mutant killed |
| Extreme future timestamp payload described in minor finding1 | same admit command | exit1, OverflowError traceback, no JSON; no permission granted | survived structured-denial assertion; minor finding, not authorization bypass |
| Revoke with malformed/future activation already present | `python3 scripts/grok_m8.py revoke`; `python3 scripts/grok_m8.py admit --action local_test` | revoke JSON revoked; subsequent admission JSON allowedfalse/L0/reasonrevoked | control passed |

Source mutant edits were sequential, individually restored; `git diff --exit-code` afterwards passed and scratch fingerprint again equaled candidate fingerprint. No blanket mutation-score claim. Artifact mutations were deliberate review fixtures, never candidate edits or empirical product evidence.

Other exact read-only observations: `git diff 2a8e3839a469b3e05da167e9d8a807bf18e6adbf..HEAD --check` exited0; `git rev-parse HEAD`, `git status --porcelain=v1`, and `PYTHONPATH=.grok-stack python3 -c 'from pathlib import Path; from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))'` yielded the identical before/after candidate identities above.

## Unexecuted / declined to judge

- Full repository verifier, coverage, PostgreSQL, external exact-head Trust CI, merge and release publication: controller-owned final gates; explicitly outside reviewer execution grant. No passing claim for them.
- Real deployment, provider calls, production/M9 recovery or local-edit/L2 promotion: outside requested bounded owner-local scope; no new authority implied.
- Owner confirmation authenticity: accepted explicit task authority, not rederived as telemetry and not treated as a human-signed external security approval.
- OS-enforced protection against a malicious same-user actor editing executable source or deleting local state: not supplied by this offline local advisory consumer or reviewer configuration. Filesystem no-follow checks were inspected statically; concurrent hostile filesystem races were not executed.
- Exhaustive schema parity, all malformed-JSON/resource-exhaustion cases and every timestamp boundary: not claimed. Important normal refusal classes were checked statically and through the bounded probes above; minor extreme-date gap is disclosed.
- Reproducible release ZIP bytes and publication state after this snapshot: not executed; immutable final-source packaging and external metadata are controller delivery responsibilities.

Assessment: PASS as independent local code/security/spec review with two non-blocking minor limitations. Ready for controller final local gate and required exact-head external checks, not presently an assertion of merge eligibility or completed release.
