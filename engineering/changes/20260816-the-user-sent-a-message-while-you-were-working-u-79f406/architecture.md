# Architecture

One README. Keep the existing K10 complete graph (already locked by tests) and add a **Current state** + **Read first** + **Map** section with markdown links. Do not explode mermaid to 90+ edges unless analysis insists; a complete K10 plus an explicit file map is more usable for an LLM than an unreadably dense K14.

Update `test_readme_*` to require:

- `2.0.8`
- links/names: `AGENTS.md`, `decisions.md`, `mistakes.md`, `QUICKSTART.md`, `CHANGELOG.md`, `.grok/skills/`, `scripts/grok_verify.py`
- existing K10 pairwise completeness
- `self-learning`
- `no GitHub Actions` / never GitHub Actions wording

Stay VERSION 2.0.8.
