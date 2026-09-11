# Verification

Require actual fail-before/pass-after behavior for opted-in process sharding, exact once-only method execution, invalid configuration, inherited option isolation, zero-worker rollback, missing tools, assertion/collection errors, worker crash, timeout cleanup, coverage below74, missing/corrupt/partial coverage and nested coverage isolation. Preserve all existing verifier compatibility tests.

Measure main baseline separately from the prior M7 worktree; run one heavy pool at a time. Final source gets full python3 scripts/grok_verify.py --mode pr, including existing PostgreSQL/restart requirements. Evidence compares method IDs and skips, with pytest9 subtests kept distinct. Independent reviewers inspect the actual final diff.
