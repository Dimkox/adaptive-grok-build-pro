# Integration compatibility analysis — M3 restack on accepted M2

Route: 41eadaeae674  
Change: 20260831-fix-the-m3-branch-after-accepted-m2-changed-merg-41eada  
Method: read-only repository/history analysis; this report is the sole write.

## Decision

**Restack by a true merge of exact M2 head 022411b05924618cfde0cb97b8c8aff4955e6013 into M3 head d4cc01fe8d6ec82cce93106191774fc32e8dbb46, preserving both branch histories and regenerating all exact-head evidence. Do not cherry-pick/squash M2 fixes or relax M3 handoff validation.**

The merge base is 635c9ddf2d63c1ea823074106976a8f3de6299a9; neither M2 nor M3 is an ancestor of the other. M2's accepted head is itself a merge commit whose first parent is 9493741, so the restack must retain both parents/lineage for accurate review and PR ancestry.

## Blocking exact-base risk

The active route declares base 1c06299894279a88b881defa3f19b004fa742223, but that commit is not an ancestor of either current M3 or accepted M2; their merge base with it is 069fe822. It is unsuitable as the exact comparison base for a stacked M3-on-M2 PR. Before final verification/receipts, regenerate or correct the route/change binding so the selected stack base is exact M2 022411b and the eventual merge commit is the exact head. Otherwise architecture/governance evidence can be valid for an unrelated divergent diff while stale route-base assertions fail or misdescribe the PR.

Any merge resolution produces a new SHA. All prior M2/M3 local receipts, architecture evidence, governance handoffs, review reports, and external check results are stale for that SHA even when source bytes are retained.

## Contract and authority compatibility

| Boundary | Required post-merge rule | Failure mode if skipped |
| --- | --- | --- |
| M2 architecture → M3 governance | Re-derive M2 architecture evidence at exact merged head/base, then make M3 consume that exact digest/base/head. | M3 must reject mismatched architecture digest, evidence digest, base, or head. |
| M3 handoff | Preserve closed v1 six-field schema: version, governance digest/evidence digest, architecture digest, exact base SHA, exact head SHA. | Never retain a pre-merge handoff or weaken schema/integrity validation to accept it. |
| Generated architecture | Resolve model/rules first, then regenerate all Mermaid diagrams; generated files are projections, not hand-edited authority. | Diagram drift or digest/fingerprint mismatch blocks architecture/governance verification. |
| M2 public contracts | M2 adds packaging/workspace compatibility and Trust-CI cleanup behavior but no OpenAPI, JSON schema, event, DB-migration, or public API change. | Do not version/migrate public contracts merely for the restack; test existing inventory unchanged. |
| Trust CI | External Check Run remains App-owned and exact-head/policy-epoch bound. | A passed check/attestation on M2/M3 old SHA cannot satisfy the restacked merge SHA. |

M3 GovernanceHandoffV1 is intentionally strict: architecture digest and exact base/head are digest-bound inputs, not narrative claims. Preserve the M3 check that governance evidence matches the completed architecture binding; resolve any new architecture digest by recomputation only.

## Actual conflict set and safe priority

Git merge-tree identifies six changed-in-both files:

1. architecture/rules.yaml — highest priority. Take accepted M2 finite FIT-BOUNDED-ARCHITECTURE-CHANGE.max_changed_lines 10820 only with its measured-delta tests and M2 requirements/digest update. Do not retain old 10000 if it makes accepted M2 untestable, and do not raise it further for M3 without measured justification.
2. tests/test_architecture_fitness.py and tests/test_change_receipts.py — combine both suites rather than selecting either side. M2 command-scoped Git trust/read-only packaging/receipt clone regressions and M3 frozen M2-to-governance binding regressions cover separate failure classes. Preserve fail-closed exact-state assertions.
3. README.md — retain M3 governance/M4 dependency documentation and add M2 secure read-only packaging behavior exactly as implemented. Do not claim deployment, release, external Trust-CI activation, or a changed public API.
4. decisions.md and mistakes.md — append both histories chronologically; neither set is a substitute for machine-derived handoff authority. Retain M3 provenance/evidence lessons and M2 command-scoped trust, descriptor safety, procfs fail-closed, and test-isolation lessons.
5. engineering/changes/20260826-m2-executable-architecture-015603/requirements.md is auto-mergeable but its recorded architecture/rules/composite digests must reflect accepted M2 source only. Do not update historical M2 evidence to the M3 merge digest; write new restack evidence for the new head.

Resolve code/tests/models before docs/history. Never resolve a test conflict by dropping either branch's regression, and never adjust an architecture budget, adoption record, M2 requirements digest, or handoff schema merely to make verification pass.

## Required exact checks after merge

1. Confirm merge parents are exact M3 d4cc01f and accepted M2 022411b; confirm PR base is M2, not main or stale route base.
2. Validate strict typed change spec and ensure scope is restack/conflict resolution. The current package is a generated empty template, so it cannot provide completed acceptance/invariant authority.
3. Run M2/M3 focused regressions: architecture-model, architecture-fitness, change-receipts, governance, governance-fitness, installer/structure/verification-doctor tests, plus M2 Trust-CI workspace and packaging tests affected by merged paths.
4. Recompute/validate architecture model, drift, exact diff/fitness, and generated diagram check on merged commit. Then build governance handoff from rederived architecture evidence and verify schema closure plus exact base/head/digest equality.
5. Run python3 scripts/grok_verify.py --mode pr only on final stable merge tree. Record fresh fingerprint-bound verification and all route-selected code/test/security review receipts after it; changes after review invalidate them.
6. Open/update stacked PR and require deployed GitHub App-owned adaptive-trust-ci/verified@<policy-sha12> Check Run for exact restack SHA. If deployed policy requires a signed scope for touched paths, wait for it. Local grants/receipts cannot substitute.

## Trust-boundary and external-system ruling

This restack has no new HTTP endpoint, webhook/event producer, schema, authentication method, external adapter, queue, deployment, systemd action, or production write. Keep existing M2 Trust-CI worker/runner separation and source-mutation/exact-SHA checks intact. Do not read credentials or alter deployed policy, holdout, images, database state, GitHub App configuration, branch protection, or external attestation while resolving this repository merge.

## Sources inspected

- Active route and change package.
- Git ancestry/diff/merge-tree for 635c9dd, 022411b, d4cc01f, and route base 1c062998.
- M2 architecture contracts/rules and M3 governance handoff/schema, receipts, verification, architecture/governance tests.

