# Contour B fresh independent test review

Status: **FAIL — original F1–F4 repaired; five new bounded regression subcases still fail.**

Evidence kind: `test_review`; role `test_reviewer`; route `03708e8ba495`. This report binds only the candidate below and supplies no merge, production or external Trust CI authority.

## Source identity, isolation and startup capacity

- Candidate: `<local-path>`.
- Agreed PR base: `63799f8760d3a55028d83ab5ff0116ececf8f7d1`.
- HEAD before/after: `5f96f392a8f3b10068d5a4a033f90fd910e9083b`.
- Git tree before/after: `c265b4c9abf542fc86932c242ade5a0e93ded663`.
- Repository `tree_fingerprint` before/after: `afd34d601fa83a247aaac2344f7ce3aad563491d6dd2e8115779a72cf9186c87`.
- Source staged, unstaged and untracked inventories were clean before and after; porcelain status emitted no records.
- Private scratch: `<local-path>`; exact reproduction under `repo/`.
- Parent `.review-scratch` and unique scratch were verified as real uid-1000-owned, non-sticky mode-0700 directories. `git clone --no-hardlinks --no-checkout <candidate> <scratch>/repo`, then exact detached HEAD checkout, reproduced source HEAD/tree/clean status/fingerprint. Scratch product HEAD/tree/status/fingerprint also remained unchanged after probes.
- Only scratch was writable. Tests used scratch `TMPDIR`, `PYTHONDONTWRITEBYTECODE=1`, `GIT_OPTIONAL_LOCKS=0`, one worker and CPU 17. Each mutant compiled one asserted source-fragment replacement into a fresh in-memory module from the exact scratch source. No candidate or scratch product file was edited.
- Final source identity check: `2026-10-02T23:48:59Z`.

reviewed-tree-modified: no

Startup measurement was recorded before route/repository inspection in `capacity.md`: `2026-10-02T23:44:11Z`; `lscpu --parse=CPU,CORE,SOCKET,ONLINE`, `nproc --all`, `nproc`, `taskset -pc $$`, actual cgroup membership/mount and ancestor cpuset/quota reads. Host: 14 physical cores / 28 online logical CPUs, `0-27`. Default affinity `0,1,8-27`, default nproc 22. Actual cgroup2 membership `/user.slice/user-1000.slice/session-2050.scope`; mount `/sys/fs/cgroup`, root `/`. Session, user-1000 and user.slice each had `cpu.max=max 100000`; root had no quota file. Session/user-1000 cpuset files were absent; nearest applicable user.slice and root effective cpusets were `0-27`. One child-only `taskset -c 0-27` probe returned nproc 28 and affinity 0-27 with unchanged membership/bounds. Verified available capacity: 28; delegated allocation: one worker on CPU 17. No controller/system affinity changes or subagents.

## Disposition of earlier findings

Fresh independent tests confirm all original F1–F4 inputs now behave as required. This is new evidence on the current HEAD, not reuse of the earlier failed review.

| Prior finding | Fresh independently exercised result |
| --- | --- |
| F1: history/past-state qualifiers suppress a current operation | All six original target-history/relative-clause cases select release with high risk, no writer, complete release evidence, release skill and both gates |
| F2: destination/object modifiers negate publication | Original EN staging restriction and RU `без изменения версии` cases retain complete release controls |
| F3: plural descriptive nouns create operations | Original plans/checklists/declarative-plans cases retain feature/review and omit release-readiness |
| F4: historical-marker guard had no isolated regression | Original three marker-only historical cases retain review; disabling that guard now fails four checked-in subcases |

The repair also adds literal checked-in tests for complete release controls, coordinated English plan descriptions, request-prefix negation and raw safety signals. All ten targeted mutants below are killed by the current checked-in matrix.

## Remaining findings

### F5 — P2: historical release declarations with normal version/name syntax create operations

Locations: `.grok-stack/adaptive_grok/router.py:256` and `:264`; missing cases in the historical-declaration test matrix.

Three independently asserted review cases select `release`:

- `Review the note; release v2.1.1 was published yesterday`.
- `Review the note; release v2.1.1 was published`.
- `Review the note; release candidate v2 was published`.

The dotted versions are split at every period before `past_statement` can see `was published`. The parser consequently accepts the first `release v2` fragment as a current operation. The multiword release name is not matched by `past_statement`, which permits at most one name token before the past-state verb. These are ordinary historical declarations of the same class as the checked-in `release v2 was published`, using the repository's version format or a release-candidate name.

Direct observation confirmed false `risk=high`, no writer, `release-readiness`, and scope/design plus production gates. No authority is actually granted, but the requested ordinary review is replaced by operational routing.

Required repair: preserve version tokens during instruction segmentation and recognize this bounded historical subject form. Add literal negative regressions alongside the existing affirmative dotted-version release case; retain object-relative past-state positives from F1.

### F6 — P2: coordinated Russian plan descriptions bypass descriptive scope

Locations: `.grok-stack/adaptive_grok/router.py:260` and `:276`; missing RU counterpart of the English coordinated-plan regressions.

Both independently asserted review cases select `release`:

- `Проведи ревью плана развернуть сборку и опубликовать пакет`.
- `Проведи ревью плана: развернуть сборку и опубликовать пакет`.

