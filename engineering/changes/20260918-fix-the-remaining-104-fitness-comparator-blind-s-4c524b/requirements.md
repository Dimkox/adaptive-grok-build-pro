# Requirements: complete the technical #104 comparator fix

## Acceptance criteria

- [ ] `AC-001` — Given the declared landing contract inventory, when the failover OpenAPI is compared to itself or a referenced capability schema receives a metadata-only edit, then the comparator resolves the complete current dependency closure and does not report `unsupported_openapi_construct` solely for existing `anyOf`, `$defs`, JSON Pointer, or `date-time` forms.
- [ ] `AC-002` — Given supported `anyOf` alternatives, when compared in either direction, then the result is `compatible` only if the source union is proven included in the destination union; reordered or duplicate branches do not alter the result, and partial/ambiguous coverage never yields `compatible`.
- [ ] `AC-003` — Given malformed, dangling, undeclared, ambiguous, cyclic, or out-of-budget references/unions, when analyzed, then the comparator fails closed as `unsupported` without external fetching or filesystem escape.
- [ ] `AC-004` — Given a schema with `format: date-time`, when the format is unchanged it is supported as contract metadata; when it changes the comparator reports semantic drift. It does not claim to validate date-time instance strings.
- [ ] `AC-005` — Given an unrelated unsupported keyword such as `prefixItems`, when analyzed, then it remains `unsupported`.

## Invariants

- [ ] `INV-001` — The only `compatible` outcome for a directional `anyOf` comparison is backed by a proof of language inclusion; failure to prove inclusion stays `unsupported`.
- [ ] `INV-002` — Reference authority stays within the current document or an exact declared contract-inventory record; network and undeclared filesystem access remain impossible.
- [ ] `INV-003` — Reference traversal, canonicalization, branch comparisons, depth, and parsed-node work share explicit limits; cycles remain unsupported.

## Forbidden outcomes

- [ ] `FORBID-001` — Do not change producer-output policy, `architecture/rules.yaml`, deployed Trust CI, or declare new profile facts in the capability contract.
- [ ] `FORBID-002` — Do not treat `anyOf` as positional, exclusive (`oneOf`), or compatible merely because one pair of branches matches.
- [ ] `FORBID-003` — Do not imply complete JSON Schema support or whitelist unrelated keywords.

## Non-functional requirements

- Security: no remote reference retrieval; strict inventory identity, pointer parsing, cycle rejection, and bounded work.
- Reliability: unknown schema-language relationships remain unsupported and fail closed.
- Performance: retain `MAX_DEPTH`, `MAX_PARSED_NODES`, 16 branches per union, and at most 256 candidate branch-pair checks per union, all charged to shared work limits.
- Observability: findings distinguish proven incompatibility from unsupported analysis without altering existing policy identities.
