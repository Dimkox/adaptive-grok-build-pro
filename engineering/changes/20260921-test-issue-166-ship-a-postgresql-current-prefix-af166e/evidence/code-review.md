# Independent code review — issue 166

Recommendation: **PASS**. No blocking findings in the issue-166 diff.

Reviewer role: independently dispatched `code_reviewer`, route `af166ec812f3`. Reviewed product commit `0558da4a4047ddf12114be33fb163b4e9124fdbf` against frozen successor base `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`. Product source remained read-only; this report is the only reviewer-authored file. Parent-owned change-state paperwork was already modified at review entry.

## Inspected behavior

- The only product/test delta is `factory/tests/test_execution_persistence_postgres.py`. Production migrator and packaged SQL resources are byte-identical to the successor base. No deployed state, timeouts, dependencies, or role definitions change.
- `create_populated_current_prefix` constructs a populated schema-14 fixture through existing service APIs, removes its historical compatibility shim, and applies real packaged SQL and ledger identities through `discover_migrations()[:-1]`. It asserts the complete real recorded prefix before using the production migrator for exactly the final resource. Expected current count and checksums come from this checkout.
- The before/after assertions preserve every prior ledger row including `applied_at`, all columns of each of six populated tables, function OID/owner/sorted ACL/SECURITY DEFINER/search path, and effective execution privileges. The actual 020-to-021 boundary additionally proves the old NULL and new named-rejection behavior. A second apply must return an empty tuple and leave the complete snapshot unchanged.
- Real database checksum corruption must raise the expected `MigrationError` and preserve the drifted snapshot. Repairing that checksum restores the original snapshot before upgrade. This exercises the database ledger rather than only an offline synthetic migration list.
- Both concurrent cases hold the production advisory-lock key in a separate transaction. The observer requires a uniquely named worker's ungranted advisory lock, lock wait event, and exact blocker PID before proceeding. Release requires successful migration; sustained contention requires server SQLSTATE `57014` or `55P03`, an elapsed lower bound, unchanged snapshot, then successful retry and replay. Client-watchdog expiration is a failure.
- Cleanup is registered immediately after database creation, before fixture construction. The concurrency `finally` releases the blocker, terminates only the uniquely named worker in the owned database if needed, and performs a bounded join; the normal path also checks session disappearance. Existing historical fixture callers retain their prior explicit-cleanup behavior.

## Evidence inspected and commands run

- Read repository contract/bootstrap, active route, code-review role, adaptive-delivery and verification skills, selected workflow skills, issue snapshot, brief/requirements, implementation report, and relevant fixture/migrator/021 SQL.
- `git fetch --all --prune` — exit 0.
- `git diff --stat 1f7aedb8 HEAD`, full test-module diff, and `git status --short` — confirmed scope and reviewed HEAD.
- `git diff --check 1f7aedb8 HEAD` — exit 0.
- Read-only Python AST/hash/scope probe — exit 0: source parses; source SHA-256 is `4ae68ffb74f4f9ec1398f3c5d96513bb6b35be1337dad6614a2af70160409236`; all three focused evidence-file hashes match `focused-postgres.json`; Git confirms only the test module differs under `factory/src` and `factory/tests`.
- Inspected coordinator verifier JSON at `/home/pall/.cache/agbp-run/issues-wave-20260921/issue166/verify-initial.json`: status pass, timestamp `2026-09-21T06:51:14+00:00`, fingerprint `32a5f001feb1e320c0308ccad89a16d06b9d9c7ddeeef328c23b47e6e825e6cc`, source-stability pass. PostgreSQL exit gate records 782 tests, 2 skips, and successful restart/reconciliation checks.
- Inspected and hash-validated `focused-postgres-run2.log`: all three new current-prefix tests passed, zero skipped, 10.807 seconds, with bound-container cleanup recorded. These are implementation/coordinator executions; this reviewer did not rerun Docker or the full gate.

## Limits and handoff

The lock tests establish advisory-lock contention recovery. Timeout occurs before migration DDL, so this is not evidence of rollback after a partially executed suffix or of live function-call blocking. The scoped brief and implementation report describe this boundary accurately. Future migrations that intentionally change the protected function or sampled table contents may require corresponding contract updates even though the prefix and suffix identities remain checkout-derived.

Local review is not merge authority. Final paperwork/commit changes need coordinator-owned fresh fingerprint binding; external exact-head Trust CI remains required.
