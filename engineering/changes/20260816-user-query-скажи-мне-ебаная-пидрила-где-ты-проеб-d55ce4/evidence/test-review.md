# Test review — restore AGENTS.md self-learning as first section

Change: `20260816-user-query-скажи-мне-ебаная-пидрила-где-ты-проеб-d55ce4`  
Route: `70e08d7b09b5` (active rematch; original `d55ce4cd4015`)  
Reviewer: `test_reviewer` (read-only) · write owner: `general_implementer`  
Reviewed: 2026-08-16  
Did **not** re-run unittest / `grok_verify` (would dirty receipts). Inspected `tests/test_structure.py`, `AGENTS.md` lines 1–20, `test-plan.md`, `evidence/implementation.md`, `evidence/code-review.md`, and the official verification receipt.

**PASS.**

The new structure test actually locks the self-learning instruction as the first `AGENTS.md` section. It is not an existence check. It would fail if the section is missing, moved after `## Mandatory entrypoint`, or if either path or the required wording is dropped. Red-then-green is claimed and is consistent with the test plus the pre-change first heading.

Do not return this to `general_implementer` for test gaps.

---

## Verdict

| Gate | Result |
| --- | --- |
| Product-test adequacy for this delta | **PASS.** `test_agents_md_starts_with_self_learning` covers every `test-plan.md` row. |
| Characterization coverage | **PASS.** Red assertion matches the pre-restore first heading (`## Mandatory entrypoint`). |
| Verification evidence | **PASS.** Official `python-unittest` is `Ran 182 tests in 39.320s` / `OK` on fingerprint `e6b6455c…`. |
| False confidence | **None.** File-exists is a different test. This one asserts heading order + prefix wording. |

Would I block? **No.**

---

## What the new test locks

```22:36:tests/test_structure.py
    def test_agents_md_starts_with_self_learning(self) -> None:
        text = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        headings = [line for line in text.splitlines() if line.startswith('## ')]
        self.assertTrue(headings, 'AGENTS.md has no ## headings')
        self.assertEqual(headings[0], '## Agent self-learning')
        entrypoint = text.find('## Mandatory entrypoint')
        self.assertGreaterEqual(entrypoint, 0, 'missing ## Mandatory entrypoint')
        prefix = text[:entrypoint]
        self.assertIn('engineering/decisions.md', prefix)
        self.assertIn('engineering/mistakes.md', prefix)
        self.assertIn('log it in', prefix)
        self.assertIn('record it in', prefix)
        self.assertIn('worth the effort', prefix)
        self.assertIn('no more than 3 sentences', prefix)
        self.assertIn('root cause (not the symptom)', prefix)
```

Current product text that those asserts hit:

```3:10:AGENTS.md
## Agent self-learning

- If you make a decision that turns out to be correct and worth the effort, log it in engineering/decisions.md (pattern + why it worked, no more than 3 sentences).
- If you make a mistake that leads to a problem, identify the root cause (not the symptom) and record it in engineering/mistakes.md.

This repository uses an adaptive, task-routed Grok Build workflow. The `UserPromptSubmit` hook classifies development tasks and writes `.grok-stack/runtime/active-route.json`. That route is the authority for which skills, agents, quality profiles, human gates, and evidence are required.

## Mandatory entrypoint
```

### Failure matrix (would this test fail?)

| Regression | Fail? | Why |
| --- | --- | --- |
| Section deleted | **Yes** | `headings[0]` becomes `## Mandatory entrypoint`; also prefix `assertIn`s fail |
| Section moved after `## Mandatory entrypoint` | **Yes** | first `##` is no longer self-learning; paths/verbs leave `prefix` |
| Heading renamed (`## Self-learning`, `###`, `#`) | **Yes** | exact `## Agent self-learning` required at `headings[0]` |
| `engineering/decisions.md` dropped | **Yes** | `assertIn` at `tests/test_structure.py:30` |
| `engineering/mistakes.md` dropped | **Yes** | `assertIn` at `tests/test_structure.py:31` |
| `log it in` / `record it in` dropped | **Yes** | `tests/test_structure.py:32-33` |
| `worth the effort` dropped | **Yes** | `tests/test_structure.py:34` |
| `no more than 3 sentences` dropped | **Yes** | `tests/test_structure.py:35` |
| `root cause (not the symptom)` dropped | **Yes** | `tests/test_structure.py:36` |
| File deleted | **Yes** | `read_text` raises; existence is also locked by `test_required_files_exist` |
| File exists but empty / no `##` | **Yes** | `self.assertTrue(headings, …)` |
| Dummy first heading with no bullets | **Yes** | heading may pass; prefix wording/paths fail |
| Only `test_required_files_exist` remaining | n/a | that test **cannot** catch this regression (existence only) |

This is not “assert the file exists.” That weaker check is `test_required_files_exist` at `tests/test_structure.py:14-20`. The new method is the content lock `requirements.md` asked for: fail if either bullet/path is missing.

---

## Red-then-green

`evidence/implementation.md` claims:

