# Implementation

Change: `20260816-the-user-sent-a-message-while-you-were-working-u-a13da8`  
Route: `a13da8f96b5a` · write owner: `general_implementer`

README now names the root agent logs and the stack mermaid is \(K_{10}\) with every pair linked. The unfinished ba1615 root-log move is included in the same path-limited commit. `VERSION` stays `2.0.8`. No push, tag, or zip from this owner.

## What changed

| Path | Change |
| --- | --- |
| `README.md` | What-this-is bullet: `AGENTS.md` starts with the self-learning rule and writes to `decisions.md` / `mistakes.md`. Mermaid is `graph TD` with `Contract["AGENTS.md"]`, `Decisions["decisions.md"]`, `Mistakes["mistakes.md"]` plus the original seven ids and all 45 undirected `---` edges. Node table and manual copy list name the three files. Caption unchanged: “every core piece is linked to every other.” |
| `tests/test_structure.py` | `test_readme_names_root_self_learning_logs` and `test_readme_stack_graph_is_complete`. First mermaid fence: exactly the 10 required ids, 45 unique `---` pairs, pair set equals `combinations` of those ids. |
| `decisions.md` / `mistakes.md` | ba1615 `git mv` from `engineering/` plus the move/stub entries (still uncommitted on this tree). New decision: emit all 45 pairs so a missing link is a test failure. |
| `engineering/decisions.md` / `engineering/mistakes.md` | Two-line stubs. Canonical log is the root file. |
| `AGENTS.md` | First-section bullets name `decisions.md` / `mistakes.md`, not `engineering/`. |
| ba1615 + this change package | Included in the commit. Leftover other packages not staged. |

Not touched: `VERSION` (2.0.8), `CHANGELOG.md` §2.0.8, `install_into.py`, packager, zip, `pyproject.toml`, GitHub Actions, `QUICKSTART.md`.

## Red then green

On the K7 README (zero `decisions.md` hits):

```
python3 -m unittest \
  tests.test_structure.StructureTests.test_readme_names_root_self_learning_logs \
  tests.test_structure.StructureTests.test_readme_stack_graph_is_complete -q
```

- `test_readme_names_root_self_learning_logs` — `AssertionError: 'decisions.md' not found`
- `test_readme_stack_graph_is_complete` — `AssertionError: 'Contract' not found`

After the README edit:

```
python3 -m unittest tests.test_structure -q
```

`Ran 17 tests in 0.010s` · `OK`

Independent count on the first mermaid fence: 10 nodes, 45 unique undirected edges, empty missing-pair set. Display labels `Contract["AGENTS.md"]`, `Decisions["decisions.md"]`, `Mistakes["mistakes.md"]` are present. `VERSION` file is still `2.0.8`.

## Residual risk

- `origin/main` still lacks the root logs and the K10 README until the controller pushes. This owner does not push.
- `install_into` still does not seed consumer `decisions.md` / `mistakes.md`. The README copy list is the manual recipe only.
- Published `CHANGELOG.md` §2.0.8 and the 2.0.8 zip still describe `engineering/` as the log path. Left as the ship record.
- A star or K7-plus-pendants regression fails `test_readme_stack_graph_is_complete` because the pair set is compared to `combinations`, not “at least N edges.”
