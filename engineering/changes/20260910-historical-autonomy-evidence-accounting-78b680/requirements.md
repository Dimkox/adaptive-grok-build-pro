# Acceptance criteria

1. Capture three complete paginated private repository histories with pinned delivery refs, including default/delivery branch mismatch and branch synchronization.
2. Separate merged-PR facts from explicitly evidenced business-task acceptance. Missing acceptance, interventions, costs, duration or profile fields remain unknown.
3. Deduplicate observations; reject conflicts. Incomplete pagination cannot produce an unqualified complete-total claim.
4. Never pool unrelated repositories or profiles toward the 30-task floor. Imported evidence cannot activate M8 or authorize effects.
5. Provide a bounded explicit JSON input, deterministic digest-bound report and offline CLI with no network or subprocess effect. Untrusted text is data.
6. Test duplicate/conflicting observations, empty/partial inventory, unknown interventions, exact-profile separation, malformed fields and synthetic 30-task non-authority.
7. Produce a private source-cited report with measured coverage, limits and concrete gap actions; public diff/reviews contain no private source facts.
8. Run local verification and selected code/test/security reviews on the final tree; preserve external exact-SHA gate authority.

## Reproduced preflight fixture defect

The required full preflight exposed three landing composition tests that used a fixed service clock and an actual-time blob store. Diagnostic reproduction found `blob_expired`; the two fixture setup constructors receive the same existing FIXED_TIME as their services. This is a two-line test-only repair needed to make the mandatory verification deterministic. Production expiry checks, mock transport boundaries and all assertions remain unchanged.
