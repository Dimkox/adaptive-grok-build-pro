# Test review — root decisions.md / mistakes.md lock

Change: `20260816-user-query-я-все-еще-не-вижу-файлов-из-промпта-д-ba1615`  
Route: `ba1615416da5`  
Reviewer: `test_reviewer` (read-only) · write owner: `general_implementer`  
Reviewed: 2026-08-16  
Did **not** re-run unittest / `grok_verify` (would dirty receipts). Inspected `tests/test_structure.py`, current `AGENTS.md` / root logs / `engineering/` stubs, `test-plan.md`, `requirements.md`, `evidence/implementation.md`, prior d55ce4 test wording, and the official verification receipt.

**PASS.**

`tests/test_structure.py` actually locks the four required properties. It is not a bare `assertIn('decisions.md')`. The same assertions would fail on the pre-move tree (logs only under `engineering/`, `AGENTS.md` bullets naming those paths). Do not return this to `general_implementer` for structure-test gaps.

Official `grok_verify --mode pr` on this fingerprint is **fail**, but the failure is an unrelated `project_copy` race, not `StructureTests`. Re-run verify before binding a pass receipt. That does not make these locks a false green.

---

## Verdict

| Gate | Result |
| --- | --- |
| Root `decisions.md` / `mistakes.md` exist | **Locked.** `is_file()` on `ROOT / 'decisions.md'` and `ROOT / 'mistakes.md'`, not a substring search. |
| `AGENTS.md` names those exact filenames, not `engineering/` | **Locked.** Prefix requires `log it in decisions.md` / `record it in mistakes.md` and forbids `engineering/decisions.md` / `engineering/mistakes.md`. |
| `engineering/` files are short stubs, not a second log | **Locked.** Sibling `test_engineering_self_learning_stubs_are_pointers`. |
| First heading remains `## Agent self-learning` | **Locked.** Exact `headings[0]` equality kept from d55ce4. |
| Bare `assertIn('decisions.md')` false green | **Avoided.** See matrix below. |
| Would fail on the pre-move tree | **Yes.** Independent reconstruction matches the claimed red run. |
| Product-test adequacy for this delta | **PASS.** Covers `test-plan.md` and `requirements.md` test rows. |
| Official verification receipt | **fail** — unrelated `project_copy` flake (see below). Not a structure-test miss. |

Would I block on test adequacy? **No.**

---

## What the tests lock

```22:60:tests/test_structure.py
    def test_agents_md_starts_with_self_learning(self) -> None:
        self.assertTrue((ROOT / 'decisions.md').is_file(), 'decisions.md')
        self.assertTrue((ROOT / 'mistakes.md').is_file(), 'mistakes.md')
        decisions_head = (ROOT / 'decisions.md').read_text(encoding='utf-8')[:400]
        mistakes_head = (ROOT / 'mistakes.md').read_text(encoding='utf-8')[:400]
        self.assertIn('Patterns that paid for themselves', decisions_head)
        self.assertIn('Root causes, not symptoms', mistakes_head)
        text = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        headings = [line for line in text.splitlines() if line.startswith('## ')]
        self.assertTrue(headings, 'AGENTS.md has no ## headings')
        self.assertEqual(headings[0], '## Agent self-learning')
        entrypoint = text.find('## Mandatory entrypoint')
        self.assertGreaterEqual(entrypoint, 0, 'missing ## Mandatory entrypoint')
        prefix = text[:entrypoint]
        self.assertIn('log it in decisions.md', prefix)
        self.assertIn('record it in mistakes.md', prefix)
        self.assertNotIn('engineering/decisions.md', prefix)
        self.assertNotIn('engineering/mistakes.md', prefix)
        self.assertIn('worth the effort', prefix)
        self.assertIn('no more than 3 sentences', prefix)
        self.assertIn('root cause (not the symptom)', prefix)

    def test_engineering_self_learning_stubs_are_pointers(self) -> None:
        for rel, dest in (
            ('engineering/decisions.md', '/decisions.md'),
            ('engineering/mistakes.md', '/mistakes.md'),
        ):
            path = ROOT / rel
            self.assertTrue(path.is_file(), rel)
            text = path.read_text(encoding='utf-8')
            lines = text.splitlines()
            self.assertLessEqual(len(lines), 5, rel)
            self.assertIn('Canonical log is /', text)
            self.assertIn(f'Canonical log is {dest}', text)
            self.assertIn('Do not append here', text)
            self.assertFalse(
                any(line.startswith('## 20') for line in lines),
                rel,
            )
```

`ROOT` is `Path(__file__).resolve().parents[1]` (repo root). Existence is a real path check, so `engineering/decisions.md` cannot satisfy `(ROOT / 'decisions.md').is_file()`.

Current product text those asserts hit:

```3:6:AGENTS.md
## Agent self-learning

- If you make a decision that turns out to be correct and worth the effort, log it in decisions.md (pattern + why it worked, no more than 3 sentences).
- If you make a mistake that leads to a problem, identify the root cause (not the symptom) and record it in mistakes.md.
```

