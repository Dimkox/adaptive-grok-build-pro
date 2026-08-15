# Requirements

- [ ] `python3 scripts/grok_verify.py --mode pr` passes on the published tree
- [ ] Zip `packages/adaptive-grok-build-pro-v2.0.5.zip` + sibling sha256
- [ ] `.env`, `err.log`, and `.grok-stack/runtime/*` (except `.gitkeep`) are not in git or the zip
- [ ] Tag `v2.0.5` on the publish commit
- [ ] `git push origin main` and `git push origin v2.0.5`
- [ ] GitHub Release `v2.0.5` with zip, sha256, notes from CHANGELOG 2.0.5
