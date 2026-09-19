# Requirements

- Gate validation fails for an AC, INV, or FORBID with empty/missing evidence.
- Draft validation remains usable and reports category-aware missing coverage without claiming it passed a gate.
- `criterion_coverage()` accounts for all declared categories and reports per-category totals/mapped/unmapped IDs without losing the existing AC-specific attestation projection.
- Attestation callers use `attestation_criterion_coverage(spec)` to produce the exact AC-only Trust CI v1 payload shape; category-aware local coverage is not a signed envelope payload.
- `summarize_spec()` exposes category-aware totals/mapped/unmapped IDs and a clear all-category aggregate; historical count fields remain compatible.
- `change-spec` verification fails if any declared criterion is unmapped and preserves actionable finding IDs/categories plus coverage metadata on failure.
- Evidence reference existence/authenticity beyond current validation is out of scope.
- Existing AC-only Trust CI v1 payloads and signatures remain valid; local evidence does not become merge authority.
