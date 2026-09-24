# Issue #73 red/green evidence

## RED

Command:

`python3 -m unittest tests.test_policy.PolicyTests.test_new_grant_uses_neutral_binding_digest_key tests.test_policy.PolicyTests.test_legacy_tree_fingerprint_grant_remains_valid tests.test_policy.PolicyTests.test_conflicting_grant_binding_fields_fail_closed -v`

The pre-change producer failed `test_new_grant_uses_neutral_binding_digest_key` because it emitted
`tree_fingerprint`; the legacy migration setup errored because `grant_binding_digest` did not yet
exist. The conflicting-field case already failed closed incidentally because the old reader bound
only the legacy key.

## GREEN

The same three policy tests plus
`test_issue_73_historical_probe_evidence_remains_byte_identical` passed after the bounded
producer/reader change: 4 tests, 0 failures. The full focused policy/history run then passed:
56 tests, 0 failures. Adjacent protected-write and human-gate suites also passed: 21 tests,
0 failures.
