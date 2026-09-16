PASS

Independent RELEASE REVIEW — route `627a16845fc4`, receipt kind `release_review`.
Subject: commit `6abc3a14fd9c2c4837e05d4247356fdc6fa091a8` on `docs/release-chain-convention-and-inspected-causes`, base `83925c12` (upstream main). Read-only review; this file is the only write. Verdict is a local independent opinion, not merge authority: the authoritative gate remains the App-owned `adaptive-trust-ci/verified@06ecf1c875bc` check on the exact PR head SHA.

## 1. Important — `DARK_FACTORY_ROADMAP.md` still states the #33 cause is uninspected, contradicting the new record

`grep -rn "not inspected or inferred" --exclude-dir=.git .` → 5 hits. Four are legitimate before-state prose inside this change package (`brief.md`, `architecture.md`, `tasks.md`, `change-spec.yaml`). The fifth is current-tense product documentation:

```
./DARK_FACTORY_ROADMAP.md:98: ... PR #33 (head `6d72d4c859dded241b55e90ae9514ad428a7eb1b`) is the only
open pull request, carrying a current-epoch App conclusion of `FAILURE` while GitGuardian is `SUCCESS`;
its failure cause was not inspected or inferred.
```

After this commit `work_inventory.open_pull_requests[0].failure_cause` states an inspected cause, so the roadmap now asserts a boundary of knowledge that the tree has crossed. `tasks.md` scoped its own check to `grep -c ... PROJECT_STATE.json` (= 0), which is true and does not cover the roadmap. The change-spec objective names only `work_inventory`, so this is outside the written scope, but it is inside the success metric ("no … entry claims an uninspected cause that is in fact inspected"). No false delivery or eligibility claim results; fix forward by dropping that one clause.

## 2. Important — the START_HERE sentence is accurate for R and A, unsatisfied for SR, and states #81 as a rule-plus-explanation rather than an explicit exception

Verified data (`PROJECT_STATE.json` at `6abc3a1`):

- `delivered_change_history.post_v2_0_16_landing.pull_requests` rows: `81, 82, 83, 85, 88, 89, 90, 91, 93, 13, 64, 94`. **#98, #99 and #100 are absent** — the core claim of the new sentence is true. `#101` is also absent, but that ledger's own `record_scope` ends at "before the v2.0.17 release sync", so the sentence's "lists what landed on `main` between publications" stays within that window and is not made false by #101.
- A recursive string walk over `PROJECT_STATE.json` for the chain identities: `78082a2` → 5 hits (`/current_unreleased_change/source_base`, `/local_candidate/source_base`, `/local_candidate/artifact_child/source_parent`, `/local_candidate/artifact_child/zip_source_note`, `/l5_production_preparation/actual_main_observation`); `c86b1a1` → 10 hits (`/observed_main_sha`, `/published_release/merge_commit`, `/current_unreleased_change/artifact_child`, `/current_unreleased_change/tag_and_release`, `/local_candidate/merge_commit`, …); tag object `5c6687ed` → 4 hits including `/published_release/tag_object`. So "the `R` and `A` steps live in `current_unreleased_change` and `local_candidate`" is backed.
- `cfc4a57` → **0 hits**, `#100` → **0 hits**, `#101` → **0 hits**, `83925c1` → **0 hits**. The sentence promises the `SR` step is recorded there; for this chain it is not. The self-reference reason is real (the SR commit is the commit that writes the release record, so it cannot appear in the subtree it creates), but an agent that follows the sentence and looks for the SR identity in `PROJECT_STATE.json` finds nothing. Recommend scoping the sentence to what the data carries, e.g. "the `R` and `A` commits are recorded in `current_unreleased_change` and `local_candidate`, and the `SR` commit is the commit that writes that record".
- Misleading-in-the-bad-direction check: the sentence never implies release-chain heads are recorded nowhere — it names the two subtrees that hold them, and the preceding clause already names `published_release`. The residual wording risk is that "A release chain's own commits are **not** landing rows" is absolute, while row #81 (in the very list named) is a release-chain commit: `6d8f6ab` is `docs(release): record published v2.0.16 - release record successor (#81)`, and the ledger row reads `{"pull_request": 81, "purpose": "release record successor", "head": "26e08254", "merge_commit": "6d8f6aba04b1e049e99f72fc79e8134acf921b5c", "merged_at": "2026-09-14T00:11:30Z", "check_run_id": 103814853460}`, i.e. landed 2026-09-14, inside the v2.0.16→v2.0.17 window. The parenthetical explains #81's presence but does not label it an exception to the stated rule; "the one exception is row #81" would remove the ambiguity. The #81 explanation is consistent with the ledger's own `record_scope` wording, and `git show 6d8f6ab --stat` confirms #81 was a release-record commit (24 files, `PROJECT_STATE.json` +128/-…; at that commit `delivered_change_history` had only the `design_partner_pilot` key, so the row was added by a later commit).

