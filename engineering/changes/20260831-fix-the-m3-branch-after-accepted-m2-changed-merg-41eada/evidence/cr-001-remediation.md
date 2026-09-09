# CR-001 remediation — branch-independent receipt assertions

Route: `41eadaeae674`

The first independent code review identified two assertions in
`tests/test_change_receipts.py` that bound receipt tests to the incidental global
architecture status of cumulative branch history. The remediation removes only
those two `result.status == "fail"` assertions.

The tests continue to assert the architecture result name, configured state,
frozen adoption base, route base, architecture fingerprint, bootstrap evidence,
receipt linkage, and staleness behavior. M3 governance receipt and invalidation
coverage is unchanged; no production source or public contract is modified.

Verification commands and final exact head are recorded by the subsequent
fingerprint-bound verifier and review wave. This note and the original FAIL
report are local workflow evidence, not merge authority.