```1:3:engineering/decisions.md
# Moved

Canonical log is /decisions.md. Do not append here.
```

```1:3:engineering/mistakes.md
# Moved

Canonical log is /mistakes.md. Do not append here.
```

Root files start with the live-log headers (`Patterns that paid for themselves` / `Root causes, not symptoms`), not the stub text.

---

## False-green trap: bare `assertIn('decisions.md')`

Pre-move `AGENTS.md` (d55ce4, quoted in that change’s code-review) was:

```
log it in engineering/decisions.md (pattern + why it worked, no more than 3 sentences).
record it in engineering/mistakes.md.
```

| Assert on that pre-move prefix | Result | Why |
| --- | --- | --- |
| `assertIn('decisions.md', prefix)` | **PASS (false green)** | substring of `engineering/decisions.md` |
| `assertIn('mistakes.md', prefix)` | **PASS (false green)** | same |
| old d55ce4 `assertIn('engineering/decisions.md', prefix)` | **PASS** | that *was* the live sink |
| **actual** `assertIn('log it in decisions.md', prefix)` | **FAIL** | after `log it in ` comes `engineering/`, not `decisions.md` |
| **actual** `assertIn('record it in mistakes.md', prefix)` | **FAIL** | same |
| **actual** `assertNotIn('engineering/decisions.md', prefix)` | **FAIL** | path still present |
| **actual** `assertNotIn('engineering/mistakes.md', prefix)` | **FAIL** | path still present |

The phrase lock is the whole verb + bare filename. `engineering/decisions.md` does **not** contain the contiguous string `log it in decisions.md`. The `assertNotIn` is a second independent tripwire: a prefix that names both sinks still fails.

They did not replace the old `assertIn('engineering/decisions.md')` with a weaker `assertIn('decisions.md')`. That is the exact trap `task_analyst` and this review brief named.

---

## Would the tests fail on the pre-move tree?

Pre-move facts (analysis reports + d55ce4 evidence, before this write):

- no root `decisions.md` / `mistakes.md`
- `engineering/decisions.md` was the live log (~13 `##` entries, implementation red said **55 lines**)
- `engineering/mistakes.md` was the live log (3 `##` entries, dated `## 2026-…`)
- `AGENTS.md` first section named `engineering/decisions.md` / `engineering/mistakes.md`
- first heading was already `## Agent self-learning`

| Test | Pre-move outcome | First failing assert |
| --- | --- | --- |
| `test_agents_md_starts_with_self_learning` | **FAIL** | `(ROOT / 'decisions.md').is_file()` → `False is not true : decisions.md` |
| same, if root files had existed and only `AGENTS.md` still pointed at `engineering/` | **FAIL** | `assertIn('log it in decisions.md')` then `assertNotIn('engineering/decisions.md')` |
| `test_engineering_self_learning_stubs_are_pointers` | **FAIL** | `55 not less than or equal to 5 : engineering/decisions.md`; also `## 20` dated headings; also missing `Canonical log is /` / `Do not append here` |
| first-heading assert alone | stay-green | already true on pre-move; kept as a stay-put lock, not the move detector |

`evidence/implementation.md` claimed exactly those two red messages, then `python3 -m unittest tests.test_structure -q` → `Ran 15 tests` / `OK`. There are **15** `def test_` methods in `tests/test_structure.py` now (14 previous + sibling). The claimed red text is the first assertion of each new/extended method. I did not re-execute the red run (tree is already moved); the claim is consistent with the asserts and the pre-move tree.

---

## Failure matrix (regression after the move)

| Regression | Fail? | Why |
| --- | --- | --- |
| Root `decisions.md` deleted | **Yes** | `is_file()` at `:23` |
| Root `mistakes.md` deleted | **Yes** | `is_file()` at `:24` |
| Root files are empty stubs | **Yes** | header phrases in first 400 chars missing |
| `AGENTS.md` still / again says `engineering/decisions.md` | **Yes** | `assertIn('log it in decisions.md')` and `assertNotIn('engineering/…')` |
| Prefix contains both root phrase and `engineering/` path | **Yes** | `assertNotIn` |
| First `##` no longer `Agent self-learning` | **Yes** | exact equality `:32` |
| Section moved after `## Mandatory entrypoint` | **Yes** | `headings[0]` + prefix wording leave `prefix` |
| `engineering/` still a full second log (copy, not move) | **Yes** | line count > 5 and/or `## 20` headings |
| Stub loses pointer / “Do not append here” | **Yes** | exact dest `Canonical log is /decisions.md` (or `/mistakes.md`) |
| Dated entry appended under `engineering/` | **Yes** | `## 20` or >5 lines |
| Heading renamed (`## Self-learning`, `###`) | **Yes** | exact `## Agent self-learning` |
| User wording dropped (`worth the effort`, 3 sentences, root cause) | **Yes** | leftover d55ce4 phrase locks kept |

---

## Test plan / requirements vs implementation

