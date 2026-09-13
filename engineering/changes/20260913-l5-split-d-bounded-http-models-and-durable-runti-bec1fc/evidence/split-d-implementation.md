# D sole-writer implementation handoff

Selected writer: data_implementer; route bec1fcdde794. Worktree /home/pall/grok-projects/adaptive-grok-build-pro-l5-split-d. Genuine product predecessor C is a75b3cd639a1483533069e8634759cdfc6612310; immutable source reference f31406e970d67f7cd59694da5de88915adb0fa68. Parent owns any concurrent paperwork-only ancestry correction, Git commits, full verification, independent reviews and receipts. This report records focused verification, not full route completion.

## Implemented selection

Twenty-four changed product/test/config paths are enumerated and SHA256/Git-blob bound in split-d-source-sha256.json. Sixteen whole files match the frozen reference exactly. The remaining eight are precisely staged architecture rules/model/inventory, pyproject without future console scripts, helper-only landing_host_config, the explicitly shortened Qwen integration test, the new independent direct-runtime test, and the separately authorized SQLite lifecycle correction.

D now includes the final bounded HTTP DTO/decoder, Grok/Qwen HTTP executor with explicit Qwen region and private credential selection, PDF/audio/image intake/media isolation and SSE decoder, normalizer/intake changes, shared runtime artifact builder, durable server composition, FactorySettings and existing server ownership wrapper. factory/uv.lock matches the final reference, including pypdf; pyproject adds only the matching dependency and worker package data. No future console entrypoint is registered.

landing_host_config contains only the frozen filesystem helper bodies and their minimal imports. No host dataclass/loader or dedicated host implementation is present. The live executor test retains both HTTP V2 sealing and native V1 persistence/reopen/cross-version rejection, but defers only final lines339-372 that import future backup/host/publication pieces. No tests/__init__.py delivery bootstrap was copied. The independent mixed-reader test introduced in C remains byte-identical to C.

Architecture declares exactly nineteen actual production landing modules: offline16, SQLite1, host1, live1. The new HOST rule contains only landing_server; the pure landing_http DTO/parser remains under the offline forbidden-import rule. Five offline paths and their exact owners were added. The new test_landing_server.py is explicitly owned by NODE-FACTORY-LOCAL-API. No future module path or architecture budget was added or relaxed. Existing rules order was preserved to avoid an unrelated reorder diff.

## Independently reproduced SQLite correction

The frozen lifetime lock leaked on four failure seams: KeyboardInterrupt after real flock before the helper returned; KeyboardInterrupt during sqlite3.connect after lock acquisition; KeyboardInterrupt during _configure; and an ordinary initialization error whose connection.close raised during unwind. Each reproduced refusal of an immediate second real store with store_writer_active. The RED tests bounded their own intentionally leaked descriptors in finally blocks.

The minimal correction is limited to landing_sqlite_store.py:

- _acquire_writer unwinds on BaseException, releasing the opened/locked descriptor even when interrupted before returning it.
- The connection-open error branch unwinds on BaseException while retaining the existing store_open translation specifically for sqlite3.Error; other failures propagate after release.
- The initialization error branch unwinds on BaseException and releases the writer in a finally around connection.close, including when that close raises.

This is a disclosed production difference from f31406e, authorized by the parent/user-approved lifecycle scope; preserve it through E-G. Exact patch against frozen: split-d-sqlite-frozen-deviation.patch. All pre-existing store methods other than __init__/close remain AST-identical to C. Schema version/application identity, SQL, column/index/FK inventory, recovery statements and row/evidence codecs are unchanged. No SQL migration, backfill, evidence rewrite, retry/replay or additional service was introduced.

## Direct lifecycle evidence

The new test_landing_server.py uses direct FactorySettings, sibling owned 0700 directories and real temporary SQLite. It does not depend on E host/config fixtures. It proves default-off composition acquires no source or provider key; competing writers fail before quarantine construction and before credential access; exact source validation precedes Qwen credential acquisition; the credential callback observes the writer lock; invalid source and Grok selection do not read Qwen credentials; RuntimeError and KeyboardInterrupt after ownership release the store; and existing server.build_app's actual ASGI lifespan holds ownership until normal or exceptional exit. Application-construction failure also releases ownership. Only legacy PG readiness/store and actor seams are mocked, so these tests never connect to PostgreSQL or open a network listener.

