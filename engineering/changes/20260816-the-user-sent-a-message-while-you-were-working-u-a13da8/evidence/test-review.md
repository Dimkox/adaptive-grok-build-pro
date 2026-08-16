# Test review — `a13da8f96b5a`

Change: `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-a13da8`  
Reviewer: `test_reviewer` (read-only). Write owner: `general_implementer`.  
Scope: `tests/test_structure.py` methods `test_readme_names_root_self_learning_logs` and `test_readme_stack_graph_is_complete` against the current `README.md` mermaid and the pre-change K7 baseline recorded in this package’s analysis reports.  
Suite was **not** re-run here (would dirty receipts / coverage artifacts / fingerprint temp files). Independent file review of the two new methods, the README they lock, and the official verification receipt.

**PASS.**

The two new tests fail on the old K7 README. The graph lock is not a node-existence check: it requires the unique undirected `---` pair set to equal `itertools.combinations` of the ten ids (45 edges). A star, a path, K7-plus-pendants, or any missing pair fails. Do not return this to `general_implementer` for test gaps.

| ID | Required case | Test | Result |
| --- | --- | --- | --- |
| P0 | Old K7 README (zero `decisions.md` / `mistakes.md` hits, no `Contract`) is red | both new methods | Covered |
| P0 | README names `decisions.md`, `mistakes.md`, and self-learning wording | `test_readme_names_root_self_learning_logs` | Covered |
| P0 | First mermaid fence is exactly the 10 required ids | `test_readme_stack_graph_is_complete` | Covered |
| P0 | 45 unique undirected `---` edges and pair set == `combinations(required, 2)` | `test_readme_stack_graph_is_complete` | Covered |
| P0 | Node-existence alone is not enough (star / K7+pendants / missing pair fail) | same; `edges == expected` | Covered |
| P0 | Existing self-learning / stub / MIT / 2.0.8 tests not weakened | surrounding `StructureTests` | Covered |

---

## Verdict

| Gate | Result |
| --- | --- |
| Product-test adequacy for this delta | **PASS.** Both new methods lock the test-plan rows. Graph completeness is pair-set equality, not “ids appear” or “at least N edges.” |
| Characterization coverage | **PASS.** K7 fail modes match `evidence/implementation.md` and the pre-edit analysis (repo_explorer / task_analyst / docs_researcher). Residual surface locks are noted below and are not fail. |
| Verification evidence | **Noted, not a test-design fail.** Official `python3 scripts/grok_verify.py --mode pr` on fingerprint `4498f1af…` is **185 tests, 1 ERROR** in unrelated `test_policy.PolicyTests.test_blocks_second_different_write_agent` (`project_copy` race on a transient `.last-fingerprint.json.*`). The two new structure tests are not in that traceback. Focused `tests.test_structure` was recorded green (17 tests) after the README edit. |

---

## 1. Assigned bar

The review question is whether these two tests:

1. fail on the **old K7** README, and
2. pass **only** if every unordered pair of the 10 nodes is linked.

A mere `assertIn(node_id, mermaid)` loop is not enough.

---

## 2. `test_readme_names_root_self_learning_logs`

```64:71:tests/test_structure.py
    def test_readme_names_root_self_learning_logs(self) -> None:
        text = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertIn('decisions.md', text)
        self.assertIn('mistakes.md', text)
        self.assertTrue(
            'self-learning' in text or 'Agent self-learning' in text,
            'README must name self-learning or Agent self-learning',
        )
```

### K7 fail

Pre-edit tree (this package’s analysis, written while README was still K7):

- `analysis-repo_explorer.md`: README has **zero** hits for `decisions.md` / `mistakes.md`.
- `analysis-docs_researcher.md` / `analysis-task_analyst.md`: same; `AGENTS.md` is prose-only and not a mermaid node.

`assertIn('decisions.md', text)` is therefore red on that README. Implementation recorded `AssertionError: 'decisions.md' not found`. That is the correct first-fail for the names lock.

### What it does **not** need to prove

This method is the name lock, not the pair lock. Pair completeness is the sibling test.

---

## 3. `test_readme_stack_graph_is_complete`

Required ids: `Route`, `Skills`, `Agents`, `Hooks`, `Policy`, `Verify`, `Packages`, `Contract`, `Decisions`, `Mistakes`.

The method:

