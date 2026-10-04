# Requirements

Typed authority: change-spec.yaml; no prose override.

AC-001: PR/release early refusal prevents later scheduled execution, retains the actual result and names unexecuted work.
AC-002: source-stability and full QG always finalize; stable valid-binding failures publish FAIL, invalid authority/source mutation retain explicit receipt refusal.
AC-003: successful selected checks/scope and permitted optional skips are unchanged; diagnostic keep-going never relaxes safety refusal.
AC-004: named smoke uses existing fast CLI, explicit targets, clean committed HEAD and actual Core environment, a positive budget at most180s, and no verification receipt.
AC-005: bounded committed-HEAD observations without receipt/scope admission precede both independent selected reviews; persist both reports, commit/freeze, then run ONE final full local PR gate in parallel with external App-owned exact-head Trust CI after exact delegated UNVERIFIED branch transport. Keep same-writer repair batches, current receipts, approvals and protected PR eligibility; ten minutes is an unconfirmed target, and Core/PostgreSQL overlap is not implemented.

Edge cases: unknown/disallowed skips, lint/pilot/discovery/Factory failures, unsafe authority, source mutation, cancellation, cleanup error, dirty HEAD, invalid/empty targets, timeout and invalid named-test/mode/recording combinations. Existing fast and explicit landing behavior stays compatible. No canonical governance exception or new debt.
