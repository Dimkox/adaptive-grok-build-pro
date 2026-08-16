# Analysis — architect

Change: `20260816-the-user-sent-a-message-while-you-were-working-u-a13da8`  
Route: `a13da8f96b5a` · write owner: `general_implementer` · reviews: `code_reviewer` + `test_reviewer`  
Question: expand README mermaid from K7 (Route Skills Agents Hooks Policy Verify Packages) to a complete graph that also includes Contract/AGENTS.md, Decisions/decisions.md, Mistakes/mistakes.md. Every pair must have an undirected `---` edge (`C(10,2)=45`). Structure test must count nodes+edges and require every pair. Then push. No VERSION bump.

Read-only. No application-code edits. No `.env`. No push / merge / deploy (push is last-mile for the write owner after receipts).

Facts from this package, sibling `evidence/analysis-repo_explorer.md`, ba1615 / 04ae05 leftovers, and the live tree at `HEAD` `22762a77` (v2.0.8).

---

## Ruling

**Expand the existing `graph TD` mermaid in place to K10.** Keep `graph TD` and undirected `---`. Add three labeled nodes. Emit every unordered pair once. Lock that with a structure test that parses the fence, counts `len(nodes)+len(edges)==55`, and compares the edge set to `itertools.combinations` of the ten IDs.

Do **not** replace the complete graph with a star, a path, a hub-and-spoke, or a “key links only” picture. The user asked whether the README already has every link for full connectivity. It does not.

Do **not** bump `VERSION`. It stays `2.0.8`. Do **not** rebuild the zip, tag, or cut a GitHub Release.

Do **not** add `decisions.md` / `mistakes.md` to `install_into.MANAGED_FILES`. The README **manual** copy list names them; the installer must not clobber consumer logs.

Architect does **not** push. After the write owner lands the tree, `python3 scripts/grok_verify.py --mode pr`, independent reviews, then a **fresh** `python3 scripts/grok_approve.py production` and `git push origin main`.

---

## 1. Current vs required

Live README (`README.md` 16–39) is **K7 only**. Repo explorer counted it: 7 node IDs, 21 `---` lines, `C(7,2)=21`. Role table has the same seven rows. `README.md` has **zero** hits for `decisions.md` / `mistakes.md`.

| Set | IDs | Edges |
| --- | --- | --- |
| Now | Route, Skills, Agents, Hooks, Policy, Verify, Packages | 21 |
| Required | those seven **plus** `Contract`, `Decisions`, `Mistakes` | 45 |

Display labels (exact mermaid text, required in the fence):

```text
Contract["AGENTS.md"]
Decisions["decisions.md"]
Mistakes["mistakes.md"]
```

The first seven keep bare IDs (label = id), matching the current block. Do not rename `Route` → `Router` or split `Verify` / `Packages`.

`HEAD` is still `22762a77` (`Release v2.0.8`). Root `decisions.md` / `mistakes.md`, retargeted `AGENTS.md` bullets, stubs, and self-learning tests are **working-tree leftovers from ba1615**, not on `origin/main`. 04ae05 (`гони`) never pushed. This route finishes that unfinished last mile **after** the README graph is honest.

---

## 2. Mermaid shape (the payload)

Keep one fence under `## Stack graph`. Keep the one-line intro (“every core piece is linked to every other”). Do not add a second diagram.

Recommended block: declare the three labeled nodes, then the upper triangle in the same node order as today, with the three new IDs appended.

Node order (lock this tuple in the test):

```text
Route, Skills, Agents, Hooks, Policy, Verify, Packages, Contract, Decisions, Mistakes
```

All 45 undirected edges, grouped the way the current K7 already is (existing 21 stay; add the 24 new pairs):

```text
Route --- Skills
Route --- Agents
Route --- Hooks
Route --- Policy
Route --- Verify
Route --- Packages
Route --- Contract
Route --- Decisions
Route --- Mistakes
Skills --- Agents
Skills --- Hooks
Skills --- Policy
Skills --- Verify
Skills --- Packages
Skills --- Contract
Skills --- Decisions
Skills --- Mistakes
Agents --- Hooks
Agents --- Policy
Agents --- Verify
Agents --- Packages
Agents --- Contract
Agents --- Decisions
Agents --- Mistakes
Hooks --- Policy
Hooks --- Verify
Hooks --- Packages
Hooks --- Contract
Hooks --- Decisions
Hooks --- Mistakes
Policy --- Verify
Policy --- Packages
Policy --- Contract
Policy --- Decisions
Policy --- Mistakes
Verify --- Packages
Verify --- Contract
Verify --- Decisions
Verify --- Mistakes
Packages --- Contract
Packages --- Decisions
Packages --- Mistakes
Contract --- Decisions
Contract --- Mistakes
Decisions --- Mistakes
```

