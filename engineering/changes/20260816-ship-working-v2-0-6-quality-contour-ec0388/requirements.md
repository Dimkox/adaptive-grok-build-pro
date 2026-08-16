# Requirements — working 2.0.6

## Acceptance

- [x] Marker-less tree still runs `python-unittest` (Ruff present or absent)
- [x] `ruff` runs without packaging markers; missing binary → skip; CI fail-closed after install
- [x] `bandit` does not replace `secret-scan`; planted `eval` in product paths fails; planted `eval` in `tests/` does not
- [x] Coverage measured this session; `fail_under = floor(line%) - 2`; no 90% invention; `fast` does not fail-under
- [x] Dependabot `.github/dependabot.yml` is `github-actions` only
- [x] Semgrep / Trivy / npm prettier|format do not appear on this tree
- [x] `VERSION` is `2.0.6`; CHANGELOG `## 2.0.6`; README H1; packages zip + sha256
- [x] No `pyproject.toml` / `requirements.txt` / `setup.py`
- [x] CI template and `.github/workflows/adaptive-grok.yml` stay byte-identical
- [x] No tag / push / `gh release`

## Non-goals

Dobryakov dump, Codecov, `trivy image`, `semgrep --config auto`, `npx` without a script, Bucket C SaaS.
