# Docs research — README complete graph wording and core pieces

Route: `a13da8f96b5a`. Change: `20260816-the-user-sent-a-message-while-you-were-working-u-a13da8`.

Question: original README graph was a K7 complete stack graph. User now wants a complete graph with all links. Confirm the standing wording “Simple complete graph: every core piece is linked to every other” and that new core pieces are `AGENTS.md`, `decisions.md`, `mistakes.md`. QUICKSTART: one-liner or skip.

Read-only. No APIs invented. No `.env`. No push / merge / deploy.

## Sources

- `README.md` § Stack graph (lines 12–49) and copy list (83–90)
- `QUICKSTART.md` (full file)
- `AGENTS.md` `## Agent self-learning` + source-of-truth order
- Root `decisions.md`, root `mistakes.md`
- `engineering/decisions.md`, `engineering/mistakes.md` (stubs)
- `CHANGELOG.md` §2.0.3 and §2.0.8
- `tests/test_structure.py` (`test_required_files_exist`, `test_agents_md_starts_with_self_learning`, `test_engineering_self_learning_stubs_are_pointers`, `test_readme_is_free_mit_commercial_product`)
- This change package (`brief.md`, `requirements.md`, `architecture.md`, `test-plan.md`, `tasks.md`, `release.md`)
- Prior packages: `20260814-rename-remaining-codex-branding-to-grok-and-docu-b8b188` (origin of the graph), `20260816-user-query-я-все-еще-не-вижу-файлов-из-промпта-д-ba1615` (root logs), `20260816-user-query-гони-user-query-04ae05` (unfinished push)
- Sibling `evidence/analysis-repo_explorer.md`
- `.grok/skills/adaptive-delivery/SKILL.md`, `.grok/skills/feature-workflow/SKILL.md`
- `scripts/install_into.py` (copy/merge surface only; no new installer API)
- `engineering/adr/` (empty)
- `engineering/contracts/{openapi,asyncapi,schemas}/` (empty; no product APIs)

---

## Verdict

| Claim | Standing fact? |
| --- | --- |
| README caption is exactly `Simple complete graph: every core piece is linked to every other.` | **Yes.** `README.md:14`. Keep that sentence. |
| Original / current mermaid is a **K7** complete stack graph | **Yes.** 7 nodes, 21 undirected `---` edges = \(C(7,2)\). |
| User asked whether the **full** graph with every link is already in README | **No, it is not**, once `AGENTS.md` / `decisions.md` / `mistakes.md` count as core pieces. Current K7 is complete only over the seven runtime nodes. |
| New core pieces to add as graph nodes | **`AGENTS.md`, `decisions.md`, `mistakes.md`.** Already required by `AGENTS.md` first rule + ba1615 + structure tests. Not yet in the mermaid or node table. |
| QUICKSTART must grow a mermaid | **No.** One-liner pointing at README § Stack graph, or **skip**. Do not paste 45 edges. |

No ADR or OpenAPI/AsyncAPI/schema names the graph, the node IDs, or a QUICKSTART duplicate. There is no graph API. The mermaid is documentation.

---

## 1. Standing wording — confirmed verbatim

`README.md:12-14`:

```
## Stack graph

Simple complete graph: every core piece is linked to every other.
```

That sentence is the completeness contract. It was introduced with the original graph (b8b188 / CHANGELOG 2.0.3: “README complete-graph of the stack”). It is **not** in `QUICKSTART.md`, `AGENTS.md`, skills, ADRs, or tests.

`test_structure.py` `test_readme_is_free_mit_commercial_product` locks MIT / commercial / free / public / no EULA. It does **not** lock the caption, node set, or edge count.

**Write-owner implication:** keep the caption. Expanding the node set without adding every new pair would violate the sentence.

---

## 2. Original graph is K7 — confirmed

Origin package `b8b188` user request (2026-08-14):

> добавь в README простой полносвязный граф стека

Its code review recorded the result as “README includes a **K7** complete graph of the stack.” CHANGELOG 2.0.3: “README complete-graph of the stack.”

Current mermaid (`README.md:16-39`) is still that K7:

| Node | Role table path |
| --- | --- |
| Route | `scripts/grok_route.py` / active-route |
| Skills | `.grok/skills/` and `.agents/skills/` |
| Agents | `.grok/agents/` |
| Hooks | `.grok/hooks/` |
| Policy | `.grok-stack/adaptive_grok/policy.py` |
| Verify | `scripts/grok_verify.py` + receipts |
| Packages | `packages/` + `scripts/package_stack.py` |

21 unique undirected `---` lines, every pair once. Sibling `analysis-repo_explorer.md` counts the same 7 / 21.

This is a complete graph **of the runtime stack**, not of every root contract file.

---

## 3. User now wants a complete graph with all links

Current user query (this route / `brief.md`):

> и полный граф со всемы ссылками для полной связности ты в ридми положил, да, ска?

Answer from the tree: **the K7 is fully linked among its seven nodes; it is not a complete graph over every current core piece.** `AGENTS.md` is named in prose and the copy list but is not a mermaid node. Root `decisions.md` and `mistakes.md` have **zero** README hits.

