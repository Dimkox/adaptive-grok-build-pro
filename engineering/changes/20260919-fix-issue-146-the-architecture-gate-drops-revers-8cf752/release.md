# Release plan — issue #146

## Deployment

Library change inside the repository's own gate code (`.grok-stack/adaptive_grok/`). It ships with the next toolchain
release; nothing is installed, started or migrated, and no contract bytes change. Delivery is by pull request and the
App-owned exact-SHA check, as always in this repository.

Sequence: commit → `python3 scripts/grok_verify.py --mode pr` on the clean head → route-selected reviews → receipts →
push `fix/contract-closure-id-refs` → open PR → wait for `adaptive-trust-ci/verified@<policy-sha12>` on that exact
head → merge only as a separately delegated action.

## Feature flags / staged rollout

None. The change is a strict widening of verification scope; a partial rollout would reintroduce exactly the
silence the fix removes. The behaviour is pinned by tests rather than gated by a flag.

## Metrics and alerts

- `SIG-001` — closure target→dependent pairs: **10 → 27**, zero edges lost (measured, `controller-verification.md`).
- `SIG-002` — comparator differential: **0 differing lines of 555** between `d871ea6` and the delivered head.
- Expected new symptom after merge: pull requests touching `M7-OPERATOR-HANDOFF-V1`, `M7-PREDECESSOR-BRIDGES-V1` or
  `M7-TASK-EVIDENCE-V1` may fail `contract_compatibility` with `unsupported compatibility semantics` on
  `M7-READY-BUNDLE-V1`. That is restored verification, not a regression, and is named in the PR description.

## Go/no-go criteria

Go: focused suites green; full root discovery green; `git diff --check` clean; ruff clean; differential 0 lines;
gate `RESULT: PASS`; verification + code/test/security receipts bound to the delivered head fingerprint; external
check SUCCESS on that same head.

No-go: any lost closure edge, any changed comparator verdict, any weakened existing assertion, or an unreviewed
`ArchitectureError` escaping `evaluate_fitness` for a reason outside the ambiguity case.
