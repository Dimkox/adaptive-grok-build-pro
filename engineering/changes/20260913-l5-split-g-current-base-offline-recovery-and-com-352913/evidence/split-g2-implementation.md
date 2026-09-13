# G2 final assembly sole-writer handoff

Selected sole writer data_implementer; route3529132ae173; genuine F2 predecessor and checkout HEAD5a2ead6e6e1eff5c5df28a8d4bcb91a209975187. Target /home/pall/grok-projects/adaptive-grok-build-pro-l5-split-g2. Frozen source f31406e970d67f7cd59694da5de88915adb0fa68 remained untouched. G data analysis was originally written against the archived F/G routes; its source hashes and bounded budget ruling apply to the unchanged product components now inherited through F2. This is focused implementation handoff, not full-route or production-readiness certification.

## Exact final extraction and preservation

G changes ten product/test/config paths. Seven files match frozen bytes and executable modes exactly: complete architecture rules, mandatory22-module inventory test, final Factory pyproject, all three runtime installer/example/service files, and the complete Qwen live-executor test including its deferred mixed-evidence recovery/publication-bundle tail. architecture/system.yaml matches frozen plus the explicitly retained D test_landing_server.py owner. The backup source and test have the bounded additions below.

No earlier C/D/F repair was overwritten. All pre-existing product files outside G's ten paths remain byte-identical to actual F2, including C's independent mixed-reader test, D's SQLite interruption/alias/server-cleanup corrections and independent tests, and F's strict publication schema/authority/restart/restore tests. Deployment inventory remains22 members, with19/20-member epochs retained by the already delivered readers.

The final product-root comparison against frozen covers factory/, delivery/, tests/, architecture/, .grok-stack/adaptive_grok/, schemas/ and scripts/, excluding Markdown documentation. It found exactly ten disclosed differing paths: architecture/system.yaml; the repaired publication, backup, landing SQLite, existing server and settings sources; the strengthened backup/publication/runtime tests; and the new independent D server test. No unexplained product difference remains in that comparison. Root owns the broader whole-Git-tree comparison and shared documentation/current-state JSON.

## Reproduced restore-budget correction

The reduced-cap regression uses only a small disposable snapshot. It sums payload size S from a probe manifest, successfully creates another snapshot under MAX_TOTAL=S+1, moves the inactive fixture roots, then attempts restore under the same cap. Frozen code completely verifies the payload, creates destination roots and fails snapshot_budget on the known second copy pass. RED asserts state_path already exists after that deterministic failure.

The production correction is exactly three added lines after complete content/mandatory-landing validation and before any restore root is created: check the existing deadline, then reject snapshot_budget if budget.total plus the validated entry-size sum exceeds MAX_TOTAL. The same Budget instance, byte consumption rules,4-GiB accounted-I/O cap,512-MiB per-file cap,4,096-entry limit and180-second common deadline remain unchanged. No reservation is charged twice, no budget is reset and no limit is expanded.

The regression now proves insufficient S+1 refuses before all three destination roots exist, while exactly2*S permits the full inactive roundtrip. Restore's two passes mean a payload larger than2GiB cannot fit the default4-GiB accounted-I/O cap; snapshot creation can still succeed for a larger payload. This change refuses that known impossibility early rather than claiming every created snapshot fits restore. Unexpected later I/O/time failures can still preserve partial roots; restore is not an atomic transaction across directories.

Exact new production deviation from frozen: split-g2-backup-frozen-deviation.patch. Preserve it in final disclosure alongside C/D/F additions.

## Added independent evidence

Four new methods extend the frozen backup test file without changing existing assertions:

- Reduced-budget early refusal and exact-two-pass positive boundary described above.
- Real active landing writer and real active F PublicationStore separately reject snapshot before destination creation; after releasing each owner, capture succeeds and both stores can be reacquired. This also checks cleanup of an earlier lock when the later lock conflicts.
- A controlled disposable SQLite source commits a fixture table/row into uncheckpointed WAL with automatic checkpoint disabled. A copy of the main DB alone cannot read the table, while _snapshot produces a DELETE-journal standalone database containing the row without WAL/SHM files. This exercises SQLite backup behavior on test-owned content; it does not bypass an operator lock or claim an application schema migration.
- A populated real F PublicationStore with a synthetic prepared request survives G snapshot/restore and is read through F's strict readonly validator with the exact saved record, digest/body/phase/timestamp. Stage/activate callbacks are forbidden; the result remains restored_inactive with publication reconciliation required.

The final Qwen test now additionally snapshots and restores native v1 and mocked-HTTP v2 retained jobs, then builds both publication bundles after same-path restore. It uses the full frozen tail and special-character snapshot pathname. No model request, actual publication grant or service operation occurs.

## Focused verification

- Before source extraction, the frozen backup test failed collection because landing_backup did not exist: split-g2-extraction-red.out.
- Reduced-budget RED: one failure after restore had created state_path, split-g2-budget-red.out. No GiB allocation was required.
- Integrated focused Factory run using28workers: **77 tests+140 subtests PASS in17.85s**, split-g2-factory-focused28.out. Paths: backup, full live-executors/Qwen, C runtime, D independent server, F publication CLI. The run reported28 existing AnyIO deprecation warnings.
- After that run, the new WAL test's unnecessary temporary process-umask wrapper was removed because _snapshot already creates its destination with explicit0600. The exact affected test then passed against final source: **1 PASS in0.98s**, split-g2-wal-final.out. No product code changed between these runs and no broad suite was repeated.
- Mandatory current22-module inventory: **4 tests+119 subtests PASS in4.94s**, split-g2-inventory-green28.out.
- Final genuine-base fitness: **PASS**, split-g2-fitness-final.json, including all unchanged code budgets/separation/import/ownership/secret/tenant/workspace checks. Earlier same-product fitness is retained as split-g2-fitness.json.
- Ruff on all4 changed Python source/test files PASS, split-g2-ruff.out. Architecture diagram --check PASS, split-g2-diagrams.json. bash -n factory/runtime/install-claw.sh PASS without running the installer. git diff --check PASS.

Focused tests used PYTHONPATH=.:factory/src:delivery/src:.grok-stack, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, PYTHONDONTWRITEBYTECODE=1 and taskset0-27. Factory and root test packages were collected separately with pytest -c /dev/null -p xdist.plugin -p no:cacheprovider --rootdir=. --import-mode=prepend -q -n28 --dist=loadfile --max-worker-restart=0. Actual fitness used --base5a2ead6e6e1eff5c5df28a8d4bcb91a209975187 --worktree --pre-risk yellow --json.

## Audit and next stage

Manifest: /tmp/agbp-sweep/split-g2-source-sha256.json, containing exact ten-path hashes/blobs/modes, route/base, seven whole-frozen selections and the complete ten-path final product difference inventory. Product/test writes are now frozen. The parent owns README/current-state/runbooks, commit, mandatory full verification, code/test/data reviews, PR delivery and external Trust CI. No local or external completion receipt is asserted here.

Suggested shared-memory decision (parent-owned): When restore already knows the complete validated payload size, preflight the second copy against remaining accounted I/O before creating destination roots. A reduced-cap fixture proves both early failure and the exact successful two-pass boundary without increasing limits or allocating large files.

Runtime templates were only copied and syntax-checked. No installer execution, source fetch, operator-state access, credential read, actual grant, provider/HTTP call, service activation, publication effect, Git mutation or other worktree edit was performed by this child. Supported recovery still requires stopped cooperative writers, disabled providers, separately retained manifest digest and absent original destination roots; restored publication state requires observation before any new independently authorized effect.
