# Architecture analysis

PASS for a bounded adapted transplant. Required invariants are signed-bigint admission for each scalar and cumulative amount, factual incomplete-cost semantics, unchanged timing semantics, and unchanged PR2 decision persistence/replay/fencing. Do not add a jsonschema CLI dependency or claim durable accounting/full U2. No migration/data rollback is needed; forward-fix any admission regression.
