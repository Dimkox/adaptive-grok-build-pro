# Repo explorer — issue #125

Reproduced on base `2f66ba6`: removing `evidence` from INV-001 and FORBID-001 still yields `ok: true`; `criterion_coverage()` enumerates only `acceptance_criteria`. Local verification `_change_specs()` records coverage after successful validation but does not reject nonempty `unmapped_ids`.
