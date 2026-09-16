FAIL

# Independent security review — route `627a16845fc4`, receipt kind `security_review`

Subject: commit `6abc3a1` on `docs/release-chain-convention-and-inspected-causes`
Worktree: `/home/pall/grok-projects/adaptive-grok-build-pro-docsfix` · Base: `83925c12`
Reviewed: 2026-09-16, read-only, against `engineering/changes/20260916-docs-state-the-release-chain-landing-convention-627a16/change-spec.yaml` clauses INV-001, INV-002, FORBID-001, FORBID-002.

Verdict rationale: no leakage, no production/release action, INV-001 holds and the
requested unit tests pass. The change is rejected only on evidence fidelity
(INV-002 / FORBID-001): two recorded causes contain a causal clause that the
retained Trust CI job records do not observe, and one quoted error string is not
a verbatim rendering of the retained output. All three are wording-only fixes.

## Findings

### 1. Important — PR #33 cause asserts an unobserved runtime composition (INV-002, FORBID-001)

`PROJECT_STATE.json` `work_inventory.open_pull_requests[0].failure_cause` states the cause is
that "the exact runtime executing the mandatory command ships unittest and coverage only".
The retained record for head `6d72d4c8` observes only that pytest is missing; it never
enumerates what the executing runtime provides, and in the same stderr tail `coverage` is
reported as `status='fail', summary='required Core run unavailable'` inside the sub-run
result — i.e. nothing in the record supports "unittest and coverage only".

Recorded `pytest missing` text itself is verbatim ✓ and the head attribution is correct
(`head` field `6d72d4c859dded241b55e90ae9514ad428a7eb1b`, job head `6d72d4c8`, exit 1,
`FAILED (failures=7, skipped=1)` after `Ran 642 tests`).

Also over-generalized in the same sentence: "this pull request's own
`tests/test_python_test_runner.py` cases raise" — all 7 failures are in that file ✓, but only
4 of the 7 carry the `pytest missing` string; the entries
`test_inherited_pytest_selection_cannot_omit_tests`,
`test_opted_in_verifier_shards_each_method_once` and
`test_unittest_filename_pattern_is_preserved` show empty assertion detail, so their cause is
not observed either.

Commands and observed output:

```
docker exec adaptive-trust-ci-postgres-1 sh -c "psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -Atc \
 \"select '### '||j.pr_number||' '||left(j.head_sha,8)||' rc='||coalesce(c->>'exit_code','?') \
 ||E'\\n--STDOUT--\\n'||coalesce(c->>'stdout_tail','')||E'\\n--STDERR--\\n'||coalesce(c->>'stderr_tail','') \
 from trust_ci_jobs j cross join jsonb_array_elements(j.result->'commands') c \
 where c->>'name'='root-unittest' and (...) order by j.pr_number\""
### 33 6d72d4c8 rc=1 status=fail
FAIL: test_missing_and_corrupt_current_coverage_fail ... (scenario='missing')
 : {... 'python-unittest': CheckResult(name='python-unittest', status='fail',
   summary='pytest missing; install .grok-stack/config/python-test-requirements.txt with this Python', ...),
     'coverage': CheckResult(name='coverage', status='fail', summary='required Core run unavailable', ...)}
AssertionError: 1 != 0 : Trust CI tests failed: pytest missing; install .grok-stack/config/python-test-requirements.txt with this Python
...
FAIL: test_inherited_pytest_selection_cannot_omit_tests
 :
FAIL: test_opted_in_verifier_shards_each_method_once
 :
FAIL: test_unittest_filename_pattern_is_preserved
 :
Ran 642 tests in 443.587s
FAILED (failures=7, skipped=1)
```

```
ls -l .grok-stack/config/python-test-requirements.txt
ls: cannot access '.grok-stack/config/python-test-requirements.txt': No such file or directory
```
(untracked runtime path; recorded only to show the tree provides no corroborating inventory.)

Fix: drop the "ships unittest and coverage only" clause, or bind it to a record that shows
the runtime inventory; scope the quoted message to the failures that carry it.

### 2. Important — PR #21 cause quotes a non-verbatim error and adds an unrecorded interpretation (FORBID-001)

