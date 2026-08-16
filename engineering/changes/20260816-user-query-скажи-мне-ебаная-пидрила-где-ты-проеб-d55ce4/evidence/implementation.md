# Implementation

Change: `20260816-user-query-скажи-мне-ебаная-пидрила-где-ты-проеб-d55ce4`  
Route: `d55ce4cd4015` · write owner: `general_implementer`

Restored the agent self-learning instruction as the first `##` section in `AGENTS.md` and locked it with a structure test. Did not bump `VERSION`, publish, edit Bitrix core, add `pyproject.toml`, or add GitHub Actions.

## Changed files

- `AGENTS.md` — inserted `## Agent self-learning` immediately after the H1 and before the intro paragraph / `## Mandatory entrypoint`. Paths are `engineering/decisions.md` and `engineering/mistakes.md`.
- `tests/test_structure.py` — added `test_agents_md_starts_with_self_learning`.
- `engineering/mistakes.md` — appended 2026-08-16 entry (authorship omission at `ca63b2d`, not a later delete; logs added in `097f5c9` without the trigger). Existing entries unchanged.

## Commands and results

1. Red: `python3 -m unittest tests.test_structure.StructureTests.test_agents_md_starts_with_self_learning`

   Failed as required: `AssertionError: '## Mandatory entrypoint' != '## Agent self-learning'`.

2. After inserting the section: `python3 -m unittest tests.test_structure`

   `Ran 14 tests in 0.009s` — `OK`.

## Residual risk

- Consumers already installed get the new bullets only on re-install / re-package (`merge_agents` copies root `AGENTS.md` verbatim). Out of scope for this change.
- Installer still does not seed empty `engineering/decisions.md` / `engineering/mistakes.md` in consumer trees. This repo already has the sinks.
- Skills (`adaptive-delivery`) were not updated; the contract lock is `AGENTS.md` + the structure test.

## Rollback

Revert the `AGENTS.md` section, the structure test, and the new `mistakes.md` entry. No data migration.