AC-002 should name factory/tests/test_landing_server.py as evidence. C's retained V1/V2 compatibility regression and D's synthetic HTTP/native producer persistence tests both pass with the real durable store. Provider responses and credentials in the tests are synthetic; no operator files or live provider requests were used.

## Focused verification

- Extraction-first RED: three missing-module collection errors against C for HTTP/media/SSE (split-d-extraction-red28.out), before their source extraction.
- Frozen SQLite RED: two initialization/unwind failures (split-d-sqlite-ownership-red.out), then the expanded three constructor failures including connect interruption (split-d-sqlite-all-constructor-red.out). Pytest additionally counts the unittest parent method as passed; these runs are failures, not passes.
- Frozen lock-helper RED: real post-flock interruption leaves writer active (split-d-writer-acquire-red.out), one failure.
- Final Factory focused run, 28 workers across eight relevant files: **105 passed, 78 subtests passed in 5.73s**, split-d-focused-green-final28.out. Earlier pre-helper strengthening run:104+78 passed, split-d-focused-green28.out.
- Root architecture/model/boundary tests, 28 workers: **172 passed, 609 subtests passed in73.01s**, split-d-architecture-green28.out. This ran before only the last SQLite helper cleanup/test addition; architecture source/model/inventory did not change afterward.
- Final actual-route-base fitness: **PASS**, including all code budgets/change separation/module/network/secret/tenant/workspace checks; split-d-fitness-final.json. Contract compatibility and migration safety are not_applicable for D's unchanged public/data schemas, not newly granted permissions.
- Changed Python Ruff: all20 files PASS, split-d-ruff-final.out. Initial invocation via the test interpreter failed because Ruff is installed as /home/pall/.local/bin/ruff rather than in /tmp/agbp-venv; that non-evidence output remains split-d-ruff.out. No package was installed to recover it.
- Architecture diagram --check passes without generated changes, split-d-diagrams.json. git diff --check passes after source completion.

Final focused command (cwd D, with PYTHONPATH=.:factory/src:delivery/src:.grok-stack, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 and PYTHONDONTWRITEBYTECODE=1):

```
taskset -c 0-27 /tmp/agbp-venv/bin/python -m pytest -c /dev/null -p xdist.plugin -p no:cacheprovider --rootdir=. --import-mode=prepend -q -n28 --dist=loadfile --max-worker-restart=0 factory/tests/test_landing_server.py factory/tests/test_landing_media.py factory/tests/test_landing_sse.py factory/tests/test_landing_normalizer.py factory/tests/test_server.py factory/tests/test_landing_live_executors.py factory/tests/test_landing_sqlite_store.py factory/tests/test_landing_runtime.py
/tmp/agbp-venv/bin/python scripts/grok_architecture.py fitness --base a75b3cd639a1483533069e8634759cdfc6612310 --worktree --pre-risk red --json
```

No product edit remains in progress. Full prescribed verifier and all five selected independent reviews are still parent-owned pending work. No coverage percentage or external Trust CI status is claimed by this handoff.

## Recovery, limitations and shared memory

Stop the owning runtime before rolling back to C; retain SQLite/WAL and referenced artifacts. C retains both evidence versions but does not enforce the new cooperative lifetime writer lock, so keep a single process while rolled back. Do not downgrade to a V1-only reader after emitting V2, relabel evidence, or replay ambiguous provider outcomes. Existing store_writer_active/store_lock_file/startup error codes and persisted needs_human dispositions remain the observable signals. No production state, secrets, providers, Git refs, pushes, merge, deployment or approvals were changed by this child.

Suggested decisions.md fact (root-owned): Direct real-SQLite failure injection at every handoff seam found interruptions that ordinary startup tests miss. Explicit BaseException cleanup around the owned descriptor and nested finally on connection close preserve restartability without changing the persisted schema.

Suggested mistakes.md fact (root-owned): The first extraction script assumed uv.lock was at repository root instead of discovering the existing factory/uv.lock path; it stopped after source copies, and no wrong lock was written. Inspect the concrete package layout before constructing source-copy manifests; the final 24-path audit proves only the correct frozen lock was copied.
