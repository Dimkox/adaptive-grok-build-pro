# Repo explorer analysis — issue #128

Route 3822310b0593; base 2f66ba6. Read-only.

- `factory/tests/run_disposable_exit.py` already binds container full ID/name/image/nonce, but normal removal uses `docker rm -f` without removing the PostgreSQL image's anonymous PGDATA volume. An unused name-based `_cleanup` helper is not safe to revive.
- Startup should enumerate only the exact harness label, inspect each candidate's full ID/name/image/nonce/creation time/state/mounts, and delete only verified stale ownership; never delete by name or prefix alone. Report reclaimed identities.
- Default SIGTERM bypasses Python `finally`. The verifier's `subprocess.run` does not relay cancellation or own a process group. Stop and wait for test descendants before cleanup; then let the harness unwind. Preserve timeout as an inconclusive failure, not an ordinary assertion result.
- Existing tests to extend: `factory/tests/test_migrations.py` exact-ID binding/cleanup tests and `tests/test_verification_doctor.py` check-result summary tests.
- The harness also leaks an anonymous volume on normal cleanup, a confirmed companion defect to the cancelled-run leak.