## 3. Verified true — all three replacement causes are verbatim in the retained Trust CI job store, with correct head attribution

```
docker exec adaptive-trust-ci-postgres-1 sh -c "psql ... -Atc \"select pr_number,left(head_sha,8),status,coalesce(failure_code,'') from trust_ci_jobs where pr_number in (33,15,21) order by pr_number, created_at desc\""
15|165d5dd9|failed|verification-failed     21|571cad78|failed|verification-failed   33|6d72d4c8|failed|verification-failed
15|f0635733|failed|verification-failed     21|460a8a01|passed|                      33|6ee6b720|failed|verification-failed
15|cdbdd5f3|failed|verification-failed                                             33|f5e6dcb6|cancelled|superseded-head
15|9dcdf588|failed|verification-failed                                             33|9db3dd66|failed|verification-failed
                                                                                 33|6fe29f28|failed|verification-failed
```

Attributed heads are the newest stored head for #33 and #15, and the failing later head for #21; they match the SHAs pinned in `work_inventory` (`6d72d4c8…`, `165d5dd9…`, `571cad78…` with `460a8a01…` as the earlier one). `root-unittest` exit codes: `33|6d72d4c8 → 1`, `15|165d5dd9 → 1`, `21|571cad78 → 1`, `21|460a8a01 → 0`. Retained command object keys are `name, status, exit_code, duration_seconds, output_sha256, stdout_tail, stderr_tail` (tails only, ~7–9 KB), so presence was re-checked with `position()`/`substr()`, not `LIKE`.

- **#33** — `Ran 642 tests … FAILED (failures=7, skipped=1)`; the failing cases are `test_python_test_runner.PythonTestRunnerTests` (`test_inherited_pytest_selection_cannot_omit_tests`, `test_missing_and_corrupt_current_coverage_fail`, `test_unittest_filename_pattern_is_preserved`). Retained text at offset 2209, verbatim: `'python-unittest': CheckResult(name='python-unittest', status='fail', summary='pytest missing; install .grok-stack/config/python-test-requirements.txt with this Python', …)`. Cause and file attribution are observed. See finding 4a for the one inferred clause.
- **#15** — `Ran 480 tests … FAILED (failures=1, errors=5)`; retained text verbatim: `adaptive_grok.architecture.ArchitectureError: base_sha is not an available commit object` and `RuntimeError: architecture binding requires an exact Git HEAD`. Both quoted messages are real code paths in this tree (`.grok-stack/adaptive_grok/architecture_diff.py:254`, `.grok-stack/adaptive_grok/receipts.py:248`).
- **#21** — `Ran 535 tests … FAILED (errors=1, skipped=1)` → "one error in 535 tests" ✓; retained text verbatim `subprocess.CalledProcessError: Command '['git', '--no-replace-objects', '-C', '/workspace', 'rev-parse', '--verify', 'HEAD^{commit}']' returned non-zero exit status 128.` raised from `tests/test_manifest_package.py:56 _shipped_git_command` → "shipped-zip comparison test" ✓. "An earlier head `460a8a01`… passed all six mandatory commands" is exactly right — that job's command set is `compileall=pass | external-holdout=pass | holdout-bundle-integrity=pass | repository-verification=pass | root-unittest=pass | trust-ci-unittest=pass` (count 6, job status `passed`). The failing head recorded only 3 commands (`external-holdout`, `holdout-bundle-integrity`, `root-unittest=fail`), i.e. a different pipeline revision stopped at the first failure.

## 4. Minor — wording precision in two cause strings

- **#33**: "because the exact runtime executing the mandatory command ships unittest and coverage only" is an inference, not a retained observation; the record proves only that the nested runner reported `pytest missing` (and the same fixture dict shows `coverage: status='fail', summary='required Core run unavailable'`). Also "its own `tests/test_python_test_runner.py` cases **raise**" is imprecise — the cases fail an `assertEqual(result.status, 'pass')` because a subprocess result carried that summary. Softening to "the runtime that executes `root-unittest` has no pytest installed" would keep the claim fully inside the evidence.
- **#21**: the sentence pairs "the later head `571cad78`" with "the superseded head" for the same SHA, which reads as two heads; and "belongs to … rather than to the branch content" is an interpretation (defensible, given `460a8a01` passed). Unlike #33 and #15, this `failure_cause` carries no "historical observation" clause of its own — AC-002's framing survives for #21 only through the sibling `disposition` field ("preserved failure conclusions are historical evidence, not current delivery blockers").

## 5. Verified — currency sweep of the six entry documents