This package already records the intended expansion (`architecture.md`, `requirements.md`):

- Keep the caption.
- Add three labeled nodes: `Contract["AGENTS.md"]`, `Decisions["decisions.md"]`, `Mistakes["mistakes.md"]`.
- Emit all \(C(10,2)=45\) undirected `---` edges. Do not leave a star or a path.
- Lock with a structure test that parses `---` lines.

No standing doc forbids that expansion. No standing doc already claims the mermaid is K10.

---

## 4. New core pieces are AGENTS.md, decisions.md, mistakes.md — confirmed

These three are the files the Engineering Contract and the ba1615 user-approved move treat as first-class root artifacts. They are the only root contract files missing from the graph.

### `AGENTS.md`

- Title: Adaptive Grok Build Pro Engineering Contract.
- First heading is `## Agent self-learning`.
- SoT #1 after user-approved scope; installer `merge_agents()`; doctor required file; `test_required_files_exist`.
- Already in README “What this is” and the manual copy list.
- **Not** a mermaid node.

### `decisions.md` / `mistakes.md`

`AGENTS.md:5-6` (live bullets, locked by `test_agents_md_starts_with_self_learning`):

- log it in **`decisions.md`**
- record it in **`mistakes.md`**

ba1615 (`brief.md`, `architecture.md`, `implementation.md`): user could not see the prompt files at the root; `git mv` to `/decisions.md` and `/mistakes.md`; `engineering/` paths are two-line stubs (“Canonical log is /…. Do not append here.”). Structure tests require the root files and forbid `engineering/` as the live sink.

`decisions.md` header: “Patterns that paid for themselves.” `mistakes.md` header: “Root causes, not symptoms.”

They are **not** in README prose, mermaid, node table, or copy list.

### Not other files

Do not add `CHANGELOG.md`, `QUICKSTART.md`, `VERSION`, or `engineering/changes/` as mermaid nodes unless a later user-approved ruling says so. Those are not named by the self-learning rule or this package’s 10-node list.

### Installer is not a graph API

`install_into.py` merges `AGENTS.md`. It does **not** copy root `decisions.md` / `mistakes.md` (`MANAGED_FILES` / `MANAGED_DIRS`; ba1615 left that as “file appears when used”). README’s copy list is the **manual** recipe (`Or copy manually:`). Adding the two filenames there documents a copy step; it does not create an installer function. Do not invent `MANAGED_FILES` entries unless a later change explicitly owns installer behavior.

---

## 5. QUICKSTART — one-liner or skip

`QUICKSTART.md` is a 7-step install / work / verify path. Facts:

| Surface | Graph / logs? |
| --- | --- |
| Mermaid | **None** |
| Caption | **None** |
| `AGENTS.md` | **None** |
| `decisions.md` / `mistakes.md` | **None** |
| Version string | **None** (standing: version-silent since 2.0.1+) |
| README link to QUICKSTART | **None** |

No ADR, skill, or contract requires QUICKSTART to duplicate the stack graph. Prior packages treated QUICKSTART feature-gap expansions as out of scope (install path only; 2eacdf only closed the verify fence). This package’s acceptance list does **not** name QUICKSTART.

**Recommendation:** **skip** QUICKSTART (preferred). If a pointer is wanted, one sentence under step 4/5, e.g. that the complete stack graph lives in README § Stack graph. Do **not** paste a 45-edge mermaid.

---

## 6. Related docs that this change should not rewrite as if they were APIs

| Surface | Fact |
| --- | --- |
| `CHANGELOG.md` §2.0.8 | Still says log-to-`engineering/decisions.md` / `engineering/mistakes.md` (the 2.0.8 ship record). ba1615 left it. This package does not require a 2.0.9 bullet. |
| `CHANGELOG.md` §2.0.3 | Historical “README complete-graph of the stack” = the K7, not a K10 promise. |
| `VERSION` | Stays **2.0.8** (`release.md`, 04ae05, architecture). No zip / tag / GitHub Release. |
| `engineering/adr/` | Empty. No ADR to amend. |
| Contracts | Empty. No OpenAPI/event schema for the graph. |
| Unfinished «гони» push (`04ae05`) | Push `origin/main` only after green verify/reviews; no identity bump. This route folds that last mile after the README K10. |

---

## Fact for the write owner

1. Keep `Simple complete graph: every core piece is linked to every other.`
2. Current mermaid is K7 (Route, Skills, Agents, Hooks, Policy, Verify, Packages) — 21 edges.
3. Add `Contract["AGENTS.md"]`, `Decisions["decisions.md"]`, `Mistakes["mistakes.md"]` and all 45 undirected pairs.
4. Name those three files in the node table; name the self-learning first rule in What-this-is; add the two logs to the **manual** copy list.
5. Lock names + 10 nodes + 45 edges in `tests/test_structure.py`. No mermaid lock exists today.
6. QUICKSTART: skip, or one pointer sentence. No second graph.
7. Do not invent installer/doctor APIs, do not bump `VERSION`, do not edit Bitrix core, do not add `.github/workflows` or `pyproject.toml`.
