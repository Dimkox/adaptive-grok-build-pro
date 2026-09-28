# Requirements — issue #218 clean squash delivery

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Acceptance criteria

- AC-001: Given base `cb9af4073...`, when the verified source is squash-merged, the staged pre-package tree equals source tree `0914b5d6...` byte-for-byte.
- AC-002: Given the delivery package and bounded repairs are added, every delta from source `68dfc70c...` is confined to this package and the thirteen paths enumerated in `architecture.md`: the historical eleven-path repair contour plus the requested `README.md`/`START_HERE.md` dated-tag corrections.
- AC-003: Generated empty bullets are whitespace-clean; receipt fixtures use the closed-scope helper. Authorized post-source verifier/util security repairs below extend behavior without weakening validation.
- AC-004: Given the candidate's selected chain, fast secret and whitespace checks complete without exposing secret values; any incomplete coverage fails closed.
- AC-005: Given the high-risk route, the package records exact base/source/tree identities, observability, rollback, and the still-required verification plus four independent reviews.
- AC-006: Given the parallel issue #219 Trust CI lane, no `trust-ci/**` path is added or changed by this candidate.
- AC-007: Given a stored PASS scope, validation independently recomputes the selected graph, blobs, bytes, paths, worktree coverage, and findings and rejects every forged or incomplete claim.
- AC-008: Given inherited repository selectors, hostile configuration, or replacement refs, every selected-base, graph, object, and diff operation stays bound to the explicit repository with isolated configuration and replacement objects disabled.
- AC-009: Given symlink blobs, gitlinks, dirty symlinks, broken links, FIFOs, or a named-file replacement race, supported blobs are scanned and every uninspectable object fails closed.
- AC-010: Given a whitespace error on a secret-bearing line, the report retains bounded location metadata but never the offending line or secret value.
- AC-011: Maximum-monotone clean anchors preserve the established clean-insertion/legacy-bad-line cases under one shared comparison budget. Unequal surviving clean multiplicities inside a changed interval with bad lines are ambiguous and produce typed incomplete coverage, never a clean claim.
- AC-012: Endpoint objects pass metadata/type/per-blob/aggregate checks before any body retrieval. Dirty/untracked worktree scanning shares a path and byte budget; exhaustion prevents further reads and complete coverage, including independent scope recomputation.
- AC-013: Preliminary `--no-record` verification precedes independent reviews. Persist reports and finish tracked accounting, transition `ready`, amend the sole candidate, run final recording verification on clean exact HEAD, then record verification-bound review receipts and require read-only zero-gap status.

## Failure and edge cases

- A source/staged tree mismatch blocks the candidate.
- A source-relative delta outside the exact thirteen-path plus package contour blocks the candidate.
- Any secret-pattern match, whitespace defect, incomplete selected range, or changed source identity blocks the candidate.
- Missing analysis reports block commit preparation; missing verification/reviews block readiness.
- A dirty base, merge conflict, unexpected Trust CI path, or external action request requires a new bounded decision.

## Non-functional requirements

- Security: retain full-chain coverage and metadata-only diagnostics while applying the explicitly authorized fail-closed security repairs.
- Reliability: preserve source commits and branches; squash only in this isolated worktree.
- Performance: run the adversarial focused matrix before one coordinator-owned full preliminary verifier; return immediately on a reproduced blocking review finding and timebox the review wave.
- Observability: preserve historical source-projection evidence, exact current source-relative contour, metadata-only findings, resource-limit failures, commands/results, and final committed identity. Historical PASS evidence is not current completion authority.

## Governance

No governance authority changes. The App-owned external Trust CI check remains merge authority; local evidence cannot replace it.
