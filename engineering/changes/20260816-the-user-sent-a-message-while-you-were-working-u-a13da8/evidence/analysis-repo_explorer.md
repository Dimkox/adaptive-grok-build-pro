# Analysis — repo_explorer

Change: `20260816-the-user-sent-a-message-while-you-were-working-u-a13da8`
Route: `a13da8f96b5a`
Question: How many nodes and edges are in README mermaid? Is it K7 only? Are `decisions.md` / `mistakes.md` / `AGENTS.md` in the graph or copy list?

## README mermaid

One mermaid block, `README.md` lines 16–39 (`graph TD`, undirected `---`).

| Measure | Count | Notes |
| --- | --- | --- |
| Nodes | **7** | `Route`, `Skills`, `Agents`, `Hooks`, `Policy`, `Verify`, `Packages` |
| Edges | **21** | every unordered pair once |
| Graph type | **K7 only** | \(C(7,2)=21\); no extra nodes or leftover star/path |

The role table under the diagram lists the same seven IDs. No second mermaid exists in README or QUICKSTART.

**Not K10.** Desired (this change package): add `Contract["AGENTS.md"]`, `Decisions["decisions.md"]`, `Mistakes["mistakes.md"]` and emit all \(C(10,2)=45\) edges.

## Graph membership

| File | In mermaid? | In node table? |
| --- | --- | --- |
| `AGENTS.md` | **No** | No (prose only: “What this is” + `grok inspect`) |
| `decisions.md` | **No** | No (`README.md` has **zero** hits) |
| `mistakes.md` | **No** | No (`README.md` has **zero** hits) |

## Copy list membership

### README documented copy list (`README.md` 83–90)

```
.grok/            → project .grok/
.agents/skills/   → project .agents/skills/
.grok-stack/      → project .grok-stack/
scripts/          → project scripts/
AGENTS.md         → project AGENTS.md
engineering/      → project engineering/  (if empty scaffold needed)
```

| File | README copy list |
| --- | --- |
| `AGENTS.md` | **Yes** — explicit line |
| `decisions.md` (root) | **No** |
| `mistakes.md` (root) | **No** |
| `engineering/` | Scaffold-only; would not name the root logs |

### Installer (`scripts/install_into.py`)

| File | Copied? |
| --- | --- |
| `AGENTS.md` | **Yes** — `merge_agents()` wraps source into `<!-- ADAPTIVE-GROK-PRO:* -->` |
| `decisions.md` | **No** — not in `MANAGED_FILES` / `MANAGED_DIRS` |
| `mistakes.md` | **No** — same |
| `engineering/decisions.md`, `engineering/mistakes.md` | **No** — installer only `ENSURE`s empty dirs (`changes`, `adr`, `runbooks`, …) |

### Package zip (`included_files`)

Walks the whole tree minus secrets/runtime/zips. Root `AGENTS.md`, `decisions.md`, and `mistakes.md` **are** in the zip. That is packaging, not the install copy list the user asked about.

## Impact surface (if write owner expands to K10)

- `README.md` — mermaid, node table, What-this-is, copy list
- `tests/test_structure.py` — add mermaid parse / name locks (today locks root logs + AGENTS self-learning, **not** the graph)
- `scripts/install_into.py` + `tests/test_installer.py` — only if copy-list claim must be true at install time
- Not required for a docs-only graph: `VERSION`, zips, `package_stack.py`

## Answer

**7 nodes, 21 edges — K7 only.** `AGENTS.md` is in the README/installer copy list but **not** in the graph. Root `decisions.md` and `mistakes.md` are in **neither** the graph nor the copy list.
