# M3 Task 7 independent code review

Status: **CHANGES_REQUIRED**

Reviewed product commit: `b688c61` (`9dc89af..b688c61`)

## Findings

### HIGH — Complete registry deletion downgrades adopted governance to unconfigured

- Location: `.grok-stack/adaptive_grok/receipts.py:280-339`, especially the `not any(present)` branch at line 335.
- Impact: after all three governance registries have existed and been bound into a receipt, deleting all three makes `active_governance_binding()` return `None`. A direct review/verification receipt writer can then replace the governed receipt with a passing receipt that contains no governance binding. This violates the fail-closed receipt boundary and permits governance removal without an explicit revocation/adoption transition.
- Reproduction: in a temporary Git project, copy and commit architecture plus all three governance registries, write a passing verification receipt, unlink `governance/rules/index.json`, `governance/debt/index.json`, and `governance/canonical-examples/index.json`, then call `write_receipt(..., "verification", "pass")`. Observed: `after_binding None` and `downgrade_receipt_has_governance False`.
- Required repair: distinguish a genuinely legacy/unconfigured repository from previously configured governance using exact Git/base-history evidence or an explicit target-owned adoption marker. Once adopted, complete deletion must fail closed. Add a regression at the direct `write_receipt` boundary, not only through architecture fitness.

### HIGH — Governance validation accepts a different architecture snapshot than the preceding architecture check

- Location: `.grok-stack/adaptive_grok/verification.py:178-204`; `_governance_check()` accepts `architecture` but line 184 ignores it and calls `active_governance_binding(root, route or {})` without the checked binding.
- Impact: architecture can validate on state A and governance can independently re-read valid state B. Both checks report `pass` even though `architecture.architecture_digest` differs from `governance.governance_architecture_digest`; the later receipt write rebinds current state but does not rerun the earlier architecture fitness verdict. This is a source-mutation/TOCTOU gap in exact-fingerprint evidence.
- Reproduction: capture a passing `active_architecture_binding`, mutate a valid field in `architecture/system.yaml`, then call `_governance_check(root, route, old_metadata)`. Observed: `governance_status pass`, checked digest `f05c...a76bc`, governance architecture digest `4814...d535`, and `mismatch_accepted True`.
- Required repair: make governance consume and verify the exact successful architecture binding from the preceding check, reject non-pass/incomplete architecture metadata, and assert digest/base/head consistency. Recheck the repository fingerprint before recording the verification receipt so source changes after the semantic checks cannot reuse their verdicts.

## Passing targeted evidence

- Receipt/governance tests: 3/3 passed after correcting the test class selector.
- Verifier ordering/failure test: 1/1 passed.
- Installer plus README/core/complete-K16 tests: 5/5 passed.
- Ruff on Task 7 Python surfaces: passed.
- Bandit on Task 7 production Python surfaces: passed.
- `git diff --check 9dc89af..b688c61`: passed.

The installer payload includes the engine, CLI, four schemas, and templates while excluding the three canonical target-owned registry paths. README current-state language, M4 pending boundary, and the complete K16 graph test are consistent with the reviewed tree. These passing areas do not close the two receipt provenance gaps above.
