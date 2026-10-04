# Fresh code review — contour B repaired candidate

Status: **FAIL — three bounded contextual false positives require repair.** The previous findings are repaired and their regressions pass; this is fresh evidence for the current candidate, not reuse of the earlier review.

## Source and isolation

- Role: route-selected `code_reviewer`, route `03708e8ba495`.
- Candidate: `<local-path>`.
- Actual agreed base: `63799f8760d3a55028d83ab5ff0116ececf8f7d1`.
- HEAD before/after: `5f96f392a8f3b10068d5a4a033f90fd910e9083b`.
- Git tree: `c265b4c9abf542fc86932c242ade5a0e93ded663`.
- Fingerprint before/after: `afd34d601fa83a247aaac2344f7ce3aad563491d6dd2e8115779a72cf9186c87`.
- Candidate porcelain inventory was empty before/after; final identity observation: `2026-10-02T23:49:35Z`.
- Private scratch: `<local-path>`; snapshot at its `snapshot/` child.
- Scratch parent and unique directory were verified as owner pall/UID1000, mode0700, non-sticky. Exact clean source was reproduced by `git clone --no-hardlinks --no-checkout` and detached checkout of the reviewed HEAD; snapshot fingerprint matched before and after.
- All execution and mutants stayed in scratch. Mutants replaced one asserted source fragment in memory in fresh Python processes; scratch product files remained unchanged. No candidate source edits, receipts, subagents, full-suite executions or external operations were performed.

reviewed-tree-modified: no

## Findings

The following three prompts were independently executed on the unmodified scratch snapshot. Each should retain `review` intent because its operational wording describes historical or plan content. Each instead selected `release`, `risk=high`, `release-readiness`, and both scope/design and production-action gates.

### F1 — P2: dotted version subjects evade historical declaration filtering

Location: `.grok-stack/adaptive_grok/router.py:264`.

Reproduction: `Review the note; release v2.1.1 was published yesterday`.

The sentence splitter treats every period as an instruction boundary. It breaks the historical declaration at the version's first dot, so `release v2` reaches command matching without its past-state predicate and is accepted immediately. This is a small variation of the checked-in historical `release v2 was published` case. Preserve numeric version tokens while retaining actual sentence-boundary resets.

### F2 — P2: two-token historical subjects are interpreted as publication instructions

Location: `.grok-stack/adaptive_grok/router.py:256` and `:279`.

Reproduction: `Review the note; publish the reviewed artifact was requested`.

The past-state recognizer allows at most one subject token after an optional article. It therefore misses `the reviewed artifact was requested` and accepts the historical action-shaped declaration as a current command. Expand the bounded direct-declaration recognition without again rejecting relative artifact qualifiers such as `Publish the artifact that was reviewed`.

### F3 — P2: coordinated Russian plan infinitives create operational intent

Location: `.grok-stack/adaptive_grok/router.py:260` and `:276`.

Reproduction: `Проведи ревью плана развернуть сборку и опубликовать пакет`.

The plan-context recognizer only contains English plan/checklist/instruction terms plus `to`. After the Russian descriptive plan part fails command matching, splitting at `и` exposes `опубликовать пакет`, which is accepted as an independent operation. Carry the equivalent bounded Russian descriptive context across coordination, while preserving genuinely separate affirmative commands.

These findings violate AC-002. Classification still creates no operational authority; the failure is incorrect workflow selection.

## Prior findings and current passing evidence

Inspected the entire actual product diff and surrounding intent, raw-domain/risk, ownership, review/evidence and gate construction, plus typed requirements, repair handoff and both initial failed reports. Product inventory remains exactly router.py and test_repo_router.py; other changes are the active package.

The earlier code report is retained byte-identically: both candidate copy and original scratch report SHA256 are `df9ffec5088ef8a177e27ee8fe9a168b88f01b7c07a4e77c0265064d07bf99e8`. Its old source identity is historical, not current acceptance.

Fresh adjacent command, from scratch snapshot:

```bash
taskset -c 16 env TMPDIR=<local-path> GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -m unittest tests.test_repo_router tests.test_hooks tests.test_reasoning_policy
```

Observed: exit0, **81 tests in 41.877s, OK**.

Independent command:

```bash
taskset -c 16 env TMPDIR=<local-path> GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 <local-path> independent
```

Observed: exit0, two methods, zero failures/errors. One method checks 14 literal cases, including all six earlier code-review counterexamples, additional artifact-history qualifiers, coordinated negation, descriptive plans and independent sentence/semicolon resets. Release positives assert complete ownership, risk, skills, reviewers, evidence and gates. The other checks incident-plus-publication containment/operational controls and preservation of raw SQL/auth/production safety inside excluded quotes.

