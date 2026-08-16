# Implementation

Change: `20260816-user-query-я-все-еще-не-вижу-файлов-из-промпта-д-ba1615`  
Route: `ba1615416da5` · write owner: `general_implementer`

## What changed

One source of truth moved to the repo root. Old `engineering/` paths are pointers only.

| Path | Change |
| --- | --- |
| `decisions.md` | `git mv` of `engineering/decisions.md`. All 13 prior `##` entries byte-identical. New ≤3-sentence entry: move-not-copy + stub at the old path. |
| `mistakes.md` | `git mv` of `engineering/mistakes.md`. All 3 prior `##` entries byte-identical. New root-cause entry: we hid the prompt files under `engineering/`. |
| `engineering/decisions.md` | Two-line stub: “Canonical log is /decisions.md. Do not append here.” No dated entries. |
| `engineering/mistakes.md` | Two-line stub: “Canonical log is /mistakes.md. Do not append here.” No dated entries. |
| `AGENTS.md` | First-section bullets restored to `log it in decisions.md` / `record it in mistakes.md`. `## Agent self-learning` still first. |
| `tests/test_structure.py` | `test_agents_md_starts_with_self_learning` now requires root files, exact root phrases, and forbids `engineering/` as the live sink. Sibling `test_engineering_self_learning_stubs_are_pointers` locks the stubs. |

Not touched: `VERSION` (2.0.8), `CHANGELOG.md` §2.0.8, `install_into.py` / `MANAGED_FILES`, packager, zip, historical change-package citations, `pyproject.toml`, GitHub Actions.

## Red then green

Failing test first, on the tree that still had logs only under `engineering/` and `AGENTS.md` bullets naming those paths:

```
python3 -m unittest tests.test_structure.StructureTests.test_agents_md_starts_with_self_learning \
    tests.test_structure.StructureTests.test_engineering_self_learning_stubs_are_pointers -q
```

- `test_agents_md_starts_with_self_learning` — `AssertionError: False is not true : decisions.md`
- `test_engineering_self_learning_stubs_are_pointers` — `AssertionError: 55 not less than or equal to 5 : engineering/decisions.md`

After `git mv`, stubs, and `AGENTS.md` retarget:

```
python3 -m unittest tests.test_structure -q
```

`Ran 15 tests in 0.009s` · `OK`

## Residual risk

- Published `CHANGELOG.md` §2.0.8 still names `engineering/` (left as the 2.0.8 ship record). A later version can mention the relocation.
- `packages/adaptive-grok-build-pro-v2.0.8.zip` still has the logs only under `engineering/`. No pack in this change.
- Historical change-package text still cites `engineering/decisions.md`. Those documents describe the path that existed then; the stub is what a follower of an old link hits.
- `install_into` still does not seed consumer `decisions.md` / `mistakes.md`. After this `AGENTS.md` retarget, a consumer agent creates the root files on first real write — same “file appears when used” behavior as today.
- A stale writer that ignores the stub and appends to `engineering/` will fail `test_engineering_self_learning_stubs_are_pointers` (dated `## 20` or >5 lines).
