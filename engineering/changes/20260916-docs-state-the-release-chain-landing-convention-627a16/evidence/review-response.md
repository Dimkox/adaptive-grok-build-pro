# Review response — release-chain convention and inspected causes

Reviewed object: `6abc3a1`. The security review returned **FAIL**; both of its Important findings were
defects in my own wording, so they are treated as blockers, not as comments. The follow-up commit on this
branch carries the corrections, and the pull request opens on that head.

## `review-security.md` — FAIL (2 Important, 2 Minor) — all accepted

| # | Finding | What the record actually says | Disposition |
| --- | --- | --- | --- |
| I-1 | Important (INV-002/FORBID-001) — my `#33` cause asserted the CI runtime "ships unittest and coverage only" and implied all seven failures carry the `pytest missing` string | re-read of the retained tail: `Ran 642 tests in 443.587s`, `FAILED (failures=7, skipped=1)`, all seven in `tests/test_python_test_runner.py`, but **one** carries `pytest missing; install .grok-stack/config/python-test-requirements.txt with this Python` (the `workers=2` case) and the other **six** assert `'fail' != 'pass'`, including the unittest-path case `test_unittest_filename_pattern_is_preserved`. The record says nothing about the image's package inventory | **Rewritten.** The entry now quotes the counts and the two distinct failure shapes and states explicitly that the record does not establish the runtime's package inventory, so no claim wider than the message is made |
| I-2 | Important — my `#21` cause quoted a command form that is not verbatim and glossed it as "the job checkout had no resolvable HEAD", which the same record contradicts (it shows the job checking out `571cad78…`) | verbatim: the test's own helper raised `subprocess.CalledProcessError` for `['git', '--no-replace-objects', '-C', '/workspace', 'rev-parse', '--verify', 'HEAD^{commit}']` with exit status 128; `Ran 535 tests in 379.425s`, `FAILED (errors=1, skipped=1)` | **Rewritten.** Quotes the argv and the exit status as recorded, drops the invented mechanism, and states that no further mechanism is claimed |
| M-1 | Minor — my `#15` cause omitted the actual first event (`dubious ownership` and the clone failure) and the `FAILED (failures=1, errors=5)` summary | record: `fatal: detected dubious ownership in repository at '/workspace/.git'`, then `fatal: Could not read from remote repository.`, then `ArchitectureError: base_sha is not an available commit object` from `architecture_diff._exact_commit` and `RuntimeError: architecture binding requires an exact Git HEAD`, with the lone failure `AssertionError: 2 != 0`; `Ran 480 tests in 244.175s` | **Rewritten** with that chain and the exact summary |
| M-2 | Minor — the `#21` entry juxtaposes a six-command pass with a three-command job without saying why | the earlier `460a8a01…` job ran all six mandatory commands; the failing `571cad78…` job aborted at the third, so only three command rows exist | **Explained** in the entry: the pass is attributed to the earlier head and the failure to the later job, and the record's own abort point is what limits the claim |

## Reviewer's clean results, kept as recorded

Only `START_HERE.md`, three `failure_cause` values and two test pins plus this route's package changed;
`published_release`, `local_candidate`, `milestones`, `active_delivery`, `trust_ci` and the frozen migration
range untouched (13/13 activation and external-effect values identical to base); head attribution correct;
no history-presented-as-current wording elsewhere; no credential, key, e-mail, home path or host identity in
the added lines; no new tag or release (`v2.0.17` is reachable from the base and unchanged);
`python3 -m unittest tests.test_project_state tests.test_structure -q` green.

## `review-release.md` — PASS (2 Important, 1 Minor, plus verbatim confirmation of the causes)

| # | Finding | Verified | Disposition |
| --- | --- | --- | --- |
| 1 | Important — `DARK_FACTORY_ROADMAP.md:98` still said #33's "failure cause was not inspected or inferred", a boundary of knowledge this commit had already crossed | `grep -c "not inspected or inferred"` → 1 in the roadmap after my cause rewrite | **Fixed.** The clause now points at the retained record in `work_inventory.open_pull_requests` and keeps the "needs a fresh base/head and check" caveat |
| 2 | Important — my START_HERE sentence claimed the `SR` step also lives in `current_unreleased_change`/`local_candidate`, and presented #81 as rule-plus-explanation rather than an explicit exception | data walk at the reviewed head: landing rows are `81,82,83,85,88,89,90,91,93,13,64,94`; `#100`/`cfc4a57` appear nowhere in `PROJECT_STATE.json` | **Fixed.** The sentence now names what does carry each step (release-sync and artifact-child in the candidate records, the publication in `published_release`/`active_delivery`), states #81 as a recorded exception, and says plainly that this chain's successor is not in the ledger |
| 3 | Minor — `#21`'s wording read as two heads and contained one interpretive clause | re-read of my own string | **Fixed.** Single head named once ("the branch's final head 571cad78…, later marked superseded"), and the attribution reworded to "the error is attributed to that job, not to the branch content" |
| — | `#33` inference flag applied to the pre-rewrite text | the current string no longer contains the "ships unittest and coverage only" clause (it was removed in the security-driven rewrite, and the reviewer's own finding 3 quotes the surviving text as verbatim-correct) | No further change; recorded so the chronology is not read as agreement with a claim I no longer make |

The reviewer independently confirmed all three rewritten causes against the retained job store, including
that `460a8a01…` passed all six mandatory commands while the failing job recorded only three (it stopped at
the first failure), and that both quoted error strings exist as real code paths in this tree.

## Process note

The reviewer disclosed creating and deleting one stray file during its run. `git status` in this worktree
shows only the intended modifications, and the tree it reviewed is the tree the follow-up commit builds on.

This is the third time in two days that an independent reviewer caught me stating more than my evidence
supported (the invented pull-request number in the v2.0.17 successor, the "review verdicts" narrated before
reports existed, and now these two over-attributed causes). The rule now applied without exception on this
branch: quote the record, name the head, and write "the record does not say" where it does not.
