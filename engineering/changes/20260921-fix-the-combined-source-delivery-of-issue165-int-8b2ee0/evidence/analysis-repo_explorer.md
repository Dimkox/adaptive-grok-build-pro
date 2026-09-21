# Repository integration analysis

Role: route-selected `repo_explorer`; route `8b2ee0533ba5`.
Date: 2026-09-21. Analysis only; no integrated verification or approval result.

## Inspected state and method

The worktree HEAD inspected was `23984e55560c6d559a46445061f10331ca05bcf9`, the frozen source of PR173. The route records observed main `839d3aa26bc90417424d814ee48d8b5cd3be367e`. PR173 was still pending external delivery when this analysis was assigned; its completion is a prerequisite, not an assumption made here.

Read `AGENTS.md`, `START_HERE.md`, the relevant `PROJECT_STATE.json` handoff, the actual active route, this package's brief/requirements/candidate manifest, and selected source/evidence from the three frozen Git objects. Applied the route and verification-evidence boundaries. Git object reads, source searches, ordinary JSON inspection and SHA-256/file-size arithmetic were the only analysis operations. No repository module was imported, no test/lint/compile/fitness command ran, and no container, database, remote write, source import or receipt operation occurred. Only this report was written.

All original eighteen manifest hashes matched their candidate Git blobs, and the three sets were disjoint. Candidate identity:

| Issues | Frozen commit | Original declared paths | Complete source set |
| --- | --- | ---: | ---: |
| 165 | `163847842ccddacd6f179c7a3ea082765530bb84` | 8 | 9 |
| 163 | `d80c5c8d8e5afe938d195401715daf5e69192a81` | 7 | 7 |
| 62 / 118 | `08dd467d0dc9c173af01f3b47876a9a3fa1ca639` | 3 | 3 |

## Findings and disposition

### RE-1: the initial manifest omitted the Stop hook

The #165 candidate also changes `.grok/hooks/stop_gate.py`; its exact SHA-256 is `7be3f2be3fb9ea1e581344388a40da84c3a092945e3fb1a51a024847ad0bf48b`. This is required behavior, not incidental paperwork: the hook inspects package/worktree diagnostics, keeps warnings nonblocking, avoids legacy receipt reads of known unsafe inputs, and does not mark an incomplete package completed merely because receipts exist. Declared `tests/test_package_status.py` contains `test_stop_warns_on_incomplete_package_even_without_receipt_obligations` and `test_stop_does_not_hide_incomplete_package_behind_current_receipts`, which require this hook. The prior implementation hash manifest already lists it.

**Disposition:** coordinator adopted the exact hook as the nineteenth path in `candidates.json`, amended brief/requirements/tasks, preserved the original manifest in `evidence/initial-manifest-18-paths.json`, and recorded the omission in shared mistakes. Importing these existing candidate bytes needs no invented repair. No other undeclared product path was found when comparing each candidate against `839d3aa` across `.grok`, `.grok-stack`, scripts, tests, docs, factory, Trust CI, schemas and architecture.

### RE-2: the scoping route's historical base overcounts delivered work

The budget implementation sums `max(base_size, head_size)` for every selected changed file, not only the edit hunk. A read-only overlay of the exact candidate files on `23984e55` produces these byte totals against the two source snapshots:

| Budget | Route base `839d3aa` | PR173 source tree `23984e55` | Unchanged limit |
| --- | ---: | ---: | ---: |
| `FIT-BOUNDED-ARCHITECTURE-CHANGE` | 497263 | 71097 | 1000000 |
| `FIT-BOUNDED-ALL-GOVERNED-CHANGE` | **1463628** | 1037462 | **1300000** |
| `FIT-BOUNDED-FACTORY-CHANGE` | 966365 | 966365 | 1150000 |
| `FIT-BOUNDED-FACTORY-SOURCE-CHANGE` | 252088 | 252088 | 375000 |
| `FIT-BOUNDED-FACTORY-TEST-CHANGE` | 714277 | 714277 | 775000 |

This projects a concrete all-governed byte-budget violation when PR173's already-delivered changes remain in the route comparison. It is not an executed fitness result; AST/line budgets and the actual integrated diff still require the real verifier. The exact snapshot comparison does not claim a future squash-merge commit identity.

**Disposition:** coordinator will retain `8b2ee0533ba5` as scoping provenance and generate a new continuation route through the router after PR173 actually delivers, using fetched actual main. The existing route base and budget rules will not be edited. Confirm the delivered tree equals `23984e55` and attach actual main as an ancestor before importing/checking the successor. Adopt unchanged analysis with exact identity rather than replaying a no-op analysis wave; unexpected delivery-tree changes require renewed impact analysis.

## Dependency and preservation map

