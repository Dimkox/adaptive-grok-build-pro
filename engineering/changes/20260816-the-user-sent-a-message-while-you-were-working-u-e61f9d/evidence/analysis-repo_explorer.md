# Analysis — repo_explorer
Route `e61f9d74d5c2`. Standing memory is already in-tree: `AGENTS.md` headings[0]=`## Agent self-learning`, headings[1]=`## README before push`, then `## Mandatory entrypoint`.
Those two AGENTS.md rules plus root `decisions.md` (live pattern log) are the memory files; `mistakes.md` is the sibling error log named by the same contract and by this package’s shared-memory set.
`engineering/decisions.md` / `engineering/mistakes.md` are two-line stubs (`Canonical log is /…`; do not append). Tests lock first heading, prefix sinks, and `test_agents_md_requires_readme_refresh_before_push`.
README already has `## Current state` (identity 2.0.8, self-learning + README-before-push named) and `## Read first` (AGENTS.md → decisions.md → mistakes.md → CHANGELOG → QUICKSTART); also Map + locked K10 (45 `---` edges).
Do not redo Current state / Read first / K10. `decisions.md` already has `README is the push-time product map`; keep it.
Gap: no `## Split large tasks` anywhere; no split-task decisions.md entry; no `test_agents_md_splits_large_tasks`.
Write-owner surface: insert `## Split large tasks` after `## README before push`; one ≤3-sentence `decisions.md` entry; one structure test for heading + `shared memory` / `decisions.md`.
Keep `headings[0]` as Agent self-learning. Stay 2.0.8. No tag, pack, push, or CI.
f1bdb9 is still `implementing` the same files; wait if that writer is mid-edit, then continue as the single write owner `general_implementer`.
No Bitrix/core/CI surface. `human_gates` empty.
Shared memory for the new rule: `AGENTS.md` + `decisions.md` + `mistakes.md` (this brief); not chat and not `engineering/adr/`.