`PROJECT_STATE.json` `work_inventory.superseded[...]` (`pull_request: 21`) quotes
`"git rev-parse --verify HEAD^{commit} returned non-zero exit status 128"`. The retained
record does not contain that contiguous string; it renders the argv list with separators and
with flags the quote drops:

```
subprocess.CalledProcessError: Command '['git', '--no-replace-objects', '-C', '/workspace',
 'rev-parse', '--verify', 'HEAD^{commit}']' returned non-zero exit status 128.
```

The trailing `returned non-zero exit status 128` and every token are present, but the quoted
form is a compression presented as a quotation.

The gloss "i.e. the job checkout had no resolvable HEAD" is also not stated in the record and
is partly contradicted by it: the same stderr tail shows git successfully detaching onto the
head commit (`Note: switching to '571cad7877431ac5ab5779b53fe9f7effd6859ce'`). What is
observed is that the test's own `git` invocation exited 128; attributing that to the job
checkout is an inference.

The quantitative part of the claim checks out: `Ran 535 tests in 379.425s`,
`FAILED (errors=1, skipped=1)` → "one error in 535 tests" ✓; the erroring test is
`test_shipped_zip_exactly_matches_filtered_tracked_head` ("shipped-zip comparison test") ✓;
head ordering ✓ (`460a8a01` 2026-09-02 00:51:58+00 passed, `571cad78` 2026-09-02 23:43:07+00
failed, so `571cad78` is "the later head") ✓; and `460a8a01` indeed passed six commands:

```
docker exec ... -Ac "select c->>'name' cmd, c->>'status' status, coalesce(c->>'exit_code','?') rc
 from trust_ci_jobs j cross join jsonb_array_elements(j.result->'commands') c
 where j.pr_number=21 and j.head_sha like '460a8a01%' order by 1"
compileall|pass|0
external-holdout|pass|0
holdout-bundle-integrity|pass|0
repository-verification|pass|0
root-unittest|pass|0
trust-ci-unittest|pass|0
```

Fix: quote the `CalledProcessError` line as recorded (or drop the quotes) and replace the
"no resolvable HEAD" gloss with the observed exit-128 fact.

### 3. Minor — PR #15 cause omits the contributing git failures and the run counts

The two quoted strings are verbatim in the retained record ✓
(`base_sha is not an available commit object`, `architecture binding requires an exact Git HEAD`)
and the head attribution is correct (`head` field `165d5dd90a2fc2831a3b85be2562a2bb241c8b14`,
job head `165d5dd9`, exit 1). However the cause's "because the branch's recorded base was not
resolvable in that checkout" is only half the record: the same stderr tail shows git refusing
operations outright, which is the visible mechanism for the unresolvable base, and the cause
omits the outcome counts:

```
.E.E.F...........E........fatal: detected dubious ownership in repository at '/workspace/.git'
	git config --global --add safe.directory /workspace/.git
fatal: Could not read from remote repository.
subprocess.CalledProcessError: Command '['git', 'clone', '-q', '--no-local', '/workspace',
 '/run/trust-ci-tmp/adaptive-grok-receipt-base-sg04er5e/project']' returned non-zero exit status 128.
Ran 480 tests in 244.175s
FAILED (failures=1, errors=5)
```

The recorded cause says "the architecture bootstrap and binding tests raise …", which matches
the 5 errors (three in `test_architecture_fitness.py`, two in `test_change_receipts.py`); the
1 failure (`test_architecture_cli_invalid_model_is_nonzero_and_bootstrap_is_explicit`,
`AssertionError: 2 != 0`) is unattributed. Wording-only completeness gap, no false claim.

### 4. Minor — the #21 sentence compares jobs with different command mandates

"An earlier head `460a8a01`… passed all six mandatory commands" is verified, but the failing
head `571cad78` job carries 3 commands, not 6 (`jsonb_array_length(result->'commands')`):