- **Package diagnostics:** `change.py` imports the new `package_status.py`; status, review and the now-declared Stop hook consume it. Its Git/safe-read/spec/receipt primitives already exist. `architecture_diff.py`, `receipts.py`, `spec.py`, `tests/_support.py` and `.grok/hooks/_lib.py` are byte-identical between candidate165 and PR173. There is no additional package or installer dependency: the managed `.grok-stack` and `.grok` directories already include the new module and changed hook. The CLI scripts are already managed entries.
- **PR173 interactions:** retain PR173's `util.py`, schema, router, installer and fingerprint work. Candidate165 predates the newer utility implementation; importing its whole tree would regress delivered changes. Its new bounded tagged filename representation remains necessary even with PR173's ASCII JSON escaping: raw surrogate identity must not enter the canonical package parser. The original candidate reviews do not establish compatibility with this integrated dependency tree.
- **Repair planning:** the reader, store mapping, SQL022 and four factory test files form one unit. SQL discovery already uses packaged resources and `factory/pyproject.toml` already includes `resources/*.sql`. No registry, dependency pin, server or migration-runner change is required. These existing modules, service/admin helpers and the semantic fake-fixture dependencies are unchanged against PR173.
- **Prefix upgrade dependency:** `test_execution_persistence_postgres.py` deliberately extends the #166 file already present in PR173. It imports the declared modified `PostgresFactoryTests` fixture to populate real semantic success/escalation rows. It retains the explicit real-resource `020→021` upgrade case while adding the current `021→022` case and both functions' OID/owner/ACL/body snapshots. Import the full declared #163 test file; do not replace it with a fresh schema-only check or drop its prerequisite history.
- **Transaction and rollout boundary:** the refusal classification happens after the database context exits; persisted deadline escalation and successful replay keep their existing transaction behavior. The SQL resource changes only the function replacement/refusal expressions and retains its grants. Server readiness still requires packaged and installed migration versions to agree. Source delivery does not establish a running old/new mixed deployment; operational rollout must coordinate versions, and post-application recovery uses a later forward migration.
- **Runner capacity:** `python_test_runner.py` imports the declared private `_cpu_capacity.py`; both need to move together. Existing verification calls the same public selector/runner surface. `verification.py`, the runner requirements and `.coveragerc` are unchanged dependencies. Explicit/default-off/child paths remain separate from Linux automatic quota discovery; degraded engine choice occurs before launching tests and does not retry a failed parallel run. The tests' Trust fixtures do not require changes to `trust-ci/` source.
- Across all three candidates, no differences against their observed common main were found under `trust-ci`, `architecture`, `governance`, `packages` or `VERSION`. The #163 resource diff adds only SQL022; historical SQL001–021 remain byte-identical. Keep those boundaries in the actual import manifest.

## Fresh-clone provenance to retain

The initial target tree does not contain these candidate packages. Preserve them from their exact commits, with a new integration index naming source commit, package path, relevant file hashes and bounded evidence meaning. Their workstation paths in `candidates.json` are convenient local locations, not durable source identity. Copying only PASS summaries would discard the failures that explain the final implementation.

1. **#165 package `20260921-fix-issue-165-diagnose-unfinished-change-package-2dfd58`:** retain original implementation RED/GREEN JSON log envelopes and hash list; `initial-full-result.json` (failed whitespace gate); first code/test reviews; raw-byte repair plan, RED/GREEN and result; corrected `full-review-repair-{report,meta,result}.json`; final code/test reports and `final-review-adoption.json`; source issue, design, limits and recovery. The corrected full names tested head `bca409d1`; the reviews name `a946f3e3`; `16384784` is a later documentation freeze. None is a receipt for this new combined tree.
2. **#163 original package `20260921-fix-issue-163-name-postgresql-semantic-plan-repa-d2e7e6` and continuation `...-806a83`:** retain both, including original analyses, design, implementation candidate hashes, RED/offline GREEN/PostgreSQL transcripts, the first failed deadline fixture and its corrected targeted rerun, initial failed full report/meta, original-base failure, current-main diagnostic and delivery-base ruling. Keep `current-main-adoption.json` with its references to the original package. The original full remains failed; its separate current-main diagnostic is not a replacement receipt. Focused 11-of-12 plus one corrected rerun must not become a fabricated fresh 12-test pass.
3. **Capacity package `20260921-fix-issues-62-and-118-in-python-test-runner-work-45e0cc`:** retain all five analyses, prior research, implementation report, `red-initial.json`, `green-runner-attempt-1.json`, and `ruff-attempt-1.json`, including exact lossless outputs, command, duration and source hashes. Keep the PR135 provenance at `7a7851af5d11e8ce5c3af23ab46214ae7ae4cdc8`. The recorded scope is 38 focused tests and scoped Ruff, not complete integrated verification or native Windows validation. Preserve the ruling that empty serial discovery did not reproduce on the measured Python runtime; do not promote the earlier static hypothesis to a repaired defect.
4. Retain the PR173 source package already in this tree, including historical failed/repaired/full/review evidence, and add the factual later delivery record when available. Historical evidence stays historical and is not copied into runtime receipts.

The new package must have its own current typed scope, obligations and reports. #165 inspection reads the selected package and explicitly referenced reports, not every archived evidence directory. Keep accounting truthful (`not_run` with reason until observed), references within its 64-file/1 MiB aggregate/256 KiB ordinary-file limits, and historical artifacts separate from current obligations. The existing full reports inspected are approximately77/81 KiB and can be retained losslessly without embedding their text in every current report.

## Handoff and closure limits

The inherited `START_HERE.md` and `PROJECT_STATE.json` still name the eight-issue PR173 predecessor. After actual delivery, coordinator-owned README/START/state must name the factual merged base, this successor's branch/package and next action; archive the predecessor delivery instead of rewriting the immutable release snapshot. Preserve VERSION2.0.18, published archive identities and architecture links. Link the declared `docs/package-status.md` and state the bounded SQL022/runner behavior in the current source handoff.

Coordinator clarified the closure scope: deliver and close **#165, #163 and #118** only after fresh combined verification, every selected independent review and exact-head external authority. **Keep #62 open** for the separate bounded App Check output source task; this candidate contributes capacity/platform work but does not fulfill that remaining issue outcome. Close retained PR135 only after its actual successor lands. Do not include an automatic closing keyword for #62. #158 Trust CI source, general capacity issue159, deployment, persistent migration execution, native Windows qualification, older-Python claims and human approval authority remain outside this integration.

Analysis is complete. RE-1 is resolved in the coordinator's manifest; RE-2 has an explicit pending delivery/route disposition. Import, integrated execution, independent review and publication remain future work owned by the coordinator and the one selected writer.
