# Declared-ID fallback review repair

Independent [code](code-review-first.md) and [test](test-review-first.md) reviews found the initial path-first implementation rejected registered IDs whose spelling fails raw relative-path grammar. The shipped 50-contract differential and plain-alias fixtures did not cover this boundary.

The sole writer added a comparator-local fallback only after the shared path-first helper returns UNSAFE; a registered ID is resolved with the existing ID-first helper. The shared helper and conservative dependency closure remain unchanged. No-ID unsafe aliases and duplicate claimants still refuse, while concrete valid paths retain priority.

Exact focused command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack python3 -m unittest tests.test_architecture_model.ArchitectureModelTests.test_schema_resolver_declared_id_fallback_detects_narrowing tests.test_architecture_model.ArchitectureModelTests.test_schema_resolver_unsafe_path_alias_fallback_preserves_refusals tests.test_architecture_model.ArchitectureModelTests.test_schema_resolver_concrete_path_cannot_be_shadowed_by_declared_id tests.test_architecture_fitness.ArchitectureFitnessTests.test_unsafe_declared_id_alias_keeps_both_dependency_candidates`.

RED exit 1: four failing subtests, wall 0.176s. GREEN exit 0: four methods in 0.013s, wall 0.202s. The CPU slot was released; broader suites/full verification were not rerun for this correction. Initial full PASS at6867f6dc is historical. Renewed independent reviews and the final mandatory full gate must cover corrected bytes.

Raw cache logs under `/home/pall/.cache/agbp-run/issues-wave-20260921/schema/`:

- `review-fix-red.log`: `2397c9275ec803ec959101bbb865fb6ba2a456420a264475c70d5853523d716f`
- `review-fix-green.log`: `03e2ce7efb78ca7222db4c9a68781f9953dd3bd674b491cc52a8a4986d74e6f4`