Math check the implementer must not re-derive differently:

- old K7 = 21
- each of 7 old nodes to each of 3 new = 21
- among the 3 new = `C(3,2)` = 3
- total 21 + 21 + 3 = **45** = `10*9/2`

Forbidden substitutes:

| Shape | Why it fails the test |
| --- | --- |
| Star (new nodes only to `Route`, or only to `Contract`) | missing pairs; edge count &lt; 45 |
| Path / cycle | missing chords |
| Directed `-->` / `---` mixed so some pairs have no `---` | those pairs are absent |
| `A --- B` and `B --- A` | unique undirected set may be 45 but line count ≠ 45 |
| Extra 11th node | `len(nodes) != 10` |
| `flowchart LR` rewrite | out of scope; keep `graph TD` |

No `click`, `classDef`, subgraphs, or `linkStyle`. Dense is the point.

---

## 3. README prose (same file, same change)

### 3.1 Node table

Keep the seven existing rows. Append:

| Node | Role |
| --- | --- |
| Contract | `AGENTS.md` |
| Decisions | `decisions.md` |
| Mistakes | `mistakes.md` |

Role text may add a short gloss (`engineering contract`, `patterns that paid for themselves`, `root causes, not symptoms`) but the filename must appear in the cell.

### 3.2 What this is

Current last bullet only says “Multi-agent discipline described in `AGENTS.md`”. Requirements: name the **self-learning first rule**.

Add one bullet (do not delete the four that exist):

```markdown
- Agent self-learning is the first rule in `AGENTS.md`: log wins in `decisions.md`, root causes in `mistakes.md`
```

That is the wording the structure test should lock: the `## What this is` section contains `self-learning`, `first`, `decisions.md`, and `mistakes.md`.

### 3.3 Manual copy list (`Or copy manually`)

Today (`README.md` 83–90) names `.grok/`, `.agents/skills/`, `.grok-stack/`, `scripts/`, `AGENTS.md`, `engineering/`. Add two **root** lines next to `AGENTS.md`:

```text
decisions.md      → project decisions.md
mistakes.md       → project mistakes.md
```

Do not claim the installer copies those files. The list is the human copy recipe.

---

## 4. Tests (fail first)

Add **one** method on `StructureTests` in `tests/test_structure.py` (same file that already locks root logs + MIT copy). Name: `test_readme_stack_graph_is_k10_complete`.

Current tree must go **red** before the README edit: 7 nodes, 21 edges, no `decisions.md` in README.

### 4.1 Parser

1. Take the first ` ```mermaid ` … ` ``` ` fence in `README.md`.
2. Ignore the `graph TD` line.
3. Node id: `[A-Za-z][A-Za-z0-9_]*`. Optional label suffix `\["[^"]+"\]` is stripped for id purposes.
4. A `---` line is an undirected edge: `frozenset({left, right})`.
5. Standalone `Contract["AGENTS.md"]` lines contribute the id (and prove the label).
6. Do not parse mermaid outside that fence. Do not count `--`, `-->`, `===`.

### 4.2 Assertions (all required)

```text
REQUIRED = (
    'Route', 'Skills', 'Agents', 'Hooks', 'Policy', 'Verify', 'Packages',
    'Contract', 'Decisions', 'Mistakes',
)
```

| Check | Pass when |
| --- | --- |
| Node set | `nodes == set(REQUIRED)` (exactly 10, no extras) |
| Raw `---` count | `== 45` |
| Unique undirected edges | `== 45` |
| **nodes + edges** | `len(nodes) + len(unique_edges) == 55` |
| Every pair | `unique_edges == {frozenset(p) for p in combinations(REQUIRED, 2)}` |
| Labels | mermaid contains `Contract["AGENTS.md"]`, `Decisions["decisions.md"]`, `Mistakes["mistakes.md"]` |
| What-this-is | that section contains `self-learning`, `first`, `decisions.md`, `mistakes.md` |
| Copy list | between `Or copy manually` and the next `## ` heading, a line starts with `decisions.md` and a line starts with `mistakes.md` |
| Table | README body still names `AGENTS.md` and the two root logs outside the fence |

Do **not** hard-code 45 literal `'Route --- Skills'` strings as the only check. Compute expected pairs. Hard-coding the list is how a missing `Policy --- Mistakes` survives a sloppy paste.

Keep `test_agents_md_starts_with_self_learning` and `test_engineering_self_learning_stubs_are_pointers` unchanged. They already lock the ba1615 move.

