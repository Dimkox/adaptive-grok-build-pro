# Requirements — Fix the M3 branch after accepted M2 changed: merge exact M2 head 022411b05924618cfde0cb97b8c8aff4955e6013 into M3, resolve integration conflicts without changing M3 requirements, add or update regression tests if needed, run verification and reviews, and prepare PR #11 for fresh exact-SHA Trust CI; no external writes without exact delegated grants.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] The final commit has the preserved M3 head and exact accepted M2 `022411b05924618cfde0cb97b8c8aff4955e6013` as its two parents, and the M2 SHA is an ancestor.
- [ ] The merged architecture rules retain M3 governance ownership and handoff fitness plus M2's finite `10820` changed-line budget.
- [ ] M2 read-only packaging, command-scoped Git trust, source-invariance, and bounded fail-closed zombie-only cleanup regressions pass unchanged.
- [ ] M3 governance schemas, loaders, candidate-only lifecycle, projections, handoff binding, architecture/governance fitness, and receipt invalidation regressions pass.
- [ ] Architecture/governance evidence and all local receipts are freshly derived for the final tree; historical receipts are not edited or reused.
- [ ] Full `python3 scripts/grok_verify.py --mode pr` and route-selected code, test, and security reviews pass on one final fingerprint.

## Failure and edge cases

- An old M3 exact-head handoff or receipt must be rejected after the merge changes the tree.
- Whole-history architecture status may differ from isolated-diff applicability; tests assert invariant fields rather than a branch-history-dependent global status.
- A live, unknown, or unclassifiable process group after SIGKILL remains a hard cleanup failure; only provable all-zombie groups preserve the original command error.
- No new public contract, external integration, or runtime behavior is introduced by conflict resolution.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: current canonical `governance/rules.json` contents; no rule activation is created by this change.
- Canonical-example deviations and evidence: none.
- Intentional debt created, repaid, or accepted: none.

## Non-functional requirements

- Security: preserve fail-closed procfs classification, no-follow/source-invariance protections, and the independent Trust-CI authority boundary.
- Reliability: deterministic merge provenance, exact-base binding, and idempotent local verification.
- Performance: no runtime impact; architecture change ceiling remains `10820`.
- Observability: exact parent SHAs, final fingerprint, verifier receipt, and review receipts provide bounded proof.
