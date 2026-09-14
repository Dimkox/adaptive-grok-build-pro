# Requirements

- R1 / AC-001: Permutations and duplicates within at most 12 raw string items produce the same canonical item tuple and spec digest, using the strict contract's JSON ordering for multilingual and escaped strings.
- R2 / AC-002: `sections` remains a list of 1 through 12 entries, with section order preserved. All other JSON container types raise `LandingContractError("sections")`; item lists over 12 entries remain rejected even if their values repeat.
- R3 / AC-003: The shared HTTP/Codex decoder keeps strict item types, text limits, Unicode normalization, prohibited-content checks, and closed fields. Direct `StaticLandingSpecV1` construction still rejects unsorted or duplicate items.
- R4 / AC-004: HTTP normalization returns `normalized` for a valid mixed-language unsorted response. Malformed section containers return `needs_human/http_outcome_unusable` with bound evidence; the service persists that reason and digest, and Codex returns `needs_human/invalid_model_output` with evidence.
- INV-001 / FORBID-001: Canonicalization only changes item order and removes repeated strings inside the original input bound. It must not drop invalid values, bypass count limits, weaken contract/schema checks, or add a caller catch-all.
- R5 / AC-005 (verification recovery): Use valid serialized PDFs to exercise the unchanged worker page limit: 101 blank pages return `pdf_page_limit`, 100 blank pages reach content validation and return `pdf_empty_or_scanned`; preserve the independent corrupt-PDF rejection test.
