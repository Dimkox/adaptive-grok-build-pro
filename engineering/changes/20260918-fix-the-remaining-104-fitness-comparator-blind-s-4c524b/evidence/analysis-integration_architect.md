# Reference-resolution analysis — issue #104 continuation

## Finding

`_SchemaResolver` can resolve the two external file references in `factory/contracts/openapi/landing-failover.v1.json` because they are plain relative paths to declared `json_schema` records. It cannot resolve JSON Schema `$defs` references or general JSON Pointers: local references are accepted only for `#/components/schemas/<simple-name>` in OpenAPI documents; external paths reject `#` entirely. Also, `$defs` and `anyOf` are absent from `_SUPPORTED_SCHEMA_KEYS`. Therefore a one-keyword `anyOf` allowlist change does not safely close the observed path: recursively visiting the status schema reaches other unsupported constructs.

The resolver is appropriately fail-closed today. It rejects undeclared/external-to-inventory targets, unsafe path syntax, non-schema contract kinds, dangling references, cycles, excess depth and excess parse/comparison work. Those boundaries should remain intact.

## Repository-wide schema scan

I parsed all 27 `factory/contracts/jsonschema/*.schema.json` documents recursively (no files changed). They contain 261 `$ref` occurrences: 176 fragment-only JSON Pointers such as `#/$defs/digest`, 74 URI references with fragments (including declared `urn:adaptive-factory:...#/$defs/...` IDs), six plain relative-file references, and five bare declared URN references. This is not a hypothetical feature: local `$defs` pointers are common, and the factory bridge schemas rely on URN identity references.

The scan found these schema keywords outside the current allowlist:

| Keyword | Occurrences / documents | Consequence |
| --- | --- | --- |
| `$defs` | 17 / 27 | Must be treated as a bounded map of subschemas; otherwise local references cannot target the definitions and the definition-bearing documents are rejected. |
| `anyOf` | 10 / 3 | Appears in attempt status, provider observation, and failover result; must use the same conservative composition treatment as existing `oneOf`/`allOf`. |
| `format` | 11 / 7 | Every observed value is `date-time`. It is meaningful contract metadata and should be validated and compared conservatively for the currently needed closure. |
| `prefixItems` | 1 / 1 | Exists only in `operator-handoff-proposal.v1.schema.json`; it is outside the reference closure for this OpenAPI contract and should remain unsupported in this bounded fix. |

Other encountered keywords are already in the allowlist. The scan did not try to claim support for all JSON Schema 2020-12: for example, `not`, `contains`, and dynamic references are not used in these 27 documents and should remain rejected unless separately designed and tested.

## Exact dependency closure for the failing OpenAPI contract

Starting from the two response schemas referenced by `landing-failover.v1.json`, the declared schema-reference closure is:

1. `landing-backend-capability.v1.schema.json` (no references).
2. `landing-attempt-status.v1.schema.json`.
3. `landing-input.v1.schema.json`.
4. `landing-site-artifact.v1.schema.json`.
5. `landing-provider-observation.v1.schema.json`.
6. `landing-provider-evidence.v1.schema.json`.
7. `landing-provider-evidence.v2.schema.json`.

The status document has four `anyOf` nullable fields and references input, artifact, and observation. The observation document uses `anyOf`, `oneOf`, `allOf`, and `if`/`then`, and references both evidence versions. The input and evidence documents use `$defs` and local pointers; input and both evidence versions use `format: date-time`. Thus an adequate change for the actual closure must cover **`anyOf`, `$defs` plus local JSON Pointers, and the observed `date-time` format**. The other existing compositions are already recognized. Supporting `prefixItems` is unnecessary for this defect.

All seven target paths appear in `architecture/system.yaml`, so the current inventory boundary can resolve them without broadening authority.

## Bounded implementation design

1. **Keep reference authority inventory-bound.** Resolve relative file references only against the current contract's normalized POSIX parent and only to an exact declared inventory record of kind `event`, `json_schema`, or `signed_payload`. Reject URL schemes, network access, query strings, percent-encoded paths, backslashes, absolute paths, path escape, and unknown targets.
2. **Add strict JSON Pointer fragments.** Accept only empty fragments or `#/...` fragments. Decode pointer segments with RFC 6901's exact `~0` and `~1` escapes, reject malformed escapes and non-canonical/unsafe input, and walk only parsed JSON values (never filesystem paths). For URI-form references, first bind the URI to an exact declared record path or unique exact document `$id` in the inventory; do not fetch URIs or resolve arbitrary URI bases. A pointer target used as a schema must be an object. Keep existing OpenAPI component references working as the `#/components/schemas/...` case of the same pointer mechanism.
3. **Bound and validate the definition graph.** Add `$defs` as an object whose keys are safe strings and whose values are schemas; preflight every definition recursively under the existing `MAX_DEPTH` and shared `MAX_PARSED_NODES` budgets. Resolve local and external pointers with a canonical identity `(target record path, decoded pointer)` so alias spellings cannot bypass cycle checks. Preserve preflight of the entire external document and inventory identity checks.
4. **Support only needed compositions and format.** Add `anyOf` to the existing 1–16 object-branch composition check and recurse into every branch. Validate the required `format` shape as a bounded string keyword; for the current closure accept the observed `date-time` value with `type: string`, and compare format changes as `changed_constraint`. Do not attempt logical equivalence between composition rewrites: as for `oneOf`/`allOf`, a changed canonical composition remains incompatible, and unchanged same-position branches are compared recursively. Keep the current conservative semantics for reordered or restructured branches.
5. **Keep reference objects contextual.** This change is for schema `$ref` only. Do not begin accepting arbitrary OpenAPI Reference Objects for parameters, responses, headers, or Path Items; current OpenAPI validation does not model their semantics, and they are not needed by `landing-failover.v1.json`'s two schema references.

This design removes the observed `unsupported_openapi_construct` through the actual dependency closure while retaining fail-closed behavior for undeclared documents, unsupported schema keywords, malformed pointers, cycles, and resource-limit exhaustion. Do not whitelist the digest/contract, skip the referenced schemas, or convert `unsupported` into a pass.

## Focused evidence to require from implementation

- The actual OpenAPI inventory compared with itself is supported in both directions and reaches the referenced attempt-status and capability schemas.
- Each reference family in the closure is exercised: OpenAPI component pointer, external relative path, local `#/$defs/...`, and an exact declared-ID reference if that form is supported.
- Malformed pointer escapes, dangling/non-object targets, undeclared files/IDs, path traversal, external URLs, cycles, depth overflow, and node-budget exhaustion remain rejected/unsupported.
- A changed `anyOf` branch or changed `date-time` format cannot produce a compatibility pass; unchanged branches still expose nested directional property/type checks.
- Existing producer object-enum behavior from #112 remains unchanged.
- The other unsupported `prefixItems` schema remains fail-closed; this fix must not silently imply complete JSON Schema support.
