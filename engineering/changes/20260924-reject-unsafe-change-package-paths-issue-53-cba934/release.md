# Release plan — Reject unsafe change-package paths (issue 53)

## Deployment

Library-only change confined to `.grok-stack/adaptive_grok/change.py`, plus the new test module `tests/test_change_path_safety.py`. No migration, no schema change, no new dependency, no service or process to restart: the code ships with the next release-sync and takes effect for every agent session that pulls it. `scripts/grok_change.py`, the only caller, is unchanged. Delivery is a normal pull request; the App-owned policy-epoch check on the exact head SHA is the merge gate and local receipts never substitute for it.

## Feature flags / staged rollout

None needed and deliberately none added — a path-validation gate that can be turned off is not a gate. The behaviour is unconditional for both entry points. The only tuning surface is the constants at the top of `change.py` (`PACKAGES_RELATIVE`, `MAX_COMPONENT_BYTES`, `ALLOWED_COMPONENT_PUNCTUATION`, `TITLE_CONTROL_BYTES`, `DRIVE_PREFIX`), which are source, not configuration; changing any of them is a new change package, not a rollout knob.

## Metrics and alerts

No metric was introduced. The negative signal is the `ValueError` itself: it names the refused input rendered by `printable_value` and the rule that fired (SIG-001), and reaches the operator's terminal or the session log through `scripts/grok_change.py`. A sustained stream of such refusals is the alarm — it means a caller is handing paths where summaries belong, which is the issue #53 bug class, not a user error. The positive signal is structural and is re-checked on every test run: `engineering/changes/` contains only single-component directory names, and the tracked-path scan finds no backslash, `:` or control byte anywhere in the tree.

## Go/no-go criteria

Go, all on the exact head SHA: `tests/test_change_path_safety.py` passes (12 tests, AC-001..AC-005); `python3 -m ruff check .grok-stack/adaptive_grok scripts tests` is clean; `python3 scripts/grok_verify.py --mode pr` passes and its receipts (`verification`, `code_review`, `test_review`) are bound to the final tree fingerprint; the tracked-path structure scan is clean; the external App-owned policy-epoch check succeeds for that SHA and the required signed approval scopes are present.

No-go — re-scope rather than ship — if any name currently under `engineering/changes/` starts refusing, if a title containing `:` or a URL is refused, or if a refusal ever leaves a partial directory behind. The first two are asserted in the test module; the third is asserted by re-listing `engineering/changes/` after each rejected call.