1. Takes the **first** ` ```mermaid ` fence only.
2. Early-fails if any required id is missing as a substring (`Contract` is absent from K7).
3. Strips mermaid `\[[^\]]*\]` labels so `Contract["AGENTS.md"]` is the id `Contract`.
4. Collects standalone id declarations and `A --- B` endpoints.
5. Asserts `nodes == set(required)` (exactly 10, no extras).
6. Asserts `len(edges) == 45`.
7. Asserts `edges == {frozenset(p) for p in combinations(required, 2)}`.

`C(10,2) = 45` is re-checked in the test (`self.assertEqual(len(expected), 45)`).

### K7 fail

Old mermaid was K7: those seven runtime ids, 21 `---` edges, no `Contract` / `Decisions` / `Mistakes`. Implementation recorded `AssertionError: 'Contract' not found` on the early `assertIn`. Even without that early check, `nodes` would be 7 and `len(edges)` would be 21, so both the node-set and pair-set asserts fail. Caption-only “complete graph” does not pass.

### Not a node-existence check

The early `assertIn(node_id, mermaid)` loop is only an early fail. The load-bearing lock is the pair set.

| Regression | What the test does |
| --- | --- |
| Ten ids declared, no new edges (K7 + 3 pendants-as-decls) | `nodes` can reach 10; `len(edges)` stays 21 → fail |
| Star (hub + 9 spokes) | 9 unique edges ≠ 45; pair set ≠ `combinations` → fail |
| K7 + three `Route --- {Contract,Decisions,Mistakes}` pendants | 24 edges → fail |
| K7 ∪ K3 among the new nodes, no cross edges | 21+3 = 24 → fail |
| 44 pairs (one missing, e.g. `Policy --- Mistakes`) | count and set equality fail |
| 45 edges on the wrong vertex set | `nodes != set(required)` and/or `edges != expected` |
| Directed `-->` / `===` counted as links | parser only accepts `\w+ --- \w+`; those lines are dropped → fail |
| Duplicate / reversed `A --- B` used to pad a hole | `frozenset` dedupes; unique count drops below 45 → fail |

`combinations` is computed, not a hard-coded list of 45 literal strings. A sloppy paste that omits `Policy --- Mistakes` cannot hide behind a matching line count of some other 45 pairs on these exact 10 vertices (there is only one such set).

### Independent read of the product mermaid

Current `README.md` first fence (`graph TD`, lines 17–67):

- Three labeled decls: `Contract["AGENTS.md"]`, `Decisions["decisions.md"]`, `Mistakes["mistakes.md"]`.
- 45 unique `A --- B` lines (grep). Degree sequence is the triangle 9+8+7+6+5+4+3+2+1. Every unordered pair among the ten ids is present, including `Contract --- Decisions`, `Contract --- Mistakes`, `Decisions --- Mistakes`, and all 21 cross edges from each new node to the original seven.
- Parser shape matches the file: two-space indent, `---` with spaces, labels only on the three decls. After label strip, decls become bare ids; every edge is a fullmatch.

The current README is the unique K10 the test accepts.

---

## 4. Surrounding suite (not weakened)

Unchanged and still the ba1615 / product locks:

- `test_agents_md_starts_with_self_learning` — root logs exist; AGENTS prefix names them; forbids `engineering/` as the live sink.
- `test_engineering_self_learning_stubs_are_pointers`
- `test_readme_is_free_mit_commercial_product` — not mixed with the new name/graph contract.
- `test_version_is_2_0_8_and_github_actions_are_absent`
- `test_package_version_matches_version_file`

No `pyproject.toml` / `requirements.txt` / `setup.py` were added to light the tests.

---

## 5. Gaps (not fail)

These are weaker than the architect / task_analyst wish-list and are **not** required to meet the assigned bar or `test-plan.md`.

| Gap | Why not fail |
| --- | --- |
| Names test is whole-file `assertIn('decisions.md')`; does not slice What-this-is vs the copy list | Test-plan row is “README contains” those names. Current README has them in What-this-is (line 11), the node table (78–80), and the copy list (120–121). Pair completeness is the sibling test. |
| Names test does not `assertNotIn('engineering/decisions.md')` | `engineering/decisions.md` contains the substring `decisions.md`, so a README that only named the old sink would pass this method **alone**. The old K7 named **neither** path (zero hits), so the K7-red requirement still holds. Live-sink forbid remains in `test_agents_md_starts_with_self_learning`. |
| Graph test does not assert the three display labels or raw `---` line count == 45 | Labels are present; unique-set equality already implies completeness. Raw-count is a duplicate-line hygiene check, not a completeness check. |
| Graph test does not explicitly forbid `-->` | Those tokens are not parsed as edges, so a directed-only diagram fails the 45-pair assert. |

---

## 6. Verification evidence (did not re-run)

Receipt: `.grok-stack/runtime/receipts/a13da8f96b5a/verification.json`  
Fingerprint: `4498f1af93563603d4d721dae7f2c3c560c3201186a7a97fd4fb7e76dd4cd7d3` (matches `last-fingerprint.json`)  
Mode: `pr` · profiles: `base` · **status: fail**

| Check | Status |
| --- | --- |
| git-diff-check | pass |
| secret-scan | pass |
| ruff | pass |
| bandit | pass |
| python-unittest | **fail** — 185 ran, 1 ERROR |
| coverage report | pass (75%) |

The unittest error is `shutil.Error` inside `tests/_support.py` `project_copy` while `test_blocks_second_different_write_agent` copied a vanished `.grok-stack/runtime/.last-fingerprint.json.t4d__gz9`. That is a concurrent fingerprint-temp race, not a README/graph assertion. The two new structure tests do not use `project_copy`.

Implementation red/green (not re-run here):

- K7 README: both new methods red as cited above.
- After README edit: `python3 -m unittest tests.test_structure -q` → `Ran 17 tests in 0.010s` / `OK`.

Test count 181 → 185 is consistent with this tree adding the two new README locks plus the two ba1615 self-learning / stub methods that landed in the same ship set.

Controller still needs a **green** `grok_verify --mode pr` on a quiet tree before review receipts are bound. That is a verify-flake / sequencing issue, not a missing characterization of K10.

---

## Verdict (repeat)

**PASS.**

`test_readme_names_root_self_learning_logs` is red on the old K7 README (`decisions.md` absent).  
`test_readme_stack_graph_is_complete` is red on that same K7 (`Contract` absent; 7 nodes / 21 edges).  
It passes only when the first mermaid fence’s unique undirected `---` pairs equal all 45 combinations of the ten required ids. Node-existence, a star, K7-plus-pendants, or a missing pair is not enough.