1. Red: `python3 -m unittest tests.test_structure.StructureTests.test_agents_md_starts_with_self_learning`  
   `AssertionError: '## Mandatory entrypoint' != '## Agent self-learning'`
2. Green: `python3 -m unittest tests.test_structure` → `Ran 14 tests in 0.009s` / `OK`

That red message is exactly `assertEqual(headings[0], '## Agent self-learning')` against the committed pre-restore first heading. Code review independently recorded base `02376cc` as H1 then intro then `## Mandatory entrypoint`. I did not re-execute the red run (tree is already restored); the claim is consistent with the assertion and the pre-change heading order.

Green count 14 matches `StructureTests` method count after the add (13 previous + this one). Official discover is 182 (`181 + 1`), which matches the same increment.

---

## Existing structure tests still make sense

None of the other `StructureTests` methods were edited. They still police independent product invariants:

| Test | Still adequate? |
| --- | --- |
| `test_required_files_exist` | Yes. Existence of `AGENTS.md` plus other shipped files. Complements, does not replace, the new content lock. |
| `test_readme_is_free_mit_commercial_product` | Yes. Unrelated positioning lock. |
| `test_grok_config_is_valid_toml` / hook tests / agent contract / skill frontmatter / quality profiles | Yes. Unchanged. |
| `test_product_tree_has_no_packaging_markers` | Yes. Still forbids `pyproject.toml` / `requirements.txt` / `setup.py`. |
| `test_version_is_2_0_7_and_github_actions_are_absent` | Yes. Identity + no GHA still in force. |
| `test_changelog_2_0_6_does_not_claim_stale_latest` | Yes. Unrelated leftover-sentence lock. |
| `test_package_version_matches_version_file` | Yes. `__version__` == `VERSION`. |

No surrounding test was weakened to let the restore pass. No new test reintroduces GHA, Dependabot, or packaging markers.

---

## Test plan vs implementation

| `test-plan.md` row | Covered? |
| --- | --- |
| New `test_agents_md_starts_with_self_learning` in `tests/test_structure.py` | Yes (`:22`) |
| First `##` heading is the self-learning section | Yes (`:26`) |
| Both `engineering/` paths appear before `## Mandatory entrypoint` | Yes (`:27-31`) |
| Two verbs + worth-the-effort / ≤3 sentences / root-cause wording | Yes (`:32-36`) |
| Existing structure tests still pass | Claimed 14/14; official verify 182 OK |

`architecture.md` asked to lock both paths and both verbs (`log it in`, `record it in`) before `## Mandatory entrypoint`. The test does that and also pins the first heading plus the user phrases.

---

## Verification evidence (did not re-run)

Path: `.grok-stack/runtime/receipts/70e08d7b09b5/verification.json`

| Field | Value |
| --- | --- |
| `kind` / `mode` | `verification` / `pr` |
| `status` | `pass` |
| `profiles` | `base` |
| `route_id` | `70e08d7b09b5` |
| `tree_fingerprint` | `e6b6455c8cd22e49f19d2103a1da52f0dd57dbd02225be4a06fa94844a3ac46d` |
| `last-fingerprint.json` | same digest — receipt current as of this review |
| `python-unittest` | `status=pass`, `Ran 182 tests in 39.320s` / `OK` |
| `ruff` / `bandit` / `coverage` | pass; TOTAL **76%** (fail-under 74) |
| `git-diff-check` / `secret-scan` / contracts / sql | pass |

`changed_files` on that receipt include the product delta this review inspected: `AGENTS.md`, `tests/test_structure.py`, `engineering/mistakes.md`, plus the change-package files.

Writing this report will stale that fingerprint. Controller rebinds after reviews.

---

## Gaps (not fail)

- The test locks the first `##` heading and prefix content, not “byte-immediately after H1 with no intervening paragraph.” `test-plan.md` asked for the heading-order lock. An extra paragraph between H1 and `## Agent self-learning` would still pass. Residual only.
- Phrases are required anywhere before `## Mandatory entrypoint`, not strictly inside the two bullets. Combined with `headings[0] == '## Agent self-learning'`, that is enough to stop a rewrite that drops or postpones the rule.
- Markdown `- ` bullet markers are not asserted. Paragraph form with the same phrases would pass. `requirements.md` cares about bullets/paths being present, not list syntax.
- The test does not assert that `engineering/decisions.md` / `engineering/mistakes.md` exist as files. Those sinks already exist; installer seed is out of scope.
- Skills (`adaptive-delivery`) are not string-tested for the loop. Brief out of scope; contract lock is `AGENTS.md` + this test.

None of these would let the omitted-first-section regression return unnoticed.

---

## Blocking findings

None.

---

## Verdict (repeat)

**PASS.** `tests/test_structure.py:22-36` locks first-heading placement, both `engineering/` sinks, and the user wording before `## Mandatory entrypoint`. Red-then-green is claimed as first heading `== Mandatory entrypoint` and is consistent with the assertion. Existing structure tests remain coherent. Official verify is 182 OK. Do not return this to `general_implementer` for test gaps.
