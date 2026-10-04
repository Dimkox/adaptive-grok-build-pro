# Contour B independent test review

Status: **FAIL — repair and regression coverage required.**

Evidence kind: `test_review`. Role: route-selected `test_reviewer`, route `03708e8ba495`. This is a local independent review, not merge approval or external Trust CI evidence.

## Source identity and isolation

- Candidate: `<local-path>`.
- Actual agreed PR base: `63799f8760d3a55028d83ab5ff0116ececf8f7d1`.
- HEAD before and after: `e1c7a01d3fe057c90e80e547c42aadddbae99d11`.
- Git tree before and after: `3cfcf87a4e6c614ed0d2118a4f186cd3a8cbb0ac`.
- Repository `tree_fingerprint` before and after: `2c2e80182a216afc38fae7f9fd7844b5c7ace88bcb9aea41d525c80323f4fc41`.
- Before/after porcelain status emitted no records: no staged, unstaged or untracked candidate changes.
- Scratch: `<local-path>`; reproduction at its `repo/` child.
- Scratch parent and unique directory were verified as real, uid-1000-owned, non-sticky mode-0700 directories. Reproduction used `git clone --no-hardlinks --no-checkout <candidate> <scratch>/repo` and detached checkout of the exact HEAD. Scratch HEAD, Git tree, clean inventory and repository fingerprint matched candidate before probes and still matched after probes.
- All tests and mutations ran from scratch. `TMPDIR` pointed into reviewer scratch, `PYTHONDONTWRITEBYTECODE=1` prevented import caches, and Git reads disabled optional locks. Mutations replaced one source fragment in a fresh in-memory module loaded from the exact scratch copy; no candidate or scratch product files were edited.
- Snapshot evidence: `capacity.md`, `identity.md`; executable probe and exact mutant definitions: `review_probe.py`, all in the reviewer directory above.
- Final candidate identity check: `2026-10-02T23:13:44Z`.

reviewed-tree-modified: no

## Capacity discovery

Startup resource discovery preceded route/repository inspection and was recorded in reviewer scratch. Commands were `date -u`, `lscpu`, `nproc --all`, `nproc`, `taskset -pc $$`, `/proc/self/cgroup`, cgroup mountinfo and ancestor cpuset/quota reads.

At `2026-10-02T23:06:40Z`: host topology was 14 physical cores / 28 online logical CPUs (`0-27`); default process affinity was `0,1,8-27`, and `nproc` reported 22. Actual cgroup2 membership was `/user.slice/user-1000.slice/session-2050.scope` under `/sys/fs/cgroup`. Session, user-1000 and user.slice quotas were all `max 100000`; root had no quota file. Session and user-1000 lacked cpuset files; nearest applicable user.slice and root effective cpusets were `0-27`. The single bounded child-only `taskset -c 0-27` probe succeeded with 28 CPUs and unchanged membership/bounds. Verified available capacity was 28 CPUs, but the delegated reviewer allocation remained exactly one worker on CPU 17. No controller/system affinity changed. No subagents were spawned.

## Findings

### F1 — P1: current operations with historical target qualifiers lose release controls

Location: `.grok-stack/adaptive_grok/router.py:257` and `:269`; missing coverage in `tests/test_repo_router.py:OperationalIntentTests`.

The parser treats a historical marker anywhere in the clause, or a past-state verb anywhere after the action, as proof the operation itself is historical. Direct supported EN/RU commands can instead describe the target's preparation or review history.

The following new independent regressions failed on the unmodified candidate, selecting `review` instead of `release`:

- `Publish the artifact reviewed yesterday through a pull request`.
- `Опубликуй пакет собранный вчера после ревью`.
- `Publish the artifact that was reviewed through a pull request`.
- `Deploy the build that has been reviewed through a pull request`.
- `Опубликуй пакет который был проверен на ревью`.

