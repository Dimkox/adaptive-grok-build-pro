# M4 implementation ledger

## Gate and base binding

- Exact implementation base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`.
- Clean-base tree fingerprint: `17f8ca8d94a118d02192e5fa0bd9cafc6e219354e390f1d640511d6e6a4fcaa2`, derived by the repository `tree_fingerprint` algorithm before package edits.
- Scope/design: explicitly approved by the user in the active conversation.
- Migration scope: fresh disposable local PostgreSQL only; no external, shared, Trust CI or production write.
- Producer handoff ruling: M2/M3 exact-base/head values remain producer-owned frozen values; M4 validates them and does not replace them with its implementation base.

## TDD cycles

Each vertical records its RED command/result before production source is added, then GREEN/refactor commands. Final real PostgreSQL and root verifier evidence is appended after the last product change.

### Contracts

- RED: `python3 -m unittest factory.tests.test_contracts -v` failed with `ModuleNotFoundError: adaptive_factory`; the package/contract behavior was absent.
- GREEN: the same command passed 5 tests after closed immutable handoffs/intake/limits, canonical digests, M0 freshness/exception and bounds were implemented.
- Focused repair: the first GREEN exposed that a valid App check name contains `@`; the existing failing contract test drove a bounded check-name grammar repair, after which all 5 passed.

### State and retry policy

- RED: `python3 -m unittest factory.tests.test_state -v` failed because `adaptive_factory.state` did not exist.
- GREEN: the same command passed 6 tests covering every state pair, terminality, operator requeue evidence, provider denial, rejected future delivery states and the initial-plus-two closed retry policy.
