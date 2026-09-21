# Evidence

Store human-readable review reports here. Machine receipts live under `.grok-stack/runtime/receipts/` and are bound to the current repository fingerprint.

## Reviewed source and limits

The full verifier passed at product commit0558da4a; full-verification-summary.json records exact initial fingerprint, command, times, report hash and check outcomes. Three independent reports passed. Advisory timeout occurs before DDL, so this proves unchanged-prefix recovery and retry under migrator-lock contention; it does not prove partial-DDL rollback or a function-call ACCESS EXCLUSIVE wait. The inherited optional fresh-cluster fixture still contains a schema21 pin; the new current-prefix tests and existing disposable/restart harness derive expected resources. Runtime receipts are host-local and must be checked against the final checkout.
