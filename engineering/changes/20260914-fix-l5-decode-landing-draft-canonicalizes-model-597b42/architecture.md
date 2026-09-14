# Architecture

The only production edit is in `decode_landing_draft` in `factory/src/adaptive_factory/landing_normalizer.py`. It verifies that the raw sections value is a list of 1..12 entries before iteration. For section objects with a list of at most 12 all-string items, it deduplicates and sorts by `json.dumps(item, sort_keys=True)`; default ASCII escaping deliberately matches `_sorted_unique` in the unchanged strict contract. Oversized, non-list, and mixed-type item values reach existing strict validation unchanged.

`StaticLandingSpecV1.from_facts` and `LandingSectionV1.from_dict` still enforce closed fields, safe text, byte bounds, NFC, paths, and canonical spec construction. Section ordering, source-owned facts, source references, spec digest construction, and schema bytes stay unchanged. The input seam tolerates item order/duplicates only; its output remains a canonical static spec.

The shared decoder serves both `HttpLandingNormalizer` and `CodexLandingNormalizer`, plus the HTTP probe. Restoring `LandingContractError` lets their existing error boundaries produce controlled outcomes and provider evidence without broadening catches. No API, persistence, retry, authentication, authorization, or transport change is needed.
