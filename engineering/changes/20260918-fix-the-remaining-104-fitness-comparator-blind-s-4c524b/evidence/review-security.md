# Security review — #104 final comparator tree

**Verdict: PASS.** Reviewed the actual final diff in `.grok-stack/adaptive_grok/architecture.py` and the #104 requirements. No product source was changed and no full verifier was run.

## Findings

- Reference resolution remains inventory-only. `_SchemaResolver.resolve` maps either an exact declared `$id` or a checked relative path to an in-memory `ContractRecord`; it has no URL client or filesystem read path. `_relative_path` rejects absolute paths, URI schemes, encoded paths, query strings, backslashes, and path escape, and the record kind is restricted to declared contract types.
- JSON Pointer traversal validates `~0`/`~1`, rejects percent escapes and malformed/dangling pointers, bounds each traversal step through the shared work counter, and only returns object schemas. Ambiguous schema IDs, cycles and invalid references fail closed. Public `compare_contracts` catches parsing and traversal failures and reports `unsupported`.
- Composition analysis has explicit depth/node limits, caps each union at 16 branches and candidate comparisons at 256, and returns unknown/unsupported when inclusion cannot be proven. It does not infer compatibility from a single matching pair or perform date-time instance validation.
- Numeric canonical keys distinguish booleans from numbers while treating mathematically equal integer/float JSON numbers equally. Numeric and string constraints are only applied to their relevant instance types; mixed-type cases remain unknown where the bounded proof cannot establish inclusion.
- `git diff --check` passed.

## Robustness note

The private pointer resolver uses `str.isdigit()` before `int()` for array indexes. Some Unicode characters satisfy `isdigit()` but are not accepted by `int()`; a direct call to this private resolver with such an index raises `ValueError`. The public `compare_contracts` boundary catches `ValueError` and returns `unsupported`, so this does not escape as an API exception or permit traversal outside the in-memory document. Restricting indexes to ASCII decimal digits would make the private helper's failure mode more uniform, but I found no security bypass or fail-open compatibility path from it.