| Required lock | Covered? |
| --- | --- |
| `(ROOT / 'decisions.md').is_file()` and same for `mistakes.md` | Yes (`:23-24`). Not added to `test_required_files_exist`; adjacent assert is what `test-plan.md` allowed. |
| `log it in decisions.md` / `record it in mistakes.md` before `## Mandatory entrypoint` | Yes (`:36-37`) |
| Fail if live bullets still say `engineering/decisions.md` / `engineering/mistakes.md` | Yes (`:38-39`) |
| Existing heading-order assert stays | Yes (`:32`) |
| `engineering/` files are pointers, not a second log | Yes (sibling `:44-60`) |
| Red on current (pre-move) tree, green after | Claimed and consistent |

`requirements.md` row “structure test fails if either root file is missing or if `AGENTS.md` still names `engineering/…` as the live sinks” is the pair of methods above.

---

## Surrounding suite

No other `tests/*.py` still asserts `engineering/decisions.md` as a live `AGENTS.md` sink. The old d55ce4 `assertIn('engineering/decisions.md', prefix)` was replaced, not left as a contradictory green.

`test_required_files_exist`, version `2.0.8`, no-GHA, no-packaging-marker, README MIT, hooks, agents, skills, and changelog-2.0.6 tests were not weakened.

`tests/_support.py` `project_copy` still does not seed root `decisions.md` / `mistakes.md`. Structure tests run against `ROOT`, so they do not need the fixture. Installer seed remains out of scope.

Discover count on the official receipt is **183** tests (182 + the new sibling). Matches the method add.

---

## Verification evidence (did not re-run)

Path: `.grok-stack/runtime/receipts/ba1615416da5/verification.json`

| Field | Value |
| --- | --- |
| `kind` / `mode` | `verification` / `pr` |
| `status` | **fail** |
| `profiles` | `base` |
| `route_id` | `ba1615416da5` |
| `tree_fingerprint` | `a615fd6003a13f67c927e991252cdf7bb131c440139b57c3072abf6bd3a2d11a` |
| `last-fingerprint.json` | same digest at review time |
| `python-unittest` | **fail**, `Ran 183 tests in 40.124s` / `FAILED (errors=1)` |
| failing test | `RouterTests.test_bug_with_regression_test_keeps_bugfix_intent` |
| fail reason | `project_copy` `shutil.copytree` of `.grok-stack/runtime/.last-fingerprint.json.f2cv7ei8` → `ENOENT` |
| `ruff` / `bandit` / `coverage` | pass; TOTAL **76%** |
| `git-diff-check` / `secret-scan` / contracts / sql | pass |

That error is a concurrent temp-file race while copying `.grok-stack/runtime` (`tests/_support.py:19-23`). It is not an assertion in `test_structure.py`. Focused structure run claimed by implementation (`Ran 15 tests` / `OK`) is consistent with 15 methods and with this review’s static read.

`changed_files` on that receipt include the product delta inspected here: `AGENTS.md`, `decisions.md`, `mistakes.md`, `engineering/decisions.md`, `engineering/mistakes.md`, `tests/test_structure.py`.

Writing this report will stale that fingerprint. Controller rebinds after reviews. Do not treat the current verification receipt as a pass receipt.

---

## Gaps (not fail)

- Tests do not snapshot the 16 pre-move `##` headings as a lasting list. That is a one-time move check (`git mv` + header phrases). A later delete of an old entry would not fail these two methods. Acceptable: the regression this change must lock is “sinks leave the root / `engineering/` becomes a second log.”
- `# Decisions` / `# Mistakes` titles are not asserted; the distinctive header sentences are.
- Markdown `- ` bullets are not asserted. Paragraph form with the same phrases would pass.
- `assertNotIn('engineering/…')` applies only to the prefix before `## Mandatory entrypoint`, which is what `test-plan.md` asked for. A contradictory later section would not trip it.
- A 5-line `engineering/` file without `## 20` headings could theoretically be a tiny second log. Combined with the pointer phrases, that is enough.
- `CHANGELOG.md` §2.0.8 still names `engineering/` (implementation residual). No new structure assert for that. Out of this review’s four locks.
- Official verify is not green. Re-run is a controller/write-owner step, not a missing `StructureTests` case.

None of these would let the pre-move tree (missing root files, `AGENTS.md` pointing at `engineering/`, live log still under `engineering/`) go green.

---

## Blocking findings

None for test adequacy.

---

## Verdict (repeat)

**PASS.** `tests/test_structure.py` locks root-file existence, exact root filenames in the `AGENTS.md` prefix (and forbids `engineering/` as the live sink), short `engineering/` stubs, and first heading `## Agent self-learning`. It is not a bare `assertIn('decisions.md')`. It would fail on the pre-move tree at `is_file()` and at the stub line-count, and the wording asserts would also fail if only `AGENTS.md` were still on `engineering/`. Do not return this to `general_implementer` for structure-test gaps. Re-run `grok_verify --mode pr` before recording a pass verification receipt; the current official run failed on an unrelated `project_copy` race.
