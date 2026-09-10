# Implementation evidence — historical accounting

Route `78b680187560`; sole application-code writer `ai_implementer`. All implementation and focused checks used the isolated evidence worktree. This report contains synthetic verification only. Root owns final full verification, independent reviews, fingerprint receipts and delivery.

## Delivered scope

- `.grok-stack/adaptive_grok/history.py`: bounded explicit-file loading, closed version-1 validation, canonical identity/deduplication, conflict rejection and deterministic source-bound accounting.
- `scripts/grok_history.py`: offline JSON-stdout CLI with safe schema errors; consumer delivery through `scripts/install_into.py` and `.grok-stack/config/managed.json`.
- `tests/test_history.py`: 31 synthetic tests; installer payload and installed CLI help added to existing installer tests.
- `examples/historical-evidence/synthetic.json`, `engineering/runbooks/historical-autonomy-evidence.md` and one README link: source capture, exact input schema, unknown denominators, profile limits and next capability order.
- Append-only decisions/mistakes facts describe denominator separation and rejected-read descriptor ownership.

No factory, M7, autonomy tuple, deployed policy or runtime authority implementation changed. The utility imports no network or subprocess capability. It reads only the explicitly supplied regular snapshot file and does not follow evidence references.

## Test-first evidence

Initial command before the module existed:

```text
python3 -m unittest tests.test_history
ModuleNotFoundError: No module named 'adaptive_grok.history'
Ran 1 test in 0.000s
FAILED (errors=1)
```

The missing implementation was the expected initial collection failure. The first implemented module/CLI passed all 27 initial history tests:

```text
python3 -m unittest tests.test_history
Ran 27 tests in 0.207s
OK
```

Installer tests were extended before enrolling the script:

```text
python3 -m unittest tests.test_installer.InstallerTests.test_payload_is_sorted_safe_duplicate_free_and_profile_explicit tests.test_installer.InstallerTests.test_materialize_new_publishes_verified_payload_once
FAIL: 'scripts/grok_history.py' not found in the managed payload
FAIL: installed scripts/grok_history.py is absent (subprocess exit 2)
Ran 2 tests in 1.233s
FAILED (failures=2)
```

After enrolling the entrypoint:

```text
python3 -m unittest tests.test_history tests.test_installer
Ran 44 tests in 9.762s
OK
```

An explicit resource probe found leaked descriptors when `os.fdopen` rejected a directory; a separate test showed Python accepted malformed offset minutes. Regressions were added before repairing both:

```text
python3 -m unittest tests.test_history.HistoryTests.test_rejected_directory_does_not_leak_descriptors tests.test_history.HistoryTests.test_malformed_timezone_offsets_are_rejected
FAIL: descriptor count 7 != 4
FAIL: HistoryError not raised for timestamp offset +00:99
Ran 2 tests in 0.002s
FAILED (failures=2)
```

Explicit descriptor ownership and strict offset ranges repaired these failures. Additional limits/cyclic-input and opaque-reference coverage brought history tests to 31.

## Final focused verification

```text
python3 -m unittest tests.test_history tests.test_installer tests.test_structure tests.test_repo_router
Ran 93 tests in 26.603s
OK

ruff check .grok-stack/adaptive_grok/history.py scripts/grok_history.py scripts/install_into.py tests/test_history.py tests/test_installer.py
All checks passed!

git diff --check
exit 0; no output

python3 scripts/grok_history.py examples/historical-evidence/synthetic.json > /tmp/synthetic-history-report.json
exit 0
```

The synthetic example reports 3 observed PRs, 2 merged PRs, 2 identified work units and 1 explicit imported acceptance. Both task and accepted full-history totals stay null because the task inventory is incomplete. Intervention coverage reports 1 complete session and 1 partial session; the complete-session zero-intervention rate uses denominator 1, while the overall observed intervention lower bound is 2. Qualification remains `not_evaluated` and authority effect remains `none`.

Tests also cover actor `User` without intervention inference, many-to-many task/PR links, branch synchronization, open-but-reachable heads, identical/conflicting repository/PR/task observations, unknown metrics versus measured zero, malformed JSON/counts/digests, regular-file/byte/depth/count limits, missing profile fields, repository mismatches, changed profile separation, unsupported/expired metadata, and 30 synthetic acceptance claims with no authority effect.

## Bounded implementation rulings and limitations

The final input schema was sent to root before private normalization. `delivery_kind` is the sole optional PR field and defaults to `unknown`; nullable task fields remain explicitly required, while sparse profiles normalize all missing fields to null. Task `source_refs` carries general measurement provenance; intervention-specific sources and bounded complete sessions are validated separately.

`accepted_task_total` also remains null when a complete task inventory contains unknown acceptance or only documented validation. Complete metadata is an accounting group only; unsupported classes, schemas, ceilings and expired-at-capture profiles remain observed with explicit diagnostics. False reachability is labeled `identity_not_reachable`, because squash/cherry-pick delivery may preserve equivalent code without the original identity.

Imported source references, acceptance claims, measurement completeness and profile metadata are not authenticated. Reports do not evaluate M8 eligibility, external acceptance/currentness, audit sufficiency or safety thresholds. No aggregate across repositories or incomplete/different profiles contributes to a 30-task bucket. Root's private report and external exact-SHA gate remain separate work.

Rollout is optional CLI use with an explicitly selected snapshot. Rollback removes or stops invoking the utility; it has no persistent product state to migrate. Private artifact retention/deletion stays with the operator.