Do **not** parse `CHANGELOG.md` for these paths. §2.0.8 is the 2.0.8 ship record (`engineering/…`). Leave it.

Do **not** add installer tests unless `install_into.py` changes. It must not.

Existing `test_version_is_2_0_8_and_github_actions_are_absent` already forbids a VERSION bump and GHA.

---

## 5. Installer / packager / identity

| Surface | Ruling |
| --- | --- |
| `scripts/install_into.py` | **No edit.** `merge_agents` already ships the self-learning bullets. Copying this repo’s filled logs would leak product memory and `--force`-clobber consumer files. Same ba1615 ruling. |
| `MANAGED_FILES` / `ENSURE` | Do not add the logs. Do not seed empty consumer stubs. |
| `package_stack.py` / `manifest.included_files` | **No edit.** A later pack will pick root logs up automatically. This route does not pack. |
| `VERSION` | **2.0.8.** Do not touch the file. |
| `packages/*.zip`, `dist/` | **Out.** Brief forbids zip / tag / GitHub Release. Architecture.md “a13da8/ba1615 packages” means **change packages** under `engineering/changes/`, not a zip rebuild. |
| `.github/`, `pyproject.toml`, `requirements.txt`, `setup.py` | Forbidden. Already locked. |
| `CHANGELOG.md` | Leave §2.0.8. Do not invent `## 2.0.9` or `## Unreleased`. |
| `QUICKSTART.md` | No mermaid. Out of scope. |
| 0f3d94 / 04ae05 leftover dirt | Do **not** `git add -A`. This change subsumes the README-name question from 0f3d94. 04ae05’s push is this route’s last mile, not a second commit of that package. |

---

## 6. Write-owner sequence

One owner. Smallest vertical.

1. Add `test_readme_stack_graph_is_k10_complete`. Confirm it fails on the current README (K7, no root-log names).
2. Edit only `README.md`: mermaid + table + What-this-is + copy list as specified.
3. Confirm the new test and the existing self-learning tests are green.
4. Path-limited commit, not `git add -A`. Include:
   - `README.md`, `tests/test_structure.py`
   - ba1615 product leftovers if still uncommitted: root `decisions.md`, `mistakes.md`, `AGENTS.md`, `engineering/decisions.md`, `engineering/mistakes.md`
   - this change package `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-a13da8/`
   - ba1615 change package if still uncommitted
5. `python3 scripts/grok_verify.py --mode pr` on the **final** tree (after evidence files that will remain).
6. Dispatch `code_reviewer` and `test_reviewer`. Record receipts on this route.
7. Fresh production approval, then `git push origin main`. Reason: complete README K10 + ba1615 root logs. User «гони» plus this query authorize **push**, not tag / Release.

Do not implement from a second write agent. Review fixes return here.

---

## 7. Push and rollback

| Step | Rule |
| --- | --- |
| Approval | `git push` is a production invocation. Need a **new** `grok_approve.py production` on this tree. Do not reuse a stale 04ae05 approval. |
| Remote | `origin/main` only. No force-push. No merge commit theater. |
| After push | Root listing shows `decisions.md`, `mistakes.md`; README mermaid is K10. |
| Rollback if not pushed | `git reset --keep origin/main` (package `rollback.md`). |
| Rollback if already on origin/main | Forward-fix. No force-push. |

Architect / this report must not run the push.

---

## 8. Risks

| Risk | Mitigation |
| --- | --- |
| Implementer draws a star “so it stays readable” | Test requires `combinations` equality, not “at least 10 edges” |
| Naive parser treats `Contract["AGENTS.md"]` as the id | Strip the `\["…"\]` suffix |
| Duplicate / reversed `---` lines | Assert raw count **and** unique set both equal 45 |
| Second mermaid later in README | Parse the **first** fence only; do not add a second |
| Installer “helpfully” copies the logs | Forbidden; do not touch `install_into.py` |
| Accidental 2.0.9 / zip / GHA | Out of scope; existing structure tests stay |
| Receipts recorded before the last remaining file | Verify + reviews only after the last README/test/package write that will stay in the tree |
| Unrelated dirty change packages land on main | Path-limited add; brief “leftover dirt” is out |

---

## 9. Out of scope (explicit)

- New services, queues, databases, dependencies, ADRs
- OpenAPI / AsyncAPI / schema changes
- Bitrix / installer behavior change
- Coverage ratchet, Ruff/Bandit config
- Rewriting historical change-package citations of `engineering/decisions.md`

No named human gate. Complexity `standard`, risk `low`. Proceed after this design.
