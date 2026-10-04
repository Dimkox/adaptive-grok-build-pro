# Code review — contour B

Status: **FAIL — changes required.** Two P1 defects drop release controls for supported affirmative commands; one P2 defect treats descriptive plan content as an instruction.

## Source and isolation

- Route: `03708e8ba495`; role: `code_reviewer`.
- Candidate: `<local-path>`.
- Reviewed HEAD: `e1c7a01d3fe057c90e80e547c42aadddbae99d11`.
- Agreed PR base: `63799f8760d3a55028d83ab5ff0116ececf8f7d1`.
- Git tree: `3cfcf87a4e6c614ed0d2118a4f186cd3a8cbb0ac`.
- Candidate fingerprint before and after: `2c2e80182a216afc38fae7f9fd7844b5c7ace88bcb9aea41d525c80323f4fc41`.
- Candidate status was clean before and after. Final observation: `2026-10-02T23:12:00Z`.
- Private scratch: `<local-path>`.
- Scratch parent and reviewer directory were verified as owner `pall`, UID `1000`, mode `0700`, non-sticky.
- Snapshot reproduced with `git clone --no-hardlinks --no-checkout` followed by detached checkout of the exact reviewed HEAD. Its clean fingerprint matched the candidate.
- All tests and mutations ran in scratch. No candidate files, index, HEAD, caches or artifacts were changed.

reviewed-tree-modified: no

## Findings

### P1 — Historical words in an artifact description suppress a current publication command

Location: `.grok-stack/adaptive_grok/router.py:257`.

`historical.search(clause)` rejects the whole clause before locating the operative command. Consequently, history describing the artifact—or another coordinated task—suppresses an affirmative publication request.

Executed reproductions:

| Prompt | Expected intent | Observed intent |
| --- | --- | --- |
| `Publish the artifact built yesterday through a pull request` | `release` | `review` |
| `Review yesterday's changes and publish v3 through PR` | `release` | `review` |

Both produced low-risk review routes, only `adaptive-delivery` and `verification-evidence`, code/test reviews and evidence, and **no human gates**. They lost `release-readiness`, security/release reviews and evidence, `scope_and_design_approval`, and `production_action_approval`.

These are supported direct publication commands, not historical publication instructions. This violates AC-001/AC-002 and then AC-003. Historical filtering should distinguish past instructions from history attached to a current command or its object, while retaining the existing historical negative cases.

### P1 — Negation anywhere in the object suppresses an affirmative operation

Location: `.grok-stack/adaptive_grok/router.py:262`.

`negative.search(part)` treats negative words anywhere in the part as negation of its operation. Russian `без` (“without”) can modify the requested artifact or deployment scope without negating publication.

Executed reproductions:

| Prompt | Expected intent | Observed intent |
| --- | --- | --- |
| `Опубликуй пакет без README через PR` | `release` | `review` |
| `Выпусти релиз без деплоя через pull request` | `release` | `review` |
| `Publish the package with no need to restart; review the PR` | `release` | `review` |

All three produced the same low-risk review route and missing release controls described above. The first means “Publish the package without README through PR”; the second explicitly requests a release while excluding deployment.

Negation must remain coordinated across genuinely negative commands, but should be associated with the requested action rather than arbitrary text in its object. These cases violate AC-001 and AC-003.

### P2 — Splitting descriptive infinitives promotes plan content into a command

Location: `.grok-stack/adaptive_grok/router.py:260`.

Executed reproduction:

```text
Review the plan to deploy and publish the build
```

Expected: `review`, with the plan’s operations remaining descriptive.

Observed: `release`, with `release-readiness` replacing the review intent’s `verification-evidence` skill.

Splitting at `and` produces `publish the build`, which is matched as a fresh imperative even though it remains coordinated content of “the plan to …”. This contradicts the function’s stated exclusion of plans “to deploy” and AC-002.

Raw deployment text may legitimately retain conservative risk and production gates; that is separate from selecting release intent. Preserve descriptive context across its coordinated infinitives without breaking genuine mixed requests such as `Review this PR and publish the package`.

## Executed evidence

