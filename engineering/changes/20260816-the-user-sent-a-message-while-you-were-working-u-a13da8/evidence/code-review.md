# Code review — README K10 complete graph + root agent logs

Change: `20260816-the-user-sent-a-message-while-you-were-working-u-a13da8`  
Route: `a13da8f96b5a` · reviewer: `code_reviewer` (read-only) · write owner: `general_implementer`  
Reviewed: 2026-08-16  
Commit: `7152b75b610bada0ecc7468752900ab1515324f1` (`Document root agent logs and complete K10 stack graph in README`)  
Base: `22762a77ea4133cc34398f9a70194daa427bd096` (`origin/main`, `Release v2.0.8`)

**PASS.** I would not block.

HEAD is `7152b75`. `origin/main` is still `22762a7`. The product tree at HEAD meets every named acceptance item: README mermaid is \(K_{10}\) with 45 unique undirected `---` pairs including Contract / Decisions / Mistakes; README names `decisions.md`, `mistakes.md`, and self-learning; root logs exist; `AGENTS.md` first section uses those names; `VERSION` is `2.0.8`; no GitHub Actions; no `pyproject.toml`.

---

## Verdict against acceptance

| # | Criterion | Result |
| --- | --- | --- |
| 1 | README mermaid is K10 complete (45 undirected `---` edges) including Contract / Decisions / Mistakes | **PASS** |
| 2 | README names `decisions.md`, `mistakes.md`, self-learning | **PASS** |
| 3 | Root `decisions.md` / `mistakes.md` exist; `AGENTS.md` first section uses those names | **PASS** |
| 4 | `VERSION` 2.0.8 | **PASS** |
| 5 | No GitHub Actions | **PASS** |
| 6 | No `pyproject.toml` | **PASS** |
| 7 | No leftover dirt in the commit | **PASS** (product/identity/CI files clean; leftover sibling packages remain uncommitted working-tree dirt — do not `git add -A` on push) |

Would I block? **No.**

---

## What was actually inspected

Did not trust `evidence/implementation.md` alone. Compared the live tree at `7152b75` to GitHub raw of `22762a77` plus this change package (`brief.md`, `requirements.md`, `architecture.md`, `test-plan.md`, `tasks.md`, `release.md`, `rollback.md`, analysis reports). This session has no shell, so there is no live `git show --name-only` / `unittest` / `ruff`. Equivalents below.

```text
# refs
.git/HEAD                     → ref: refs/heads/main
.git/refs/heads/main          → 7152b75b610bada0ecc7468752900ab1515324f1
.git/refs/remotes/origin/main → 22762a77ea4133cc34398f9a70194daa427bd096
.git/COMMIT_EDITMSG           → Document root agent logs and complete K10 stack graph in README

# contracts
engineering/changes/…-a13da8/{brief,requirements,architecture,test-plan,tasks,release,rollback}.md
engineering/changes/…-a13da8/evidence/{analysis-*,implementation}.md

# product vs 22762a77 (GitHub raw + working tree at HEAD)
README.md                     K7 (21 ---) → K10 (45 ---) + names + copy-list lines
tests/test_structure.py       +test_readme_names_root_self_learning_logs
                              +test_readme_stack_graph_is_complete
decisions.md                  NEW at root (ba1615 move + K10 decision)
mistakes.md                   NEW at root (ba1615 move)
engineering/decisions.md      full log → 3-line pointer
engineering/mistakes.md       full log → 3-line pointer
AGENTS.md                     first-section bullets drop engineering/ prefix

# unchanged on purpose
VERSION                       2.0.8
.grok-stack/adaptive_grok/__init__.py  __version__ = "2.0.8"
CHANGELOG.md                  not in the verify changed-file set
scripts/install_into.py       not in the verify changed-file set
QUICKSTART.md                 no mermaid

# absences
pyproject.toml / requirements.txt / setup.py   do not exist
.github/                                       directory missing
.github/dependabot.yml                         missing
.grok-stack/templates/ci/github-actions.yml    missing
```

`grok_verify --mode pr` receipt at `.grok-stack/runtime/receipts/a13da8f96b5a/verification.json` (fingerprint `4498f1af…`, after the commit) was used only as a changed-file *union* (`base...HEAD` plus unstaged plus untracked). It is not a `git show` of `7152b75`.

---

## Diff reviewed

### README mermaid is \(K_{10}\)

Origin `22762a77` fence is K7 only (`Route` … `Packages`, 21 `---` lines). Current first (and only) fence:

- `graph TD`
- labeled nodes `Contract["AGENTS.md"]`, `Decisions["decisions.md"]`, `Mistakes["mistakes.md"]`
- 45 `---` lines, lines 22–66
- no `-->` / `===` / self-loops
- caption kept verbatim: `Simple complete graph: every core piece is linked to every other.`

Independent pair check against  
`{Route, Skills, Agents, Hooks, Policy, Verify, Packages, Contract, Decisions, Mistakes}`:

| From | Degree-to-later nodes |
| --- | --- |
| Route | 9 (Skills…Mistakes) |
| Skills | 8 |
| Agents | 7 |
| Hooks | 6 |
| Policy | 5 |
| Verify | 4 |
| Packages | 3 |
| Contract | 2 |
| Decisions | 1 |
| **Total** | **45 = C(10,2)** |

