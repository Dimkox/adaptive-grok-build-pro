# Acceptance criteria

AC-001: helper emits exactly the legacy ordered43-table TRUNCATE, RESTART IDENTITY, no CASCADE; leaf cursor API propagates SQL errors and has no connection/transaction/credential/discovery side effects.

AC-002: execution and restart callers delegate only their shared first reset statement. Their distinct conditional/unconditional singleton resets, counters, observations, transactions, returned values, target/version checks and timeouts remain identical. Third integration reset is explicitly deferred to F; do not claim all duplicates removed.

AC-003: source package, standalone restart script and installed generic/Bitrix payload resolve the helper; installer materializes identical helper bytes and retains its closed inventory.

AC-004: deterministic characterization proves SQL equivalence, call order, failure propagation and caller-owned rollback. Real guarded disposablePG17 controls prove legacy execution/reset, rollback/permissions and actual restart behavior. No live datastore, role expansion, future migration or time-budget relaxation.

AC-005: actual exact-base architecture/code budgets, full PR verification and all five independent reviews pass for the final candidate; external App check and signed scopes remain independently required. Failure/skipped/historical evidence is not passed.

Invariants: unchanged001-025 migrations; no026 feature bytes; unchanged rules/selector/trust boundary; one application writer; preserved dirty historical worktrees.

AC-006: original two-reconciler acceptance permits only explicitly typed lock-contention refusal, preserves one actual claim and all exact-once terminal/job/claim/release/audit assertions, and checks bounded post-contention retry without swallowing unrelated errors. Deterministic refusal and unexpected-error controls plus guarded real holder/rollback/retry must pass with unchanged500ms/3s production limits. This is a minimal test repair in an existing scoped caller, not a runtime policy change or suite retry.
