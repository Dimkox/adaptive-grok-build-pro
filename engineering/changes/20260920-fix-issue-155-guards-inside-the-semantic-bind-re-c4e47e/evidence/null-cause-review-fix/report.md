# Issue 155 — legacy NULL exception-cause review fix

Route `c4e47ea3ced7`; starting HEAD `4a47c76b3fb37fbac430fd209771a695832610d2`. Application/test bytes frozen after the focused checks below. No commit was made.

## Root cause and change

`bind_repair_child` sent a legacy SQL NULL response (`None`) into `RepairChildTaskBindingV1.from_dict`. The parser raised `ContractError('invalid_object: repair_child_task_binding')`; the catch branch then raised the correct top-level `StoreError('...store_returned_null')` **from that misleading contract error**. Checking only the outer message missed the exception cause/context that violated `SIG-001`.

Moved the existing `None` classification immediately before the parser. A legacy refusal now raises its `StoreError` without creating a contract error. The malformed-payload catch still uses `raise ... from exc`, preserving real contract failures. Exact rejection envelopes retain their distinct reason.

Changed only:

- `factory/src/adaptive_factory/store.py`
- `factory/tests/test_migrations.py`

The existing `test_bind_repair_child_separates_an_unexplained_store_refusal` now covers legacy NULL, a malformed mapping, and the exact deadline rejection envelope. It checks no cause/context or `invalid_object` rendered traceback for the refusals and preserves a `ContractError` cause for malformed data. No test method was added: the migration module still contains **24 tests**.

## Red-green evidence

The targeted RED failed only for `response=None` at `assertIsNone(raised.exception.__cause__)`, with `AssertionError: ContractError('invalid_object: repair_child_task_binding') is not None`. The other subcases passed before the source repair. After the minimal repair, the targeted test and all 24 migration tests pass. Focused ruff was clean before and after; `git diff --check` passes.

| Check | Exit | Seconds | Full output |
| --- | --- | --- | --- |
| red | 1 | 0.315 | `/home/pall/.cache/agbp-run/p155-null-cause-review-fix-7grobyc6/red.log` |
| ruff-before | 0 | 0.033 | `/home/pall/.cache/agbp-run/p155-null-cause-review-fix-7grobyc6/ruff-before.log` |
| green | 0 | 0.365 | `/home/pall/.cache/agbp-run/p155-null-cause-review-fix-7grobyc6/green.log` |
| migrations | 0 | 0.365 | `/home/pall/.cache/agbp-run/p155-null-cause-review-fix-7grobyc6/migrations.log` |
| ruff-after | 0 | 0.065 | `/home/pall/.cache/agbp-run/p155-null-cause-review-fix-7grobyc6/ruff-after.log` |
| diff-check | 0 | 0.017 | `/home/pall/.cache/agbp-run/p155-null-cause-review-fix-7grobyc6/diff-check.log` |

Commands are recorded verbatim in `results.json`; the reviewed two-file diff is `change.patch`. All artifacts are outside the checkout.

## Frozen content

- `factory/src/adaptive_factory/store.py`: `802cee57ab296935f52433e2c53e822735bec3ff75cc97cc40b2cc286b5845cc`
- `factory/tests/test_migrations.py`: `91313992381cfe19cff1fa360fbd8ce34ee2dd8f492ab7b45342af4701354fd7`
- `factory/src/adaptive_factory/resources/018_semantic_validation_bridge.sql`: `33053563dce7c34edfa9301130272adb34651d44dd1f2bc305ba3eec01382c70`
- `factory/src/adaptive_factory/resources/021_semantic_repair_child_rejection_reasons.sql`: `868bc21f47351f92b79acb8bd8e9390c62b43803c0b5761400e32c7143d56d5e`

No SQL resource changed. `018` remains byte-identical to the route base. The fix changes only diagnostic classification of the sentinel return; it changes no success binding, migration, database state, timeout, guard, schema, or rollout gate.

The controller owns the fresh full verifier, the new four-pass PostgreSQL streak, final independent review, and rollback-document repair. Earlier verification/streak evidence predates this source change and cannot certify these bytes. No runtime receipts/grants/routes, durable documentation, commits, or external services were changed by this subtask.

Durable memory fact for the controller: verifying only an exception's top-level message can miss a misleading chained cause. Classify a non-payload sentinel before schema parsing and verify both the exception chain and rendered traceback while preserving the cause for genuinely malformed data.
