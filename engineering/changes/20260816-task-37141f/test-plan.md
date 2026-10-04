# Test plan

- Existing `test_agents_md_starts_with_self_learning` still green.
- Version pins in `test_structure` and `test_manifest_package` expect 2.0.8.
- Shipped zip has `VERSION=2.0.8`, no `.github/workflows`, no Dependabot, no `github-actions.yml`.
- `test_package_version_matches_version_file`: `__version__` == `VERSION`.
- No packaging markers (`pyproject.toml` / `requirements.txt` / `setup.py`).
- `python3 scripts/grok_verify.py --mode pr` is the gate.