Direct route observation for the first and third examples showed `risk=low`, `workflow_skills=['adaptive-delivery', 'verification-evidence']`, and `human_gates=[]`. They lose `release-readiness` and both expected release gates. A comma before the RU relative clause happened to avoid the past-verb failure, demonstrating punctuation-dependent scope rather than a different requested operation. These are bounded direct command forms already admitted by the supported grammar, not a request for general natural-language parsing.

Required repair: distinguish historical instruction context from object qualifiers, with literal positive and historical-negative regression cases that assert complete release obligations.

### F2 — P1: object/destination restrictions are treated as operation negation

Location: `.grok-stack/adaptive_grok/router.py:252` and `:262`; missing affirmative modifier coverage in the negation matrix.

`negative.search(part)` scans the entire part. The `без` and `not to` alternatives can describe a positive operation's object or destination rather than negate the action.

Independent regressions failed:

- `Опубликуй пакет без изменения версии после ревью` selected `review` rather than `release`.
- `Publish the artifact not to production but to staging after review` selected `review` rather than `release`.

The RU case had `risk=low`, only the review workflow skill, and no human gates. In the EN case the raw `production` signal still conservatively supplies existing risk/gate behavior, but the operational workflow classification is lost.

Required repair: bind operation negation to the command/request prefix and preserve coordinated negative lists, while allowing object modifiers and destination restrictions. Add both positive modifier regressions and true-negation controls.

### F3 — P2: plural descriptive nouns escalate ordinary work to release

Location: `.grok-stack/adaptive_grok/router.py:243` and `:273`; missing plural-descriptive coverage.

The descriptive guard contains singular `plan` and `checklist`, but not their ordinary plural forms. New independent regressions showed:

| Prompt | Expected | Actual |
| --- | --- | --- |
| `Create release plans` | `feature` | `release` |
| `Prepare release checklists` | `feature` | `release` |
| `Review the report; release plans are listed below` | `review` | `release` |

For `Create release plans`, actual routing selects `risk=high`, no write owner, `release-readiness`, and production/scope gates. This prevents the ordinary document preparation route, contradicting the existing singular-plan exclusion. The declarative third example likewise creates operational intent from incidental release nouns.

Required repair: cover plural forms of the supported descriptive nouns, with literal ordinary-intent/no-release-skill expectations.

### F4 — P2: historical-marker regression tests do not independently exercise that guard

Removing only `if historical.search(clause):` from the parser survived all six checked-in `OperationalIntentTests` methods with zero failures/errors. Current historical examples are also rejected by anchored command matching or redundant past-state verbs, so they do not prove the marker guard is working.

Reviewer-added marker-only cases passed the unmodified candidate and killed this mutant in all three subcases:

- `Review the report; yesterday, publish the artifact`.
- `Review the report; last week, deploy the build`.
- `Проведи ревью отчета; вчера, опубликуй пакет`.

Required coverage: add an isolated historical-marker negative that does not also contain a past-state verb or a non-command prefix on the action part. Keep this alongside F1 positive object-history cases.

## Executed commands and observations

All test commands below ran with working directory:

`<local-path>`

Exact baseline command:

```bash
env TMPDIR=<local-path> GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 taskset -c 17 python3 -m unittest tests.test_repo_router tests.test_hooks tests.test_reasoning_policy
```

Observed: exit 0, `Ran 76 tests in 44.451s`, `OK`. This executes the current operational matrix and adjacent ordinary-router, hook and reasoning-policy contracts independently in scratch.

Exact independent regression command:

```bash
env TMPDIR=<local-path> GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 taskset -c 17 python3 <local-path> independent
```

Observed: exit 1, `Ran 9 tests`, `FAILED (failures=10)`, zero errors. Ten failing subcases are precisely F1-F3. Supported polite/request EN/RU forms, independent sentence/semicolon/newline boundaries, coordinated negation, additional quote/history exclusions, incident containment+publish controls, and raw security/domain preservation all passed their independent methods. These passing subsets do not cancel the failure verdict.

Exact checked-in matrix mutation loop:

```bash
for mutant in quoted-operation-admitted coordinated-negation-reset history-guard-removed incident-release-gate-lost incident-release-skill-lost; do
  printf 'MUTANT %s\n' "$mutant"
  env TMPDIR=<local-path> GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 taskset -c 17 python3 <local-path> mutation "$mutant"
  printf 'EXIT %s\n' "$?"
done
```

Exact independent historical/safety mutant commands:

```bash
env TMPDIR=<local-path> GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 taskset -c 17 python3 <local-path> history-probe
env TMPDIR=<local-path> GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 taskset -c 17 python3 <local-path> history-probe history-guard-removed
env TMPDIR=<local-path> GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 taskset -c 17 python3 <local-path> safety-probe raw-domain-scanner-sanitized
```

Observed: clean historical probe exit 0 / one method passed; historical mutant exit 1 / three subcase failures; raw-domain mutant exit 1 / one failure, missing both `data` and `security` task domains. The raw-domain test passed on the clean candidate in the independent suite.

`git --no-optional-locks diff --check 63799f8760d3a55028d83ab5ff0116ececf8f7d1..e1c7a01d3fe057c90e80e547c42aadddbae99d11` emitted nothing and exited 0.

## Mutation claims and outcomes

| Mutant | Exact changed behavior | Test claim | Result and observed output |
| --- | --- | --- | --- |
| `quoted-operation-admitted` | Quote erasure replaced by retaining quote content with delimiters stripped | Quoted multiline/fenced operations remain context | **Killed** by checked-in matrix: 6 methods, 3 failed subcases, zero errors, exit 1 |
| `coordinated-negation-reset` | `negated = negated or bool(...)` becomes `negated = bool(...)` | Negation persists through comma/and action lists | **Killed**: 6 methods, 2 failed subcases (`Never deploy and publish`, `Do not deploy and then publish`), exit 1 |
| `history-guard-removed` | `if historical.search(clause):` becomes `if False:` | Historical markers exclude action-shaped text | **Survived checked-in matrix**: 6 methods, zero failures/errors, exit 0. **Killed by independent marker-only probe**: 3 failed subcases, exit 1. This is F4, not a clean coverage result |
| `incident-release-gate-lost` | Production gate condition uses `intent == 'release'` instead of `operational_intent` | Incident+publish keeps operational gate without relying on raw production/deploy words | **Killed**: RU incident subcase loses `production_action_approval`, exit 1 |
| `incident-release-skill-lost` | Operational skill condition uses `intent == 'release'` | Incident priority keeps `release-readiness` | **Killed**: both incident subcases fail missing skill, exit 1 |
| `raw-domain-scanner-sanitized` | `_domains(prompt, repo)` receives text with double-quoted content erased | Excluded operations do not sanitize raw domain/risk safety scanning | **Killed** by independent raw-safety test: `data` and `security` absent, one method failure, exit 1 |

Mutants ran in separate fresh Python processes using exact scratch source plus one asserted single-fragment replacement. No compilation/setup errors occurred. No mutation-score threshold is claimed.

## Coverage limits and declined scope

- This is bounded EN/RU intent/parser test review, not general linguistic qualification. Unsupported grammar, regex adversarial-performance fuzzing and exhaustive Unicode quote forms were not executed.
- Full PR verifier, total coverage, factory/PostgreSQL checks and external exact-head Trust CI were not independently rerun by this reviewer. The coordinator owns those checks; its reported pass is not substituted for the observed failed independent regressions here.
- Static inspection covered actual product diff, surrounding risk/domain/write ownership and gate construction, typed requirements and test plan. It is not an executable proof of every operational-authority boundary. Adjacent hook tests were executed, but deployed approvals, protected-branch behavior and production actions were deliberately outside scope.
- No version/state/classifier repair, candidate write, receipt write, external fetch/push/merge/deploy, secret access or human approval operation was performed. Coordinator persists reports and delegates repairs to the sole selected writer.
- Source and snapshot remained exact and clean, so the result is conclusive for this candidate. Any repair/new HEAD requires fresh verification and independent review.