```
docker exec ... -Ac "select pr_number, left(head_sha,8) head, jsonb_array_length(result->'commands') n_cmds
 from trust_ci_jobs where pr_number in (33,15,21) order by 1,2"
15|165d5dd9|3
15|9dcdf588|3
15|cdbdd5f3|3
15|f0635733|3
21|460a8a01|6
21|571cad78|3
33|6d72d4c8|3
33|6ee6b720|3
33|6fe29f28|3
33|9db3dd66|3
33|f5e6dcb6|
```

The juxtaposition implies an equal mandate; the conclusion "the failure belongs to the
superseded head rather than to the branch content" is an interpretation, not a record field.

## Verified observations (no findings)

Scope of the change:

```
git diff --stat 83925c12..HEAD   →  14 files changed, 391 insertions(+), 6 deletions(-)
git diff 83925c12..HEAD --name-only
PROJECT_STATE.json
START_HERE.md
tests/test_project_state.py
engineering/changes/20260916-docs-state-the-release-chain-landing-convention-627a16/{architecture.md,brief.md,change-spec.yaml,evidence/README.md,release.md,requirements.md,rollback.md,route.json,state.json,tasks.md,test-plan.md}
```

The only non-test product files touched are `START_HERE.md` (1 changed line, the convention
sentence) and `PROJECT_STATE.json` (3 changed lines = 3 insertions + 3 deletions, all three
`failure_cause` values); the 11 remaining files are the change package for this route.
`published_release`, `prior_published_releases`, `local_candidate`, `milestones`,
`active_delivery`, `trust_ci` and the frozen migration range have no diff hunks → INV-001 holds.
`tests/test_project_state.py` changes exactly two pins, both the `retained_unresolved` PR #15
entry and the `superseded` PR #21 entry, matching the JSON byte for byte; the PR #33 entry has
no test pin (its array is not pinned in the test file) — observed, not a defect.

FORBID-002 / no release action:

```
git tag --list 'v2.0.1*'   → v2.0.1 … v2.0.17 (newest tag v2.0.17, creatordate 2026-09-16 01:16:35 +0000)
git merge-base --is-ancestor v2.0.17 83925c12 → v2.0.17 reachable from base (pre-existing)
gh release list --limit 3  → v2.0.17 (Latest, 2026-09-16T01:17:14Z), v2.0.16, v2.0.15 — nothing new
```

Candidate/operational flags unchanged from base — a recursive walk of every
`operational_activation` and `external_effect` key in both blobs:

```
python3 (walk of git show 83925c12:PROJECT_STATE.json vs git show HEAD:PROJECT_STATE.json)
base count 13 head count 13 IDENTICAL
```

Nothing in the commit is pushed: `git log -1 origin/docs/release-chain-convention-and-inspected-causes`
→ `fatal: ambiguous argument ... unknown revision`. PR #33 is still `OPEN` at head
`6d72d4c859dded241b55e90ae9514ad428a7eb1b` (`gh pr view 33`), consistent with the
head-bound "historical observation for that head" wording; none of the three causes is
phrased as current eligibility (the #33 and #15 sentences say "Historical observation", the
#21 sentence sits in `superseded` next to the pre-existing "not current delivery blockers"
disposition).

Leakage scan over every added line of the full diff (all 14 files):

```
git diff 83925c12..HEAD | grep '^+' | grep -nEi 'BEGIN [A-Z ]*PRIVATE KEY|-----BEGIN|ghp_[A-Za-z0-9]{20}|github_pat_|AKIA[0-9A-Z]{16}|eyJhbGciOi|/home/[a-z0-9_.-]+|/root/|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|password|secret|token=|-----BEGIN OPENSSH'
(no matches; grep exit 1)
```

Added lines contain only repository-relative paths, short commit prefixes, branch names, and
job output strings; the only absolute paths anywhere in the cited evidence are the CI
container's own `/workspace` and `/run/trust-ci-tmp/...`, which are not in the committed text.
No credential values, key material, email addresses, host identities or user home paths were
added. `START_HERE.md` mentions `row #81` and the `R`/`A`/`SR` step convention only.

Requested test run:

```
python3 -m unittest tests.test_project_state tests.test_structure -q
----------------------------------------------------------------------
Ran 33 tests in 0.515s

OK
```

`scripts/grok_verify.py` was deliberately not run, per the review brief.
