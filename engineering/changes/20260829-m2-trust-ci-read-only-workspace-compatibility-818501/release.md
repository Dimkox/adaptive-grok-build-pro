# Release plan — M2 Trust CI read-only workspace compatibility

## Deployment

This is repository source only. No Trust CI deployment, policy/holdout/image update, service action, push, merge, release, or external write is part of this implementation handoff.

## Feature flags / staged rollout

No feature flag is needed. The final reviewed-tree disposable commit passed the local digest-pinned read-only evaluation at 404/404, and the final code, test, security, and release reviews all pass locally. The PR exact-SHA external App check remains a separate merge gate.

## Metrics and alerts

- Targeted architecture, package, and receipt-clone regression status.
- Source-tree mutation check in the pinned runner.
- Existing archive digest/sidecar determinism checks.
- External-symlink exclusion, replacement-race rejection, and bounded streaming checksum regressions.
- Early and final-window temporary-name swap rejection, new/existing output mode compatibility, symlink-root compatibility, controlled capability absence, and descriptor-cleanup regressions.
- Private output-parent enforcement and relocation/path-swap cleanup through one held parent descriptor.
- Canonical ancestor rename-authority enforcement, private missing-parent creation, and exclusive verified sidecar replacement across regular/non-regular pre-existing names.
- Frozen M2 handoff digest equality with the canonical architecture summary after the approved rules change.
- Historical remediation-3 digest-pinned runner: 391/391 PASS in 227.409 seconds.
- Final reviewed-tree remediation-5 digest-pinned runner: 404/404 PASS in 230.283 seconds on disposable commit `ec341a22874872e50b2e73f05e6934c816f6fcc6`; this is local evidence, not App-owned merge authority.

## Go/no-go criteria

- **Local source-ready:** remediation-5 regressions, focused package suite, Ruff, Bandit, diff-check, architecture fitness, spec validation, final independent and release reviews, and the fresh pinned remediation-5 suite all pass locally.
- **No-go:** any source mutation, unsafe/unbound output parent, source/temp symlink follow, identity/digest race acceptance, unbounded checksum, output mode regression, fd leak/raw validation error, wildcard/persistent Git trust, host-config dependency, archive compatibility regression, unbounded architecture rule, missing architecture/governance/security approval, or `trust-ci/**` change.
- **Local evidence complete:** fingerprint-bound verification and code/test/security/release receipts are recorded with PASS/MATCH status, and `state.json` is `ready`.
- **Not yet complete:** the PR exact-SHA App check, signed architecture/governance/security approvals, push, merge, and deployment.