Exact new-finding command:

```bash
taskset -c 16 env TMPDIR=<local-path> GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 - <<'PY'
import sys, tempfile
from pathlib import Path
sys.path.insert(0,'.grok-stack')
from adaptive_grok.router import build_route
cases=(
 'Review the note; release v2.1.1 was published yesterday',
 'Review the note; publish the reviewed artifact was requested',
 'Проведи ревью плана развернуть сборку и опубликовать пакет',
)
with tempfile.TemporaryDirectory() as tmp:
 for prompt in cases:
  r=build_route(Path(tmp),prompt,'review-bounded-repro',base_commit_override=None,base_fingerprint_override='0'*64)
  print(repr(prompt),'->',r.intent,r.risk,r.workflow_skills,r.human_gates)
PY
```

Observed for each: `release high ['adaptive-delivery', 'release-readiness'] ['scope_and_design_approval', 'production_action_approval']`.

`git diff --check 63799f8760d3a55028d83ab5ff0116ececf8f7d1..HEAD` returned exit0/no output.

## Bounded mutation evidence

Exact corrected mutation loop, from scratch snapshot:

```bash
for review_mutant in release-precedence-lost object-history-veto-restored object-negation-veto-restored relative-past-veto-restored plan-context-lost plural-noun-guard-lost historical-prefix-guard-lost quote-filter-lost; do
  taskset -c 16 env TMPDIR=<local-path> GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 <local-path> "$review_mutant"
  printf 'PROBE_EXIT=%s\n' "$?"
done
```

Each valid invocation ran all eleven checked-in OperationalIntentTests methods.

| Mutant | Claim probed | Final result |
| --- | --- | --- |
| release-precedence-lost | Move release below bugfix/review | **Killed:** 39 assertion failures |
| object-history-veto-restored | Add global yesterday/вчера veto inside objects | **Killed:** 4 assertion failures |
| object-negation-veto-restored | Add global без/not-to/no-need-to object veto | **Killed:** 5 assertion failures |
| relative-past-veto-restored | Reject any past-state verb in the command tail | **Killed:** 3 assertion failures |
| plan-context-lost | Remove descriptive infinitive context propagation | **Killed:** 3 assertion failures |
| plural-noun-guard-lost | Restore singular-only plan/checklist/workflow/policy guards | **Killed:** 5 assertion failures |
| historical-prefix-guard-lost | Remove historical-prefix propagation | **Killed:** 4 assertion failures |
| quote-filter-lost | Retain quoted operation text | **Killed:** 4 assertion failures |

All valid mutants exited1 with zero test errors. No valid mutant survived. These are scoped probes, not a blanket mutation-score claim.

The first eight mutation invocations were **inconclusive setup failures** because the absolute-path harness did not put snapshot cwd on sys.path and could not import tests. This was corrected in the private harness and every mutant rerun successfully. The root cause is recorded in scratch mistakes.md; setup failures are not counted as kills.

## Capacity and verifier observations

Fresh startup snapshot was recorded in scratch capacity.md before repository inspection at `2026-10-02T23:43:56Z`. Commands covered lscpu, nproc/all, affinity, actual cgroup/mounts, every visible ancestor cpuset/quota and one child-only widening probe. Observed 14 physical cores/28 online logical CPUs; default affinity0,1,8-27/nproc22; inherited effective cpuset0-27 and unlimited visible quotas under /user.slice/user-1000.slice/session-2050.scope. Child-only probe succeeded with affinity0-27/nproc28; controller affinity unchanged. Review used one worker on CPU16.

Read-only inspection of the coordinator's final-verify.json found current timestamp `2026-10-02T23:40:21+00:00`, matching fingerprint, status pass, full-pr-suite, reason unallowlisted-path, changed-path digest `51f3d35edc6969fca012ea7ab8c8c0d3c1e41ac9905e9ae811f0e446f6c87af2`, and no scope-selected skips. Coverage, factory-unit and factory-postgres-exit are reported passing. This is inspected coordinator evidence, not my own full-suite execution, and does not invalidate the reproduced findings.

## Unexecuted claims and declined scope

- General EN/RU language understanding, exhaustive grammar/Unicode quotes and adversarial regex performance were not tested.
- Schema stability and absence of grant creation were inspected statically; no exhaustive executable authority proof was performed.
- Full PR verification, deployed Trust CI, protected branches, signed approvals, operational deployment and merge eligibility were not independently tested or judged.
- All earlier repairs have bounded current evidence, but current completion is blocked by F1-F3. Repair through the sole selected writer and obtain fresh exact-state verification and independent review, including the planned aggregate source candidate.
