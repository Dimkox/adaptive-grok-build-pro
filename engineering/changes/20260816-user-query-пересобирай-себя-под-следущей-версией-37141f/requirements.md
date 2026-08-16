# Requirements

- [x] `VERSION` and `__version__` are `2.0.8`
- [x] CHANGELOG has `## 2.0.8` first; README H1 is `v2.0.8`; packages/README has a 2.0.8 row
- [x] `AGENTS.md` still starts with `## Agent self-learning` pointing at `engineering/decisions.md` / `engineering/mistakes.md`
- [x] `packages/adaptive-grok-build-pro-v2.0.8.zip` exists; in-zip `VERSION` is `2.0.8`; no GHA / Dependabot / `pyproject.toml`
- [x] Structure tests pin 2.0.8 and still lock the self-learning first heading
- [ ] `python3 scripts/grok_verify.py --mode pr` PASS
- [ ] Independent `code_review` PASS
- [ ] `origin/main` has the 2.0.8 ship commit after the above is green
