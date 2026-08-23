# Requirements — v2.0.12 ship

## Acceptance criteria

- [ ] VERSION, README H1, CHANGELOG, packages zip, and `tests/test_manifest_package.py` say 2.0.12.
- [ ] Trust CI service identity remains 2.1.0. Example image pins remain `REPLACE_WITH_*`.
- [ ] Leftover `20260817-вычисти*` and pin env/PEMs are not committed.
- [ ] `python3 scripts/grok_verify.py --mode pr` passes on the ship tree.
- [ ] Independent security_review and release_review pass.
- [ ] PR #2 is rebase-merged to `main`. Tag `v2.0.12` points at the merged SHA. GitHub Release exists with the zip assets.
- [ ] `.github/workflows/` remains absent.

## Non-goals

- GitHub App, deploy, webhook proof, branch protection.
- Invented Trust CI check runs.
