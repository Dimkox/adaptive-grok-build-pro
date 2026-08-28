# M3 Task 8 architecture repair review

Status: **CHANGES_REQUIRED**

Reviewed product commit: `d31825e` (`406ab224..d31825e`)

## Findings

### HIGH — Persisted M2 base fingerprint is truncated and does not bind the exact base

- Location: `engineering/changes/20260826-m3-m9-production-delivery-continuation-355689/route.json:22` and the synchronized runtime route.
- Evidence: `base_commit` is the reachable immediate reviewed M2 commit `635c9ddf2d63c1ea823074106976a8f3de6299a9`, but the stored fingerprint has 63 characters: `6b4212f06a6c095db1a9e9c6eeb8c51d731dfa900e596bc915f98c012a4ac59`. `tree_fingerprint()` for a clean exact commit is SHA-256 of the HEAD identity and yields the 64-character `6b4212f06a6c095db1a9e9c6eeb8c51d731dfa900e596bc915f98c012a4ac59c`.
- Impact: the durable route cannot prove the base fingerprint it claims, so exact stacked provenance and any consumer validating 64-hex fingerprints are broken even though the base commit itself is correct.
- Required repair: derive rather than transcribe the clean exact-M2 fingerprint, update both active and durable route state consistently, and add a length/value regression bound to `base_commit`.

### HIGH — Frozen-schema digest exception permits incompatible weakening against a different schema

- Location: `.grok-stack/adaptive_grok/architecture.py:916-918` and `:1510-1515`.
- Evidence: `_SUPPORTED_CLOSED_SCHEMA_DIGESTS` exempts each input independently from unsupported-key rejection. Starting from the whitelisted governance handoff schema, removing `$defs`, all `$ref` constraints, and `const` produces a supported but substantially weaker schema. `compare_contracts(base, weakened, "consumer_accepts_old")` returns `CompatibilityResult(status='compatible', reasons=())` because the directional comparator ignores the unsupported frozen branches.
- Impact: the exception intended only to allow exact self-comparison weakens contract policy for changed pairs and can classify removal of digest/length/version constraints as compatible.
- Required repair: scope the exception to an exact identical pair whose two canonical digests equal the reviewed frozen digest. Any changed comparison involving unsupported `$defs`, `$ref`, `const`, `oneOf`, or aliases must remain `unsupported`. Add the demonstrated frozen-to-weakened regression alongside the self-comparison case.

## Passing bounded evidence

- Exact new tests: 2/2 passed for nullable type-array semantics and frozen self-comparison.
- Nullable arrays are non-empty, unique, limited to seven known types, compared as deterministic sets, and directional consumer/producer semantics are correct.
- Existing unknown type, duplicate type, non-string type, empty type list, and `$ref` probe remain unsupported outside the digest exception.
- Exact-M2 worktree fitness: overall `pass`; `code_budget` pass; `contract_compatibility` pass.
- Architecture summary: pass; drift: `ok=true`, zero findings.
- Ruff: pass; Bandit: pass; `git diff --check 406ab224..d31825e`: pass.
- `635c9dd…` is an ancestor of `d31825e` and is labeled as the exact M2-A review-evidence commit.

No broad suite or `grok_verify` was run. The two findings above block approval because both affect exact evidence/policy semantics requested by this review.
