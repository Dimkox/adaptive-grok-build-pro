# Architecture

Next identity after published 2.0.7 is **2.0.8**. Product delta is the AGENTS.md self-learning first section plus its structure-test lock and the mistakes.md authorship-omission entry.

Surfaces that move with `VERSION`:

- `VERSION`
- `.grok-stack/adaptive_grok/__init__.py` `__version__`
- `README.md` H1
- `CHANGELOG.md` new `## 2.0.8` (leave `## 2.0.7`)
- `packages/README.md` row
- `tests/test_structure.py` `test_version_is_2_0_7_…` → 2.0.8
- `tests/test_manifest_package.py` pins
- `engineering/runbooks/publish-v2.0.8.md` (new; do not rewrite 2.0.7)
- `dist/RELEASE-NOTES.md` scratch (gitignored)

Pack **after** the bump:

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.8.zip* packages/
```

Stage only 2.0.8 product files + this change package. Do not add other routes' leftover evidence.

Last mile for this prompt is `git push origin main` after green verify/review. Tag + `gh release create` stay in the runbook / `grok_deploy` printout. Mint a fresh `grok_approve.py production` row with reason scoped to this push; do not reuse expired 2.0.7 tokens.
