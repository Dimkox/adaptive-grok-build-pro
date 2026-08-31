# M4 implementation ledger

## Gate and base binding

- Exact implementation base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`.
- Clean-base tree fingerprint: `17f8ca8d94a118d02192e5fa0bd9cafc6e219354e390f1d640511d6e6a4fcaa2`, derived by the repository `tree_fingerprint` algorithm before package edits.
- Scope/design: explicitly approved by the user in the active conversation.
- Migration scope: fresh disposable local PostgreSQL only; no external, shared, Trust CI or production write.
- Producer handoff ruling: M2/M3 exact-base/head values remain producer-owned frozen values; M4 validates them and does not replace them with its implementation base.

## TDD cycles

Each vertical records its RED command/result before production source is added, then GREEN/refactor commands. Final real PostgreSQL and root verifier evidence is appended after the last product change.
