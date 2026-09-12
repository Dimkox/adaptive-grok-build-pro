# Implementation plan

1. Retain benchmark/source inventory and dependency/isolation analyses; characterize the missing normal-runner feature with a failing subprocess test.
2. Implement closed opt-in/worker controls, the scoped invocation helper, fresh coverage ownership and bounded process cleanup.
3. Wire normal Core verification and scoped requirements/Make setup, preserving generic consumer and other-suite behavior.
4. Run focused failures and compatibility tests, then exact-tree serial/parallel coverage and full grok_verify pr.
5. Freeze implementation, obtain independent code/test review from the two user-approved available agents, record actual evidence and deliver the priority branch through a PR and fresh external Trust CI.

- Complete the original Trust CI recipe with a module entrypoint and Make target; reuse bounded process/tooling primitives while isolating imports and retaining PG skip semantics.
- Add missing runner-image source pins and the existing pin regression, then include all final changes in verification and both independent reviews.

## Delivery split after architecture verification

`FIT-TRUST-CI-SEPARATION` rejects a PR combining local implementation with `trust-ci/**` source mutations. Move the three runner package pins and the existing test_ops pin assertion into a separate bootstrap branch/PR; this acceleration branch has no Trust CI source changes. Its Make target still invokes the existing Trust test suite with loadfile. Companion image deployment remains independently operated, and actual signed scopes come from the external exact-head check.
