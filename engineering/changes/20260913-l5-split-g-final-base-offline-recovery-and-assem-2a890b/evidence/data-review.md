# Independent data review — L5 G3

Verdict: **PASS**. No blocking data-integrity finding in this final source slice.

- Reviewer: route-selected independent read-only `data_reviewer`; sole implementation owner: `data_implementer`.
- Route: `2a890b6485a5`; change: `20260913-l5-split-g-final-base-offline-recovery-and-assem-2a890b`.
- Source: `/home/pall/grok-projects/adaptive-grok-build-pro-l5-split-g3`.
- Exact HEAD: `e6a813e4c16543f262ced2d9ea353caaad9452d1`.
- Genuine corrected-F base: `c3f60f09b819c1a246f7af2dcd6664cf3be52dd6`.
- Current fingerprint: `d462d16bbd7f26d6f2dac6fc4b2ae4c5b9bc44d437898297cf3ca524c7b0028b`.
- Full verifier: `/tmp/agbp-sweep/split-g3-full-final.json`; SHA-256 `7c9ff5a6340c93fe595e5dfefca996610ec0f2308300baed7c752a500f764a99`. Route, fingerprint and architecture HEAD match this checkout; all 15 checks PASS, including disposable PostgreSQL and source stability.

## Review findings

1. **Backup coordinates with both existing writers.** `create_snapshot` validates private disjoint roots, takes the landing store's actual lifetime writer lock and the publication store's actual intent-writer lock, and only then creates the snapshot directory. Both acquisitions are nonblocking and registered for cleanup. Tests hold real temporary owners in turn, prove rejection before destination creation, close the owner, then successfully snapshot and reacquire both stores. The locked interval spans both SQLite copies and the retained-artifact inventory, preserving a coherent offline application snapshot under the documented cooperative-writer assumptions.
2. **SQLite backup includes committed WAL state.** `_snapshot` opens the source through an escaped read-only URI, checks application ID/version, disables trusted schema and uses SQLite's backup API. It enforces the database size/deadline checks through its progress callback, converts the destination to DELETE journal mode and closes/syncs it. The independent test leaves a committed row only in WAL, proves a main-file-only copy lacks it, then proves the backup includes it with no WAL/SHM dependency. This low-level fixture intentionally adds a test table; it proves the copy mechanism, not application acceptance of an expanded schema.
3. **Snapshot integrity and restore identity are explicit.** Artifact names, types, owner/mode/link count, file bounds and descriptor metadata are checked; copies are exclusive and hashed. A final manifest records exact roots and sorted entries, and is written/synced after the copied categories. Restore requires the separately retained manifest digest, exact expected roots, closed entries, unique allowed names and matching file digests. All destination roots must be absent and private parents valid; existing roots are neither overwritten nor rewritten. Absolute retained-artifact paths therefore remain valid without altering sealed envelopes.
4. **The deterministic restore-budget defect is corrected narrowly.** Relative to frozen `f31406e970d67f7cd59694da5de88915adb0fa68`, backup source changes only by adding the remaining second-pass size check after successful hashes and before any destination root creation. The same budget/deadline continues into copying. With payload size S, verification consumes S and copying consumes S; known `2S > MAX_TOTAL` is rejected before mutation. The regression demonstrates backup success under `S + 1`, restore rejection with all original roots still absent, and successful restore at exactly `2S`. The existing 4 GiB accounting cap, 512 MiB per-file bound, 4,096-file limit and 180-second cooperative deadline remain unchanged.
5. **Restore remains inactive and preserves cross-component data.** Live-enabled restore is refused. No provider executor or publication stage/activate path is called by backup/restore. The populated publication fixture roundtrips an actual prepared intent and reopens it through the corrected strict F store, preserving the full saved result. The final mocked-Qwen integration creates both V1 and V2 retained evidence, closes/reopens SQLite, snapshots/restores at the exact original paths with special characters in the snapshot name, reopens both records and constructs validated publication bundles. External site pointers are excluded and publication reconciliation is explicitly required after restore.
6. **Predecessor repairs and data contracts are preserved.** Direct Git blob/mode comparisons confirm that corrected F publication source/tests, D SQLite cleanup/settings/server changes and C's independent reader test are identical to the genuine corrected-F base. No factory/delivery contract or migration path changes in G. The review uses the current tree and fresh checks; earlier G/F analysis hashes remain historical provenance only. There is no schema migration, backfill, index redesign, state conversion or sealed-record rewrite in this slice.

## Independent disposable verification

Executed against the exact current source:

```text
PYTHONPATH=.:factory/src:delivery/src:.grok-stack PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 taskset -c 0-27 /tmp/agbp-venv/bin/python -m pytest -c /dev/null -p xdist.plugin -p no:cacheprovider --rootdir=. --import-mode=prepend -q -n28 --dist=loadfile --max-worker-restart=0 factory/tests/test_landing_backup.py factory/tests/test_landing_live_executors.py::LandingLiveGrokQwenCompositionTests::test_qwen_compose_seals_complete_artifact_with_mocked_http factory/tests/test_landing_publication_cli.py::PublicationStoreSchemaTests
```

Result: **22 passed, 63 subtests passed in 4.99 seconds**, exit 0. There were 28 existing dependency deprecation warnings for Starlette's AnyIO BlockingPortal alias. This run includes negative snapshot/manifest/content/link/duplicate/existing-root checks, active-writer reacquisition, WAL content, the exact two-pass budget boundary, retained mixed evidence, populated intent recovery and the corrected F conflict-policy schema regressions. Final source HEAD, clean working tree and fingerprint were verified after testing. Only this counterpart review report was written.

## Limits and recovery

These are local source/data checks, not external Trust CI merge authority, real-provider acceptance or production activation. No operational database, credential, provider endpoint, live site or installer was accessed/executed. Synthetic fixtures do not establish Qwen moderation behavior or serving-origin readiness.

The offline boundary relies on local cooperative locks plus the documented operator requirement to stop writers and avoid sharing artifact/quarantine roots across different stores. Moving old roots is an operator-controlled recovery step; absence of a pathname is not proof that every unrelated/raw client has stopped. Snapshot/restore validates database identity and byte integrity; normal application readers still validate supported schema and records when reopened. It is not a repair tool for unknown or corrupt application state.

The 180-second budget is checked cooperatively during work; it is not an OS-level hard deadline for blocking filesystem calls. The 4 GiB value is the existing operation accounting limit, not a guarantee about all physical filesystem I/O. Restore requires at most 2 GiB payload before the other bounds; a saved snapshot can exceed that restore allowance. The runbook states this asymmetry and the new pre-mutation refusal honestly. Failures after destination creation can leave partial roots; they remain inactive and must be preserved for inspection, with no automatic retry/cleanup or service start.

Keep the separately retained manifest digest and old roots as recovery evidence. Retain a V2-capable reader or a consistent pre-V2 snapshot for binary rollback. Source rollback does not undo external publication, and restoring intent/artifact state does not restore the deployment pointer. Reconcile the actual target by observation before any later separately authorized publication action.