Not a star, path, or K7-plus-pendants. Cross edges such as `Policy --- Mistakes`, `Packages --- Contract`, and `Contract --- Decisions` are present.

Node table lists `AGENTS.md`, `decisions.md`, `mistakes.md`. One mermaid in README. `QUICKSTART.md` has none.

### README names the root logs

`## What this is` last bullet:

```markdown
- `AGENTS.md` starts with the self-learning rule and writes to `decisions.md` / `mistakes.md`
```

Manual copy list (next to `AGENTS.md`):

```text
decisions.md      → project decisions.md
mistakes.md       → project mistakes.md
```

Zero hits for `engineering/decisions.md` / `engineering/mistakes.md` in README. MIT / commercial / free / public / no-EULA copy is unchanged.

Architect asked for the exact sentence “Agent self-learning is the first rule…”. The shipped bullet says “starts with the self-learning rule” instead. User acceptance only requires the names `decisions.md`, `mistakes.md`, and self-learning. That is met. Not a block.

### Root logs + AGENTS.md first section

- Root `decisions.md` / `mistakes.md` exist. Prior dated bodies from origin `engineering/` are still there; new 2026-08-16 entries are prepended (move + K10).
- `engineering/` copies are three-line stubs (“Canonical log is /…”, “Do not append here”). No `## 20*` entries.
- `AGENTS.md` first `##` is still `## Agent self-learning`. Prefix before `## Mandatory entrypoint` has `log it in decisions.md` and `record it in mistakes.md`. Origin `22762a77` still said `engineering/decisions.md` / `engineering/mistakes.md`.

### VERSION / GHA / pyproject

- `VERSION` file is `2.0.8`. README H1 is `v2.0.8`. `__version__` is `"2.0.8"`.
- `.github/` does not exist. No Dependabot. No CI template.
- No root `pyproject.toml` / `requirements.txt` / `setup.py`.
- None of `VERSION`, `CHANGELOG.md`, `packages/*`, `dist/*`, `install_into.py`, or `.github/**` appear in the verify changed-file set.

### Leftover dirt in the commit

Forbidden identity/CI/packaging files are absent from the delta. That part is clean.

The post-commit verify `changed_files` list also contains sibling packages that are **not** on `22762a77` (`04ae05`, `0f3d94`, `39b13f`, `d55ce4`, `b625b4`, `864726`, ad4090 `*-merge.md`, plus dirty state/review files under already-published packages). `changed_files()` is the union of `git diff 22762a77...HEAD` **and** unstaged **and** `git ls-files --others`, so that list is not proof those paths are in `7152b75`.

Independent signals they are **not** in the commit:

- Commit subject is the README/K10 change only.
- Write-owner ship set (and architect sequence) is README + structure tests + ba1615 product move + `a13da8`/`ba1615` packages. Implementation states leftover packages were not staged.
- Including whole 2.0.6 leftover packages (`39b13f`, `864726`, `b625b4`, …) would contradict that ship set.
- `2a31f5` (newer change package, now `active-change.json`) is not in the 22:38 verify list; it is post-commit working-tree dirt.

Residual for the controller: the working tree is still dirty with those leftovers. Push must stay path-limited. `git add -A` would fail this criterion.

### Tests that lock the product

`tests/test_structure.py`:

- `test_readme_names_root_self_learning_logs` — whole-file `decisions.md` / `mistakes.md` / self-learning.
- `test_readme_stack_graph_is_complete` — first mermaid fence; exactly the 10 ids; unique undirected `---` set equals `combinations(..., 2)` (45). A star or K7 regression fails.
- Existing self-learning, stub-pointer, MIT, no-packaging-marker, and `2.0.8`/no-GHA tests are still present.

Weaker than the architect method (`test_readme_stack_graph_is_k10_complete`): no explicit assert of `Contract["AGENTS.md"]` label strings, no raw-`---` count vs unique count, no What-this-is / copy-list block isolation, no “do not name `engineering/…` as live sinks”. The **product** still has those properties. Test gaps belong to `test_reviewer`; they do not fail this code review.

---

## Out of scope (confirmed not done)

- VERSION bump, zip rebuild, tag, GitHub Release
- `install_into` `MANAGED_FILES` (manual copy list only, by design)
- QUICKSTART mermaid duplicate
- New services, GHA, `pyproject.toml`

---

## Residual risk

- `origin/main` is still `22762a7` until the controller pushes. This reviewer does not push.
- Working-tree leftovers (`04ae05`, `0f3d94`, `39b13f`, `d55ce4`, ad4090 merge files, `2a31f5`, …) must stay unstaged.
- `install_into` still does not seed consumer `decisions.md` / `mistakes.md`. README copy list is the manual recipe.
- Published `CHANGELOG.md` §2.0.8 still describes `engineering/` as the 2.0.8 ship path. Left as the ship record.
- Post-commit `grok_verify --mode pr` receipt is `fail` on a `shutil.copytree` race (`runtime/.last-fingerprint.json.t4d__gz9` vanished mid-copy). That is not a defect in this README/graph change; structure tests themselves are not implicated.

Rollback if not pushed: `git reset --keep origin/main`. If already on `origin/main`: forward-fix, no force-push.
