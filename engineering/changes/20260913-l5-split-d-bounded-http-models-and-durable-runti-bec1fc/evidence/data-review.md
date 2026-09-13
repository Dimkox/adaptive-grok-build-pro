# Independent data review — L5 D

Verdict: **PASS**. No blocking data-integrity finding in this source slice.

- Reviewer: selected read-only `data_reviewer`, independent of `data_implementer`.
- Route: `bec1fcdde794`; change: `20260913-l5-split-d-bounded-http-models-and-durable-runti-bec1fc`.
- Source: `/home/pall/grok-projects/adaptive-grok-build-pro-l5-split-d`.
- Exact HEAD: `bb93885034e52b80653efd96602fec182f7db10a`.
- Actual route base inspected: `a75b3cd639a1483533069e8634759cdfc6612310`.
- Current tree fingerprint: `1a7e327a57a74acdb38f883a7496e52eb97732c42c42026a22f2a102e7018999`.
- Verifier: `/tmp/agbp-sweep/split-d-full-final.json`; SHA-256: `24ac27ae045e5f6181aa38768bf781a4bc9b5b68dcc50fe6a0b0737f966511bb`. Its route, fingerprint and architecture HEAD match this checkout; all 15 checks are PASS, including disposable PostgreSQL and source stability.

## Findings and evidence

1. **The persisted data contract is unchanged.** I inspected the actual base-to-HEAD diff and the surrounding SQLite store, composition, settings, server and retained-reader tests. Independent AST comparisons confirm that `_SCHEMA`, schema version 1, application ID, expected columns/foreign keys, recovery batch cap, configuration/schema validation, recovery query, transaction/read/decode/validation functions are unchanged from the genuine route base. No migration or contract file differs in this slice. Consequently there is no migration, backfill, new index or query-plan change to approve. Existing tenant/repository/job keys, durable command idempotency and optimistic revision checks remain authoritative.
2. **Writer ownership precedes startup state effects.** `landing_sqlite_store.py:98` acquires the private advisory lock before SQLite open/configuration/schema initialization/recovery. `_acquire_writer` at line 485 checks regular-file type, owner, mode, link count and post-lock inode identity, using exclusive nonblocking `flock`. `landing_server.py:27` acquires that store before quarantine initialization and provider credential acquisition. A competing owner therefore cannot purge quarantine or run interrupted-job recovery. Default-off composition performs no provider/source credential acquisition; explicit live composition validates source before acquiring its key.
3. **Failure cleanup preserves restartability.** Constructor connect/configuration failures and interruptions release the acquired descriptor; nested cleanup releases it even when connection close raises. Returned-store close is idempotent and survives checkpoint/connection cleanup failure. The existing server's ASGI lifespan and application-construction unwind close its owned runtime. The repaired nested `server.main` teardown independently attempts listener close, runtime close and socket cleanup. The repaired `FactorySettings.validate_landing` rejects double-slash anchors before I/O, preventing a state/quarantine alias from escaping the lexical disjointness check.
4. **Recovery remains bounded and does not replay uncertain model work.** Startup recovery processes at most the configured 0–100 rows and advances interrupted work to `needs_human` with the existing accepted/ambiguous-provider/local-interruption reasons. It does not call a provider or builder. The row cap does not bound the cost of the existing table scan or integrity check. A later composition failure can leave legitimate recovery changes already committed; startup is not advertised as read-only or fully rollback-atomic.
5. **V1/V2 retention survives this composition change.** C's independent mixed-evidence test remains present: real temporary SQLite close/reopen preserves both envelopes and original serialized bytes, rejects version/digest tampering, and does not repeat provider work. The existing durable idempotency, cross-tenant/repository isolation, bounded recovery and no-replay tests remain applicable.

## Independent disposable verification

Executed on the exact source above, without changing repository files:

```text
PYTHONPATH=.:factory/src:delivery/src:.grok-stack PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 taskset -c 0-27 /tmp/agbp-venv/bin/python -m pytest -c /dev/null -p xdist.plugin -p no:cacheprovider --rootdir=. --import-mode=prepend -q -n28 --dist=loadfile --max-worker-restart=0 factory/tests/test_landing_sqlite_store.py factory/tests/test_landing_runtime.py factory/tests/test_landing_server.py
```

Result: **23 passed, 46 subtests passed in 11.32 seconds**, exit 0. These tests use disposable roots/SQLite and synthetic or blocked provider callbacks. Final HEAD, clean working tree and fingerprint were rechecked after execution.

## Limits and recovery

This is a local source/data review, not external Trust CI merge authority or a production readiness claim. No operator credentials, operational database, deployed policy or production filesystem was accessed; no provider request, migration, deployment or rollback was performed.

The lifetime lock is cooperative, local and per state root. Raw SQLite clients and older runtimes that ignore it do not participate; two distinct state roots must not be configured to share quarantine. Existing private-root and operator deployment assumptions still apply. Stop the owner before reverting D to C; preserve database/WAL and retained artifact files, retain one-process operation, and retain C's V2 reader. Rollback earlier than C requires a consistent pre-V2 snapshot or compatible reader. Ambiguous model outcomes must not be replayed automatically.
