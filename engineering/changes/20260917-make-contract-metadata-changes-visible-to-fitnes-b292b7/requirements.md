# Requirements — contract metadata fitness (#120)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Acceptance criteria

- [x] Root JSON Schema `title` and `description` changes produce distinct `changed_documentation` review finding.
- [x] Finding makes metadata-only diffs visible without mislabeling wire compatibility.
- [x] Structural-only and combined edits preserve current structural compatibility behavior.
- [x] Unchanged documents, current event semantics, route/receipt schemas, and deployed Trust CI remain unchanged.
- [ ] OpenAPI and nested annotation behavior are explicitly out of scope.

## Failure and edge cases

- Metadata value changes to a different string, including removal and addition.
- Structural change in the same diff still yields the existing directional compatibility finding.
- Unsupported schema remains unsupported; metadata finding must not mask preflight failure.
- Unchanged and semantically equivalent raw JSON ordering remains governed by existing canonicalization behavior.

## Governance context

This is local architecture fitness evidence only. A finding requires review; it does not itself grant or replace external approval.

## Non-functional requirements

- Security: do not weaken unsupported-semantic fail-closed behavior.
- Reliability: deterministic stable reason code and table-driven controls.
- Compatibility: no fitness result, receipt, route, or Trust CI schema changes.
- Performance: bounded metadata comparison of two root scalar fields per changed schema.