`plan_infinitive` only recognizes English plan/checklist/instruction words followed by English `to` and operation verbs. The first Russian plan-description part therefore does not establish plan scope; after splitting at `и`, the descriptive `опубликовать` infinitive is treated as a direct operation. Actual fields again show high-risk release routing, release-readiness and production/scope gates.

This is the RU counterpart of the existing English exclusion, within the advertised EN/RU operations and incidental-plan boundary. Required repair: cover these bounded Russian plan-description forms while keeping a separately delimited affirmative RU publication command detectable.

## Commands and observed results

All test commands ran from `<local-path>`.

Exact adjacent compatibility command:

```bash
env TMPDIR=<local-path> GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 taskset -c 17 python3 -m unittest tests.test_repo_router tests.test_hooks tests.test_reasoning_policy
```

Observed: exit 0; `Ran 81 tests in 63.733s`; `OK`. This is the focused router/hooks/reasoning suite, not the full PR verifier.

Exact fresh independent regression command:

```bash
env TMPDIR=<local-path> GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 taskset -c 17 python3 <local-path> independent
```

Observed: exit 1; nine methods, five failed subcases, zero errors. Seven methods pass: original F1, F2, F3 and F4; supported polite/request forms and independent boundaries; quote/negation/history guard alternatives; raw domain/risk safety and incident operation controls. The two remaining methods fail exactly the five F5/F6 cases above.

Exact mutation loop:

```bash
for mutant in global-target-history-veto global-object-negation-veto singular-descriptive-nouns history-prefix-disabled plan-scope-disabled coordinated-negation-reset quoted-operation-admitted incident-release-gate-lost incident-release-skill-lost raw-domain-scanner-sanitized; do
  printf 'MUTANT %s\n' "$mutant"
  env TMPDIR=<local-path> GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 taskset -c 17 python3 <local-path> mutation "$mutant"
  printf 'EXIT %s\n' "$?"
done
```

Every mutant process ran the 11 checked-in `OperationalIntentTests` methods, exited 1, and had zero errors. Exact definitions are retained in `review_probe.py` in this private scratch.

| Mutant | Claim probed / changed behavior | Result / observed failed subcases |
| --- | --- | --- |
| `global-target-history-veto` | Reintroduce historical/past-state tail veto despite current command | Killed: 6 target-history/relative-clause failures |
| `global-object-negation-veto` | Reintroduce global `без`, `not to`, `no need to` object negation | Killed: 5 modifier/destination failures |
| `singular-descriptive-nouns` | Replace plural plan/checklist/workflow guard forms with singular forms | Killed: 4 descriptive-plural failures |
| `history-prefix-disabled` | Historical-prefix update becomes `historical_context or False` | Killed: 4 marker-only historical failures |
| `plan-scope-disabled` | Replace plan-infinitive context assignment with `False` | Killed: 3 coordinated English plan failures |
| `coordinated-negation-reset` | Reset rather than retain prior negation on each coordinated part | Killed: 5 coordinated-negation failures |
| `quoted-operation-admitted` | Retain quoted/fenced content with delimiters removed | Killed: 4 quoted-content failures |
| `incident-release-gate-lost` | Bind production gate to release intent instead of explicit operation | Killed: 1 RU incident failure missing production gate |
| `incident-release-skill-lost` | Bind release-readiness to release intent instead of explicit operation | Killed: 2 incident failures missing release skill |
| `raw-domain-scanner-sanitized` | Erase double-quoted content before raw domain scanner | Killed: 1 raw-safety failure, missing data/security domains |

No surviving or inconclusive mutants; no mutation-score threshold is asserted. Passing mutation controls do not cancel the five unmodified-candidate regression failures.

`git --no-optional-locks diff --check 63799f8760d3a55028d83ab5ff0116ececf8f7d1..HEAD` emitted nothing and exited 0.

Candidate identity commands before/after were `git --no-optional-locks rev-parse HEAD HEAD^{tree}`, `git --no-optional-locks status --porcelain=v1 --untracked-files=all`, and `env PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 PYTHONPATH=.grok-stack taskset -c 17 python3 -c 'from pathlib import Path; from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))'`; exact matching results are recorded above and in `identity.md`.

## Unexecuted claims and scope limits

- General natural-language parsing, unsupported grammar and adversarial regex-performance/Unicode fuzzing were not attempted. Additional cases are bounded to advertised EN/RU historical and descriptive-plan exclusions.
- Full PR verification, coverage and factory/PostgreSQL checks were not rerun by this reviewer. Coordinator supplied the current `full-pr-suite` pass at `2026-10-02T23:40:21Z`; that prerequisite is not independent reviewer evidence.
- No external exact-head Trust CI, approvals, branch protection or deployed authority behavior was tested. No secrets, remote fetch/push/merge, production action, receipts or candidate writes occurred.
- Static review of the actual base-to-HEAD product diff, repaired tests, requirements and surrounding owner/review/evidence/gate logic is not executable proof of every authority boundary. Adjacent hook tests and concrete raw-safety/incident controls were executed as listed.
- This conclusive FAIL binds the exact clean current candidate. Prior failures F1–F4 are repaired, but F5/F6 require the sole writer and a fresh verification/review cycle; aggregate delivery authority remains with the coordinator.
