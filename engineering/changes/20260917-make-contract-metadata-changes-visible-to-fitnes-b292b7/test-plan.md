# Test plan — JSON Schema documentation metadata

| Priority | Scenario | Expected | Evidence |
| --- | --- | --- | --- |
| P0 | Root `description`-only edit on registered JSON Schema | fitness fail/review with `changed_documentation`; no wire incompatibility label | comparator unit test |
| P0 | Root `title`-only edit | same metadata-specific signal | comparator unit test |
| P0 | Optional structural property only | existing `widened_producer_output` behavior unchanged | structural control test |
| P1 | Metadata and structural edit together | metadata signal plus existing structural finding | combined diff test |
| P1 | No effective contract change | existing pass behavior | unchanged control |
| P1 | Nested property title/description edit | no root `changed_documentation` finding | comparator negative control |
| P1 | Existing event contract change | existing event semantic finding unchanged | event control |
| P1 | Unsupported JSON Schema change | unsupported status remains fail-closed | unsupported control |
| P1 | Change-package slug contains `contract` and contains `contracts/openapi.yaml`, while a partner API spec sits directly under `engineering/contracts/` | verifier skips all `engineering/changes/` YAML while checking exact API contract directories and filenames elsewhere | verifier regression |

Focused evidence: all 113 cases in `tests.test_architecture_fitness` pass, including the new metadata controls and existing event dependency controls. `py_compile` and `git diff --check` pass. Run `python3 scripts/grok_verify.py --mode pr`, then code/test/security/release reviews before closing this package. No live Trust CI calls or external writes.
