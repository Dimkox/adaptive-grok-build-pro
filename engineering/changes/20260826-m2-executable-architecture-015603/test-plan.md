# Test plan — M2-A Executable Architecture

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Malformed/ambiguous/unsafe architecture input fails closed | `tests/test_architecture_model.py` |
| P0 | Secret/trust/workspace/mixed-change rules cannot be weakened | `tests/test_architecture_fitness.py`, security review |
| P0 | Post-risk cannot fall and exact evidence cannot use the stale route base | fitness tests, verification receipt |
| P1 | Contract/migration/job/network/import/budget categories are explicit and conservative | fitness/model tests, data/test reviews |
| P1 | Queue branch/container/alias/scope provenance uses bounded monotone joins; relevant uncertainty is unsupported and unrelated operations stay N/A | fitness tests, code/test/security reviews |
| P1 | Stdout-only diagrams and CLI output are reproducible and repository-read-only | model tests, `diagram`, `diagram --check` |
| P1 | Existing-target planning is byte/metadata read-only and executes no dependency advice | installer tests, release review |
| P1 | Absent-target materialization publishes a verified stage with no-replace semantics | installer/manifest tests, security/release reviews |
| P1 | Installer packages valid examples but never manages marker/model/rules; `--force` is rejected | installer/manifest tests |
| P1 | Unresolved constructor identity preserves the current entry and emits the stable manual-cleanup diagnostic | installer tests, security review |
| P1 | K16 remains exactly 120 decorative inventory edges and links point to real architecture authority | structure tests |

## Automated checks

- Unit: both architecture modules plus existing root discovery.
- Contract: strict schemas and existing HTTP/envelope baselines.
- Compatibility: M1 spec/receipt behavior and unconfigured installed consumer.
- Static: Ruff, Bandit, compileall, AST fitness, `git diff --check`.
- Integration: local `grok_verify --mode pr --no-record --json`, then coordinator-owned exact-head verification and exact-fingerprint receipts.

## Safety-pivot command set

```bash
python3 -m unittest -v tests.test_architecture_model tests.test_architecture_fitness tests.test_installer tests.test_manifest_package tests.test_structure
python3 scripts/grok_spec.py validate --change-id 20260826-m2-executable-architecture-015603 --gate --json
python3 -m unittest discover -s tests
ruff check .grok-stack/adaptive_grok scripts tests
bandit -q -r .grok-stack/adaptive_grok scripts
python3 -m compileall -q .grok-stack/adaptive_grok scripts
python3 scripts/grok_architecture.py validate --json
python3 scripts/grok_architecture.py summary --json
python3 scripts/grok_architecture.py drift --json
python3 scripts/grok_architecture.py diagram --json
python3 scripts/grok_architecture.py diagram --check
python3 scripts/grok_architecture.py diff --base 25bfbe59ea188d9687b20a9caad19e7db3d031f8 --head <reviewed-40-character-head-sha> --json
python3 scripts/grok_architecture.py fitness --base 25bfbe59ea188d9687b20a9caad19e7db3d031f8 --head <reviewed-40-character-head-sha> --pre-risk red --json
python3 scripts/grok_verify.py --mode pr --no-record --json
git diff --name-only 25bfbe59ea188d9687b20a9caad19e7db3d031f8...HEAD -- trust-ci
git diff --name-only 25bfbe59ea188d9687b20a9caad19e7db3d031f8...HEAD -- .github/workflows
```

For exact diff and fitness, replace the placeholder with the literal 40-character commit SHA already selected as the immutable review head. Never use `HEAD` or `--worktree` for this reproducible release evidence; `--worktree` remains diagnostic only.

## Manual checks

- Inspect all five stdout-rendered/checked-in views and architecture diff for truthfulness; projection updates use normal reviewed source edits.
- Confirm no changed path under `trust-ci/**` relative to the adoption base.
- Confirm docs describe M2-A as local/source-ready only and identify M2-B/deployment gaps.
- Confirm `--plan` is read-only, `--materialize-new` accepts only an absent target, `--force` is rejected, dependency commands are advice only, and authority paths are absent from every payload.
- Inject staging constructor failures and confirm known-owned entries clean exactly while unresolved identity preserves the name with `manual cleanup required: installer ownership is unresolved`.
- Compare receipt `active_architecture_binding` base selection with verification `_architecture_base` on the exact final tree before final review closure.
