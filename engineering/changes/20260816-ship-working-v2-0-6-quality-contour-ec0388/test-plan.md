# Test plan

1. Characterization: marker-less + ruff on PATH still emits `python-unittest`.
2. Characterization: marker + pytest still wins; ruff/bandit still run before that return.
3. Fail: unused import in a QUALITY path → `ruff` fail.
4. Fail: `eval` under `.grok-stack/adaptive_grok/` → `bandit` fail; same in `tests/` does not.
5. `secret-scan` still fails on a planted API key.
6. No packaging marker, no Dockerfile, no semgrep config → no `semgrep` / `trivy-config` / `npm-*`.
7. Semgrep signal + no binary → `skip`.
8. Existing unittest / contract / sql / doctor tests stay green.
9. `test_root_workflow_equals_template` stays green.
10. Official `python3 scripts/grok_verify.py --mode pr` PASS on the 2.0.6 tree.