No remaining `not inspected or inferred` in `PROJECT_STATE.json`, `README.md`, `START_HERE.md`, `GROK_BUILD_HANDOFF.md` or `CHANGELOG.md`; the only product-tree hit is finding 1. No sentence describes v2.0.17 as a candidate or pending state — the single regex hit is `START_HERE.md:16` matching on the field name `local_candidate`, and the sentence itself reads "`current_unreleased_change` and `local_candidate` record the published `v2.0.17` release". No #98/#99/#100 reference is described as open; `work_inventory.open_pull_requests` is exactly `[{pull_request: 33, head: 6d72d4c859dded241b55e90ae9514ad428a7eb1b, status: open}]`, and `START_HERE.md` and the roadmap agree that #33 is the only open pull request.

## 6. Verified — no release action, and INV-001/AC-003/FORBID-002 hold

```
git tag --list 'v2.0.1*'   ->  v2.0.1 v2.0.10 v2.0.11 v2.0.12 v2.0.13 v2.0.14 v2.0.15 v2.0.16 v2.0.17
gh release list --limit 3  ->  ...v2.0.17 — ...   Latest   v2.0.17   2026-09-16T01:17:14Z
                               ...v2.0.16 — ...           v2.0.16   2026-09-13T22:04:08Z
                               ...v2.0.15 — ...           v2.0.15   2026-09-05T20:17:20Z
```

Tag set and release list are the already-published chain; nothing new was cut or published by this branch (I listed tags/releases, I did not verify the absence of a tag pointing at `6abc3a1` beyond the fact that no `v2.0.1*` name beyond `v2.0.17` exists). Data-level comparison against `git show 83925c12:PROJECT_STATE.json` (canonical JSON, sorted keys):

```
published_release        IDENTICAL
local_candidate          IDENTICAL
prior_published_releases IDENTICAL
milestones               IDENTICAL
delivered_change_history IDENTICAL   (the convention exists only in START_HERE prose now)
work_inventory           differs     (the three failure_cause strings)
operational_activation   False False
```

The only other changed product files are `START_HERE.md` (one paragraph) and `tests/test_project_state.py` (the two exact-value pins for the #15 and #21 rows, shown in the diff), so the moved values are asserted by the coupled test as AC-001/AC-002 require.

## 7. Verification run (as requested; `scripts/grok_verify.py` deliberately not run)

```
python3 -m unittest tests.test_project_state tests.test_structure tests.test_change_spec -q
Ran 63 tests in 0.670s

OK
```

The commit message's "119 tests OK" figure covers four modules (it also includes `test_manifest_package`); the three-module subset requested here is 63 tests, all passing. I did not independently re-run the 119-test figure.

## Go / no-go

**GO for merging this pull request**, conditional on the normal gate: the App-owned exact-head `adaptive-trust-ci/verified@06ecf1c875bc` Check Run on this PR head plus the human-signed `pull-request-merge` scope. Nothing here touches trust-boundary artefacts — every immutable release subtree is byte-identical to base, `operational_activation` stays false, no tag or release is created or claimed, and every recorded gate cause is reproduced verbatim from the retained job store. The findings above are wording/currency defects in prose, all forward-fixable and none a false certification of delivery or eligibility; I recommend one follow-up commit for finding 1 and, if it is convenient, the #33 softening in 4a. Rollback is `forward_fix` as the spec states.

Genuinely unestablished after this PR, unchanged by it:

- **External pilot acceptance** — no pilot acceptance record; the ledger's `design_partner_pilot` history is preparation evidence, not an accepted pilot.
- **M8 cohort and activation** — the M8 row for PR #64 is explicitly "zero M8 qualifying contribution"; `operational_activation` is false in both `local_candidate` and `current_unreleased_change`; no cohort exists.
- **M9 operational qualification** — `operational_qualification` still records unproven outcomes; deployed Trust CI policy, holdout bundle, images and branch protection remain outside this repository's evidence.
- **PR #33 remains open** with a `FAILURE` conclusion on head `6d72d4c8…`. Its repair prerequisite is now concrete and evidence-backed: the `tests/test_python_test_runner.py` cases fail because the runtime executing `root-unittest` has no pytest (`summary='pytest missing; install .grok-stack/config/python-test-requirements.txt with this Python'`), so either that runtime must carry `.grok-stack/config/python-test-requirements.txt` or the cases must be made satisfiable on a unittest-only runtime; then base/head refresh and a fresh exact-SHA App check.
- **Post-v2.0.17 landing is unrecorded anywhere I checked** — `PROJECT_STATE.json` contains no `83925c1`/`#101` string and no ledger for what has landed since the v2.0.17 sync; that gap is pre-existing and this commit neither creates nor closes it, but the new START_HERE sentence makes it more visible.
