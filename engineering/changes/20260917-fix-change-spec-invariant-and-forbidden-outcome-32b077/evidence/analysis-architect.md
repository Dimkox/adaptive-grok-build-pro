# Architect analysis — issue #125

`schemas/change-spec.schema.json` requires evidence arrays but permits empty arrays. `_semantic_errors()` rejects empty evidence at gate only for AC. Fix shared AC/INV/FORBID gate semantics and preserve coverage metadata/findings on invalid specs. Existing specs may newly fail and need migration/remediation; do not expand into proving a referenced test name exists (#117). Trust CI signed coverage and receipt `criterion_ids` are AC-specific compatibility contracts; preserve their v1 semantics or version explicitly.
