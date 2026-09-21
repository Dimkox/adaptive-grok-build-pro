# #59 / #51 — immutable dependency checks and honest test discovery

Research route `d54d3afd1c92`; execution packet, not implementation or verification evidence. One routed writer owns each source branch; serialize edits to shared verifier files. No external authority is created by this packet.

## Required outcome and dependencies

Verification must not repair its own source inputs. Every applicable factory and delivery test module must be accounted for, with database coverage separately identified. Preserve exact-SHA/fingerprint binding and never describe database skips as passes.

Recover local candidate `fix/issue59-frozen-uv-lock` / `aa7dbcdb` for #59. Coordinate first with PR143/#128 (same disposable harness), PR136/#119 (cancellation/report lifecycle), and PR170/#155 (factory fixture timing). #51 then builds on read-only dependency execution. #169's product-scope policy is related but does not need to block adding currently omitted repository tests.

## Implementation sequence and acceptance

1. Port only reviewed #59 product hunks/tests onto the current base; do not transplant stale package receipts. Shared uv prefix uses `uv run --locked`, including restart probes. `--frozen` is not equivalent: it can silently accept manifest drift.
2. Move a named lock consistency check before expensive disposable execution. Missing uv, unavailable offline metadata, invalid manifest and actual lock drift have distinct messages. Test matching and mismatching temporary manifests: lock bytes and repository status remain unchanged on both outcomes. Avoid network resolution in the cheap diagnostic.
3. Inventory current factory/delivery test modules and dependency/import requirements. Add full DB-free factory discovery plus delivery discovery with `factory/src` import roots; preserve independent actual-PostgreSQL evidence. Use installed locked environments or the trusted runner's preinstalled packages; never repair the checkout during verification.
4. Test command selection under normal and repository-sandbox capabilities with subprocess execution mocked. A deliberately failing module outside the old four names must make the correct discovery command fail in a temporary fixture. A newly added discoverable test is included automatically; a database requirement is recorded as skipped/unavailable rather than silently omitted.
5. Report coverage matrix by tier, selected modules and skip reason. Source changes may expose missing image dependencies; record that as unresolved external capability, not a passing source fix. Run focused tests first, then final route verification and selected reviews once the tree is stable.

Files: `factory/tests/run_disposable_exit.py`, `.grok-stack/adaptive_grok/verification.py`, candidate `tests/test_uv_lock_drift.py`, `tests/test_verification_doctor.py` and test-command fixtures. External runner dependency/policy examples may need a separate source proposal; deployed files remain untouched.

## Gates and recovery

Source implementation has ordinary routed verification/review gates. Installing runner dependencies or making a database command mandatory in deployed Trust CI requires the operator's exact image/policy operation and any external signed scopes; source merging cannot perform it. Do not close the entire #51 operational outcome until deployed mandatory coverage is evidenced.

Recovery: a source revert can restore the previous command matrix but must disclose the coverage regression; retain read-only locked behavior. No runtime data migrations are involved. Keep old exact-head reports as history and issue fresh receipts after each change.

Optional, separate enhancements: source-stability changed-path diagnostics, generalized all-package lock inventory, test-manifest machinery. They are not necessary to stop current factory lock mutation or add discoverable factory/delivery tests.
