# Release plan — issue #147

## Deployment

Library change inside the repository's own gate code (`.grok-stack/adaptive_grok/architecture.py`), delivered by
branch `fix/contract-reference-identity-precedence` through a pull request. No artifact is built for installation here,
no service restarts, nothing is migrated. Merge order matters operationally: the deployed Trust CI runner executes the
repo's own verification, so the fix becomes effective for new checks once it is on `main`.

Sequence: commit → `grok_verify --mode pr` on the clean head → route-selected reviews → receipts → push → PR →
App-owned `adaptive-trust-ci/verified@06ecf1c875bc` on the exact head → merge only as a delegated action.

## Feature flags / staged rollout

None. A verification gate cannot be partially enforced: either a shadowed reference resolves correctly or it does not.

## Metrics and alerts

- `SIG-001` — the repro's status pair (`compatible ()` → `incompatible (narrowed_constraint,)`) and the shipped
  differential's zero differing rows out of 25,328 with the grid stated.
- Expected new symptom after merge: an inventory that declares an `$id` equal to another contract's path now fails
  model building with a named error instead of silently capturing references. Measured zero such cases shipped
  (AC-003), so no existing pull request is expected to change verdict — the 9-claimant control (1,178 rows) is the
  evidence that this is a real behaviour change only where capture exists.

## Go/no-go

Go requires all of: 238 focused tests green; `tests.test_structure` green (frozen digests); ruff and `git diff --check`
clean; shipped differential 0 differing rows with the non-vacuity control firing; gate `RESULT: PASS`; three receipts
bound to that fingerprint; external exact-SHA check SUCCESS.

No-go: any changed verdict on the shipped inventory; any pre-existing assertion weakened (beyond the documented
defect-asserting arm); the guard rejecting a self-`$id`; the closure union losing either leg (m6/m7 must stay red).
