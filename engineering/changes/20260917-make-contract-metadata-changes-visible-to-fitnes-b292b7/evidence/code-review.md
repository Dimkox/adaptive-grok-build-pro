# Code review — #120

**Final result: PASS — no outstanding findings.** Reviewed the exact expanded final diff after the latest full verifier pass; no verifier was run as part of this review.

The comparator keeps resolver and unsupported-schema preflight ahead of the new finding. It emits `changed_documentation` only for changed root `title`/`description` in a registered JSON Schema with stable identity/path, and preserves the separate directional structural findings. Nested annotations are out of scope and do not trigger the root finding. Tests cover metadata additions/removals, nested metadata, combined and structural-only edits, unchanged controls, both comparison directions, and unsupported root `$ref` handling.

The YAML classifier now explicitly excludes paths whose first two components are `engineering/changes`, including adversarial package paths that also contain `contracts/` or an `openapi.yaml` filename. Outside that subtree it still validates files under `contracts`, `contract`, `openapi`, or `asyncapi` components and explicit OpenAPI/AsyncAPI filenames. The regression test checks excluded `change-spec.yaml` and nested package `contracts/openapi.yaml`, while confirming registered contract, OpenAPI, and AsyncAPI paths remain counted. `git diff --check` passed.