All test processes used one worker on CPU `16`, with `PYTHONDONTWRITEBYTECODE=1`.

Baseline:

```bash
taskset -c 16 env GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_repo_router.OperationalIntentTests
```

Observed: **6 tests passed**, `0.096s`.

Adjacent compatibility after restoring every scratch mutant:

```bash
taskset -c 16 env GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_repo_router tests.test_hooks tests.test_reasoning_policy
```

Observed: **76 tests passed**, `27.905s`.

Context reproductions:

```bash
taskset -c 16 env GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 python3 <local-path>
```

The script called `build_route` for the six prompts above against an empty temporary repository, using `base_commit_override=None` and `base_fingerprint_override='0' * 64`. It printed intent, risk, write owner, skills, reviews, evidence and gates. All six discrepancies were observed on the restored exact source.

```bash
git diff --check 63799f8760d3a55028d83ab5ff0116ececf8f7d1..e1c7a01d3fe057c90e80e547c42aadddbae99d11
```

Observed: exit `0`, no output.

The coordinator’s `.grok-stack/runtime/final-verify.json` was inspected read-only. It reports `pass`, the matching candidate fingerprint, `full-pr-suite`, reason `unallowlisted-path`, rejected product path `router.py`, and no scope-selected skipped checks. Coverage and factory/PostgreSQL checks are reported passing. This is inspected coordinator evidence; I did not rerun that suite.

## Bounded mutation probes

Each mutant was applied only to scratch, tested independently, then restored using `apply_patch`. Final scratch `git diff --exit-code` passed and its fingerprint matched the original source.

| Mutant | Claim probed | Observed result |
| --- | --- | --- |
| Move release below bugfix/review in the priority ladder | Explicit operations survive PR/review/fix vocabulary | **Killed:** 17 assertion failures, zero errors |
| Remove quoted-span filtering | Quoted multiline/incomplete text and fenced commands remain context | **Killed:** 3 assertion failures, zero errors |
| Replace coordinated negation propagation with `negated = False` | Negation carries across coordinated operations | **Killed:** 2 assertion failures, zero errors |

Exact commands:

```bash
taskset -c 16 env GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 python3 <local-path> tests.test_repo_router.OperationalIntentTests.test_affirmative_operation_survives_pr_review_and_fix_words

taskset -c 16 env GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 python3 <local-path> tests.test_repo_router.OperationalIntentTests.test_quoted_and_historical_operations_are_context_only

taskset -c 16 env GROK_TEST_WORKERS=1 PYTHONDONTWRITEBYTECODE=1 python3 <local-path> tests.test_repo_router.OperationalIntentTests.test_negated_operations_do_not_mask_code_or_review_tasks
```

All exited `1` from assertion failures. No mutant survived or was inconclusive. These results establish the named probes only; no blanket mutation threshold is claimed.

## Capacity evidence

Startup measurement was recorded before repository inspection in scratch `capacity.md`.

Commands included `lscpu`, `nproc --all`, `nproc`, `taskset -pc $$`, actual `/proc/self/cgroup` and cgroup mount discovery, ancestor cpuset/quota reads, and one child-only `taskset -c 0-27` widening probe.

Observed at `2026-10-02T23:06:23Z`: 14 physical cores, 28 online logical CPUs, default affinity `0,1,8-27`, effective inherited cpuset `0-27`, and unlimited visible ancestor CPU quotas. The child probe exposed 28 CPUs with affinity `0-27`; controller affinity was unchanged. Review allocation remained one worker on CPU `16`.

## Unexecuted claims and declined judgments

- Raw risk/domain scanning, persisted Route schema, and absence of grant creation were inspected statically. No dedicated mutation or exhaustive executable proof covers those claims.
- General English/Russian language understanding, exhaustive quote nesting, and regex performance under adversarial input were not tested; this remains bounded grammar.
- Deployed Trust CI policy, exact-head external checks, branch protection, signed approvals, deployment and merge eligibility were not evaluated. They are outside this source review and its authority.

The existing baseline and adjacent tests pass, but they omit the six executed context discrepancies above. Return the findings to the sole selected B writer, add regression coverage, and obtain fresh verification and independent reviews for the repaired candidate.
