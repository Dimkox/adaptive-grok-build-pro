# Test plan

- Table-driven gate validation: AC/INV/FORBID empty evidence each fail; each with evidence passes; draft mode remains descriptive.
- Mixed-category coverage reports exact totals and missing IDs by category.
- AC-only attestation adapter retains the exact Trust CI v1 key shape and passes the checked-in strict v1 coverage normalizer.
- Draft API accepts empty INV and FORBID evidence while gate mode rejects both.
- Summary output reports category-aware coverage and an all-category aggregate while preserving the historical summary fields.
- `change-spec` verifier emits a failing result and actionable finding for unmapped INV and FORBID criteria, while retaining coverage metadata.
- Trust CI metadata extraction / normalization tests establish backward compatibility for existing AC-only signed payloads and ensure any supported expanded projection has stable category-aware IDs.
- Run targeted spec and Trust CI tests, then `python3 scripts/grok_verify.py --mode pr` and route-selected reviews.
