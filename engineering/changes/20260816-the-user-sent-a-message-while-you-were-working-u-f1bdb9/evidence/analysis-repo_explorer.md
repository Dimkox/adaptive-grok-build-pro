# Analysis — repo_explorer
Route `f1bdb94f5af3`. Standing memory is root `AGENTS.md` (always applied) plus root `decisions.md`.
`AGENTS.md` is the project contract loaded on every task; self-learning writes patterns to root `decisions.md`.
`engineering/decisions.md` is a stub pointing at `/decisions.md`. Never append there.
`mistakes.md` is the error log, not this standing-memory pair.
README mermaid is already K10: Route, Skills, Agents, Hooks, Policy, Verify, Packages, Contract, Decisions, Mistakes.
All 45 undirected `---` pairs are written out (`C(10,2)=45`); do not rewrite that graph.
`tests/test_structure.py::test_readme_stack_graph_is_complete` already asserts those 10 IDs and the exact 45-edge set.
`test_agents_md_starts_with_self_learning` locks `## Agent self-learning` first; insert `## README before push` immediately after that block.
Gaps: no `## README before push` in `AGENTS.md`; no `README is the push-time product map` entry in `decisions.md`.
README has no Current state, Read first, or Map; title already says v2.0.8; it does not name `QUICKSTART.md` or `CHANGELOG.md`.
Write-owner surface: `AGENTS.md`, `decisions.md`, `README.md`, `tests/test_structure.py`. Stay 2.0.8; no tag, pack, or push.
Do not treat `engineering/adr/` or chat as standing memory. User-approved scope: refresh README before every `git push` / `grok_deploy`.
K10 tests already exist; new tests should lock the AGENTS.md heading, the decisions.md title, and keep the existing pairwise check.
No Bitrix/core/CI surface. `human_gates` empty; write owner is `general_implementer`.
