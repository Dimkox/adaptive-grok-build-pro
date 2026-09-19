# Decoder diagnostic vocabulary — issue #152

- Route: `814ed9c452cd`; role: `docs_researcher`; source HEAD: `26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960`.
- Scope: local static source inspection only; no tests, provider/runtime/network calls, or application edits.
- Question: which decoder errors can be retained as a finite diagnostic without retaining model-supplied text?

## Evidence and reachable codes

- `factory/src/adaptive_factory/landing_contracts.py:50` gives `LandingContractError` a separate `.code`; its string combines code and detail.
- `strict_json_object` (`landing_contracts.py:147–177`) emits `invalid_json`, `json_too_large`, `duplicate_json_key`, `nonfinite_json`, `invalid_json_object`.
- `decode_landing_draft` (`landing_normalizer.py:465–502`) additionally emits `draft_fields` and `sections`, then reconstructs source-owned facts and calls `StaticLandingSpecV1.from_facts`.
- With a valid input digest, the remaining draft-reachable contract codes are `locale`, `direction`, `invalid_object`, `unknown_fields`, `missing_fields`, `section_kind`, `section_items`, `invalid_text`, `unsafe_content`, `cta_path`.
- These arise from `StaticLandingSpecV1` (`landing_contracts.py:361–397`), `LandingSectionV1` (`:289–305`), and helpers (`:56–108`, `:130–144`).
- Full direct `StaticLandingSpecV1.from_facts` validation also has `unsupported_version`, `site_identity`, `robots_policy`, `assets`, `source_claim_refs`, `asset_path`, `asset_media_type`, `invalid_identifier`, `invalid_digest`; `from_dict` additionally has `digest_mismatch` (`:399–405`).
- Those extra codes cannot originate from model fields through the current decoder with valid source input: schema/site/robots/assets/refs are reconstructed. An invalid caller-supplied input digest can produce `invalid_digest`, `invalid_identifier`, or `invalid_text`.

## Details that must not be retained

- `unknown_fields` joins arbitrary JSON keys (`landing_contracts.py:66`); `duplicate_json_key` includes the duplicated arbitrary key (`:162`). Either key may contain sensitive model text.
- `missing_fields` joins fixed schema names (`:68`). `invalid_object`, `invalid_text`, `unsafe_content`, `invalid_identifier`, `invalid_digest`, `unsupported_version`, and `digest_mismatch` details use fixed caller-supplied field/type names along this call graph.
- `nonfinite_json` interpolates the JSON parser token (`NaN`, `Infinity`, or `-Infinity`), not arbitrary free text (`:166–170`); still retain only its code.
- The other listed codes have no detail. Never serialize exception strings, args, causes, tracebacks, raw output, or offending values into the diagnostic.

## Bounded recommendation

- Explicit allowlist: `invalid_json`, `json_too_large`, `duplicate_json_key`, `nonfinite_json`, `invalid_json_object`, `draft_fields`, `sections`, `locale`, `direction`, `invalid_object`, `unknown_fields`, `missing_fields`, `section_kind`, `section_items`, `invalid_text`, `unsafe_content`, `cta_path`.
- For `LandingContractError`, accept only an actual string `.code` equal to a member of that set; emit a constant allowlisted token, never the exception message. This also rejects an unknown or non-string injected `.code`.
- `LandingProviderError` is a plain `RuntimeError` (`landing_provider.py:57`); recognize only its exact single string argument `draft_fields`. Do not parse arbitrary text or accept matching prefixes.
- Map every other caught decoder exception to one fixed fallback, e.g. `draft_validation_failed`; preserve `needs_human`, `http_outcome_unusable`, and category `draft` separately.
- The full-spec-only codes may safely be added deliberately, but are unnecessary for model draft diagnostics; avoid permitting every repository error code or any regex-shaped string.
- Existing defect adjacent to this scope: unhashable `direction`/section `kind` can raise `TypeError` at set membership (`landing_contracts.py:372`, `:293`); excessive JSON nesting can raise `RecursionError`. The present HTTP decoder catch (`landing_http.py:295`) does not catch either. Do not leak such messages if the catch is deliberately extended.
- Suggested offline evidence: two distinct known codes; secret-bearing unknown/duplicate keys; unknown `ValueError`/`LandingProviderError` strings; malformed/non-string `.code`; unchanged generic reason/state with real digest and reported usage retained.

## Carry-forward fact

Read only `.code` after exact membership validation: trusted error classes can contain untrusted detail, so exception type alone is not a redaction boundary. The parent should preserve this fact in the shared decision log when adopting the allowlist.
