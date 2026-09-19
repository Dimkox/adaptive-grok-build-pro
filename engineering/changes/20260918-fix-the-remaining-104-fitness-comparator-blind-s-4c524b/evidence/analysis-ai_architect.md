# AI architecture risk analysis — bounded `anyOf` support for #104

## Finding and scope

The unsupported referenced schema is `factory/contracts/jsonschema/landing-attempt-status.v1.schema.json`, whose nullable fields use `anyOf`; the referenced `landing-backend-capability` schema itself already passes the current subset. JSON Schema `anyOf` denotes the union of branch languages: branch order is irrelevant, overlapping branches are allowed, and duplicate branches do not change the accepted set. Treating it as a positional list or importing `oneOf`'s exclusive-match semantics would be wrong.

## Recommended compatibility contract

Use a three-outcome proof discipline: report `compatible` only where the supported subset proves the required language inclusion; report `incompatible` where a supported comparison proves drift; return `unsupported` whenever the relation cannot be established. For a consumer, require `L(base) ⊆ L(head)`; for producer outputs require `L(head) ⊆ L(base)`. These are the same directional obligations as the existing comparator, applied to union languages.

For a bounded, low-risk implementation, first canonicalize each `anyOf` as an unordered set of canonical branch schemas (deduplicate branches; charge every visit/ref resolution to the existing shared work budget). This gives exact handling of reordering and duplicate branches. For directional inclusion, a sufficient—not complete—proof is that every source branch is wholly covered by at least one destination branch, using a tri-state branch-inclusion routine. If that routine cannot prove coverage, return `unsupported`; do not infer inclusion from pairwise partial overlap, matching array position, matching branch counts, or a changed-constraint finding alone. Detect a proven counterexample only where the supported subset can establish it; otherwise stay `unsupported` rather than overstate incompatibility.

The target nullable union can be handled by canonical branch-set equality for unchanged schemas and by direct, bounded inclusion for simple disjoint/identical branches. If implementing a sound branch-inclusion routine is too large for this fix, safely whitelist only exact unordered-set equality for `anyOf` and return `unsupported` for changed unions. That preserves fail-closed behavior but does not claim general union-difference analysis.

## Bounds and reference behavior

- Require a non-empty array of at most 16 object-schema branches, matching existing composition limits. Reject malformed members and any branch that contains an unsupported keyword.
- Keep `MAX_DEPTH` (64) and the resolver's shared `MAX_PARSED_NODES` (100,000) budget for traversal, canonicalization, and comparison. Charge branch-pair attempts too; also impose a bounded per-union comparison budget (at most 16×16 candidate pairs, included in the global budget) to prevent nested unions from multiplying work unexpectedly.
- Resolve only declared, safe local/external `$ref`s through the existing resolver and the corresponding base/head inventory. A reference cycle, dangling/ambiguous reference, cross-inventory mismatch, depth overflow, or work exhaustion remains `unsupported` (or the existing fail-closed malformed result); never truncate a branch list or assume a recursive fixed point.
- Keep recursive-reference support out of scope. `anyOf` can amplify recursive schemas and requires fixed-point reasoning plus memoization keyed by schema identity and comparison direction. The current resolver deliberately rejects cycles; retain that invariant unless a separate design proves bounded semantics.

## Hazards and required tests

1. Reordered branches and duplicate branches must preserve the union and compare as equivalent; overlapping branches must not be rejected as they would under `oneOf`.
2. A nullable union (`{"anyOf":[{"type":"null"},{"$ref":"..."}]}`) must retain both branches and resolve the ref in the correct record/inventory.
3. Add directional cases: adding a branch widens an input consumer's accepted set (compatible in that direction) but can widen producer output (incompatible); removing a branch has the reverse result. Include same-count replacement and changed nested branch constraints to catch positional-comparison false passes.
4. Include ambiguous coverage (e.g. a broad source branch partially covered by multiple narrower destination branches): it must be `unsupported` unless the implementation proves the union coverage, never `compatible` based on a single successful pair.
5. Verify malformed/empty/over-16 unions, nested-depth overflow, global/pair-work exhaustion, missing refs, and cycles fail closed. Ensure canonical `anyOf` comparison and any newly supported branch traversal do not bypass resolver accounting.
6. Preserve existing producer-output policy and profile facts. Do not convert arbitrary changed unions into `compatible`, and do not silently skip `anyOf` branches in meaning/description extraction if the accepted subset now traverses those branches.

## Implementation risk

The main risk is confusing structural similarity with set inclusion. Branch-wise positional comparison or “any pair matches” is unsound for unions with overlap or coverage split across branches. The safest small change is unordered canonical-set equality plus fail-closed results for non-identical unions; broader directional proof should be added only with explicit tri-state inclusion logic and the adversarial cases above.
