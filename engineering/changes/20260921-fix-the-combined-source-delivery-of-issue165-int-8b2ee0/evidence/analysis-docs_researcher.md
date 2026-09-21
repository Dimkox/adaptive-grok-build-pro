# Documentation and provenance analysis — factory/tooling successor

Route `8b2ee0533ba5`; selected role `docs_researcher`; 2026-09-21. This is source and evidence analysis, not implementation, review approval, a current verification receipt, or a delivery claim. The integration worktree was observed at `23984e55560c6d559a46445061f10331ca05bcf9`; source imports remain conditional on actual PR #173 delivery. No tests, lint, compilation, product-module execution, containers, operational commands, or external writes were performed for this analysis.

## Adopted closure ruling

The coordinator accepted this clarification during analysis: this successor may auto-close **#165, #163 and #118 only after actual delivery**. **#62 remains open** because its bounded App Check Run command-output request is not implemented here. Name that remaining source task in the durable plan without inventing a successor issue/PR number. The initial combined requirements paragraph suggesting all four closures must be reconciled with this ruling before publication.

| Item | What this candidate can establish | Closure/delivery boundary |
| --- | --- | --- |
| #165 | Bounded same-worktree package diagnostics, truthful evidence accounting, and durable start/first-implementation observations. | Close after the integrated source and current gates deliver. State that no automatic publication, cross-host recovery, global worktree discovery, or proof that an author crashed was added. |
| #163 | Named existing repair-planning refusals, strict corruption separation, and additive migration 022 preserving existing function behavior. | Close after source delivery and integrated immutable-history/current-prefix evidence. Applying 022 to a deployed database is a separate operation, not a claim made by closing the source defect. |
| #118 | Unsupported parallel cleanup selects disclosed sequential execution before launch, including explicit positive worker requests. | Close after source delivery/current gates; tests emulate the capability boundary on Linux and do not qualify native Windows process cleanup. |
| #62 | Linux auto worker selection respects visible CPU quotas; collection tests use deterministic exact markers instead of requiring all requested worker PIDs to receive tiny jobs. | Partial only. Keep open with no auto-closing keyword until bounded failing-command output in the App Check Run is separately delivered. |
| PR #135 | Retained #118 source is incorporated with provenance. | Close as superseded only after the successor actually lands; retain its branch/history and link the real delivered successor. |
| #51 / #159 | No new result for either issue. | #51 concerns factory/delivery discovery and visible capability skips; it does not itself discharge #62's command-output remainder. This local batch does not establish #159's deployed throughput, queue draining, concurrency, or merge-train qualification. |

The cached original #62 body distinguishes seven historical PR #33 runner failures from an eighth reproduction artifact caused by a read-only host Git mount. It also requests bounded command output. Preserve both distinctions: do not report the old seven failures as newly reproduced, and do not silently treat the output request as implemented by capacity selection. The prior capacity research records that PR #113 already delivered capability-selected fallback for the earlier failure family.

## Exact candidate provenance

I read each candidate's clean worktree/HEAD and independently computed SHA-256 from `git show <head>:<path>` for all paths in the combined `candidates.json`. **All 18 hashes match**, with 8 paths from #165, 7 from #163 and 3 from capacity. This verifies the declared source identity only; it neither imports those files nor certifies the combined tree.

| Candidate | Exact frozen head | Durable package |
| --- | --- | --- |
| #165 | `163847842ccddacd6f179c7a3ea082765530bb84` | `engineering/changes/20260921-fix-issue-165-diagnose-unfinished-change-package-2dfd58` — `P165` below. |
| #163 | `d80c5c8d8e5afe938d195401715daf5e69192a81` | `engineering/changes/20260921-fix-issue-163-name-postgresql-semantic-plan-repa-806a83` — `P163-current`; preserved original package ends `d2e7e6` — `P163-original`. |
| #62/#118 | `08dd467d0dc9c173af01f3b47876a9a3fa1ca639` | `engineering/changes/20260921-fix-issues-62-and-118-in-python-test-runner-work-45e0cc` — `Pcapacity`. |

Retained PR #135 source is exactly `7a7851af5d11e8ce5c3af23ab46214ae7ae4cdc8`. Its runner change is9 additions/2 deletions against observed main839d3aa, with80 added test lines. The capacity candidate attributes the same platform product hunk and carries its tests with stronger exact-marker assertions. Historical PR #135 checks are not current authority.

Preserve original packages/reports or archive their exact bytes with an explicit mapping before the combined session ends. Importing source alone would discard the reasons for earlier failures, adoption of corrected code, and rollout constraints. Do not copy candidate README/START_HERE/PROJECT_STATE wholesale: each describes its own now-superseded branch and verification stage.

## Evidence accounting: #165

The current candidate has corrected-source full verification plus two renewed independent reviews, not a fresh full-tree receipt for either its final head or this integration.

| Observation | Actual result and identity |
| --- | --- |
| Initial implementation RED |20 tests,32 assertion failures including subtests,0 errors; exit1;9.787s unittest/10s shell wall. `P165/evidence/implementation-red.log.json`. |
| First focused GREEN attempt |25 tests,3 failures,0 errors; exit1. Copied fixtures omitted the canonical schema or retained an accounting key through a merge helper. The failures remain recorded. |
| Corrected initial focused run |25 tests PASS; exit0;13.066s unittest/14s shell wall. `implementation-green-2.log.json`. |
| First full run |HEAD `738ea719d91cf439d3332ce621418dc994e7365b`,09:11:56–09:20:25UTC; **overall FAIL**, exit1. Only `git-diff-check` failed, on raw RED-log trailing whitespace. Lossless JSON packaging corrected the paperwork without changing product bytes; it did not retroactively change this result. |
| First independent review wave |Code/test **FAIL**, findings CR-165-01/T165-1: raw-byte branch/path identities failed strict state serialization/readback. Original reports remain `code-review-first.md` and `test-review-first.md`. |
| Raw-byte repair |Three new lifecycle regressions first failed; corrected focused suite28 tests PASS. Only the package-status implementation and its regressions changed; strict shared parser/serializer and receipt authority were retained. |
| Corrected full run |HEAD `bca409d10d01663ee90dbd083089f41edad0b2bd`,10:17:57–10:26:15UTC; **PASS**, exit0. Report SHA256 `cdebdb7105546cf5396e91491fea9c04c902b8eaf706e096d80f67046a3b3c7a`; fingerprint `1a37c3098177239578508680ae2bfa82c326114f4df206ed4d76dcd0a47d2dae`. |
| Renewed reviews |Code/test **PASS** at `a946f3e3ac92dfd60ece94437b20406e2edd3959`; final `16384784` adds guide clarity, evidence accounting and handoff. Product/test identity is retained, but final whole-tree receipts still require refreshing. |

The corrected full report records813 root tests and1117 subtests passed;44 pilot tests with 1 skip requiring an explicitly pinned local Codex sandbox;56 factory-unit tests;779 factory/PostgreSQL tests with 2 reported skips. `workflow-artifacts` is explicitly skipped because it is unconfigured. These skips must remain visible and must not be described as executed passes. The earlier full-run summary and implementation narrative contain historical “final pending” wording; retain them as dated observations and let the new combined evidence index state the current result.

Independent digest reads matched `code-review.md`=`8168b586091267233caa145b8e1d1b95fb118e348ae0a933bfb35e5c79c2d7ae` and `test-review.md`=`ee0891d7dfadc701ff50386e265c8ec15bf17c089bf8ceb30c97f39eaf41042f`, as declared in `final-review-adoption.json`. None is an integrated review receipt.

## Evidence accounting: #163

`P163-original/evidence/implementation-candidate.json` binds the same seven source hashes declared by the combined manifest. The current-main continuation adopts those bytes and preserved analysis; it does not turn the original full failure into a pass.

| Observation | Actual result and identity |
| --- | --- |
| Offline RED |14 methods,47 assertion failures,0 errors; exit1;0.082s unittest/1.117176s wall at source `1eef8ecc1f3cdc5e397f47814cf65de14360e0c1`. |
| Offline GREEN |46 tests PASS; exit0;0.132s unittest/1.116933s wall. |
| First focused PostgreSQL run |11 of12 cases passed. One fixture failed before planning SQL because inherited execution stages totalled 390s while the task allowed 20s. |
| Corrected deadline case |Only that failed case was rerun after giving its fixture four 5-second stages; PASS in 21.503s unittest/36.766830s wall. Disposable preflight and two real PostgreSQL restart/recovery probes also passed. This is not a claim that the original 12-case command was rerun successfully. Production timeouts stayed unchanged. |
| First full run |HEAD `b4ff8e3e7a30ba8c85679c2763f209452be5d420`,09:56:23–10:05:35UTC; **overall FAIL**, exit1. Tests, lint, coverage, drift, diagrams and source stability passed; architecture fitness and dependent governance failed. |
| Actual-main diagnostic |An 8.575971s fitness check against main `839d3aa26bc90417424d814ee48d8b5cd3be367e` passed. It is a separate comparison diagnostic, not a full verification replacement or receipt. |

The failed full report (`full-initial-report.json`, SHA256 `ac1bfaffbb027691add018c5d544ac781cbc97fbf7dc4c972cbcd9e8d8644ced`) records785 root tests/1098 subtests passed,44 pilot tests with 1 skip,60 factory-unit tests and804 factory/PostgreSQL tests with 2 reported skips. Workflow artifacts were unconfigured/skipped. The root cause of full failure was the original route base9007895 counting already-delivered #155 work: factory-test complexity 601 exceeded 600 and 803562 bytes exceeded 775000. `delivery-base-ruling.md` preserves that explanation; the tool-generated current route806a83 adopts actual main839d3aa without editing old runtime authority or weakening limits.

No new full success or independent-review success is present for frozen candidate d80c5c8d. A fresh combined verifier must assess both its real target base and the route's recorded comparison base; source identity does not settle architecture budget eligibility. Do not hide a genuine combined-budget failure by importing the diagnostic result.

## Evidence accounting: #62/#118

`Pcapacity/evidence/implementation-ai_implementer.md` and the lossless JSON logs distinguish implementation evidence from full verification.

- Meaningful current-source RED:4 test methods,8 assertion failures,0 errors; exit1;1.563s unittest/1.84s wall. Nested finite quotas selected22 workers instead of2/3/1, and unsupported cleanup selected `(2, 'pytest-xdist')` instead of `(0, 'unittest-degraded')`.
- The two empty-serial-discovery methods in that same RED command **passed**. This hypothesis was not a reproduced defect. `/usr/bin/python3` executed Python 3.12; its unittest rejects zero tests with exit5. Python 3.14 source was separately inspected and has the same rule, but Python 3.14 was **not executed**. Older Python behavior remains unqualified. Serial commands/accounting were therefore preserved, with non-vacuous `Ran 0 tests` assertions retained.
- Focused GREEN: all 38 runner tests passed on the exact three manifest hashes; exit0;20.148s unittest/20.441919s wall. Scoped Ruff passed on its first attempt in0.023660s. No test was skipped in that focused run, no full suite was run, and no native Windows execution or newly deployed cgroup experiment is claimed.
- Both successful records name precommit HEAD839d3aa plus exact changed-file hashes. Commit08dd467d preserves those files. The hashes, rather than a claim that the unmodified old HEAD was tested, explain their provenance.
- Independently read evidence digests: `red-initial.json`=`59ce3520ffbfe990a9bce93f2f4a3a96a3c27a378606461719295c3de92e35b1`; `green-runner-attempt-1.json`=`82fc0dde0e7b54638455dfaa47da3f33e36a6434b0b0b2ef6cc4c944a3438e6e`; `ruff-attempt-1.json`=`f06ce2d19c34bf13117870d65ddb05f7a2a0f2e8713e43033e5d33b068457a6d`.

## Current guide and handoff requirements

1. Import `docs/package-status.md` at the exact #165 candidate hash. Its final clarification already documents UTF-8 strings versus tagged `{"encoding":"hex","value":"..."}` raw-byte identities for branch/paths,4096-byte individual limits,32768-byte encoded collection budget, and explicit `git_path_representation_limit` unknown observations. This resolves the renewed review's nonblocking guide note; do not reimport the earlier incomplete guide.
2. Preserve package status's semantic separation: bounded `complete` is not verification success; `not_run` needs a reason; a recorded failure is accounted for but not passed; unknown Git facts stay unknown. The immutable diagnostic checkpoint is separate from the route base. The observer selects one package and explicitly declared evidence references rather than crawling other packages or arbitrary historical reports. Its no-write guarantee excludes access times; lifecycle checkpoint writes are explicit, state is canonical, and failed README mirroring uses visible pending/retry recovery rather than claiming two-file crash atomicity.
3. Add a small current optional-runner explanation to the coordinator-owned README/handoff (or explicitly scoped guide), because the capacity candidate's README only contains a brief status paragraph. State config `{"schema_version":1,"workers":"auto"}` in `.grok-test-runner.json`, `GROK_TEST_WORKERS` override, accepted explicit 0–64 values, no-opt-in preserving the existing runner, and `GROK_TEST_WORKERS=0` recovery. Do not imply environment override makes an invalid configuration file valid; file validation happens first.
4. Explain that Linux `auto` takes the minimum of the 28 ceiling, positive affinity/CPU-count fallback and finite quotas reachable through actual membership/mount mapping. Fractional policy is `max(1, quota // period)`. Missing/unlimited v2 leaf controls do not stop the visible ancestor walk; malformed/unreadable/ambiguous/bounded-out evidence falls back to one worker. A visible unlimited hierarchy is not proof that invisible ancestors are unlimited, CPU time is reserved, or PID/memory capacity is available. Explicit requests are unchanged and are not quota-clamped.
5. Explain #118 as this repository's POSIX cleanup restriction, not a claim that pytest-xdist itself cannot run on Windows. Unsupported positive requests select `unittest-degraded` with effective workers 0 before execution. A failed parallel run is never retried serially. Measured sequential Core retains pinned coverage and qualifying current-run coverage; supported parallel runs retain strict existing pins and cleanup.
6. Rewrite current README/START_HERE/PROJECT_STATE around this route, actual delivered prerequisite main, the three closure candidates and partially addressed #62. Preserve VERSION2.0.18, immutable release history, runtime observations, architecture model/rules/generated-view links, and the distinction between source, installed runtime and external pilot/M8/M9 qualification. Do not publish a guessed successor PR number or treat PR #173 as delivered before its actual merge record exists.
7. The new evidence index should separately name original source heads/hashes, every measured failed/passing run and skip, imported historical reviews, and fresh integrated verification/reviews. Existing #165 accounting/report rows are historical self-reports; do not copy them into current receipts. Finish guide/checkpoint/report writes before recording the final fingerprint-bound evidence.

## Rollout and recovery claims

For #165, recovery is a reviewed revert/forward repair of diagnostic, lifecycle and template wiring. Preserve already-recorded checkpoint observations; older readers may ignore additive fields. No database migration or service installation is involved, and a locally written checkpoint still needs authorized Git publication to be available on another host.

For #163, ship the compatible reader and022 together. Migration022 changes only the existing function definition and its original privilege contract; SQL 001–021 remain immutable. Keep the 15 refusal sites / 14 SQL reasons, exact one-key rejection channel, fixed unknown fallback, legacy NULL separation, deadline `needs_human` escalation, replay and request bindings. Classification occurs after the transaction context exits. Some normal refusal returns can retain earlier writes, while the existing exception block rolls back its own work; do not summarize every refusal as write-free.

Parser compatibility does not establish rolling availability: readiness requires packaged and database migration versions to match. A later authorized operation must coordinate drain/package/migration and observe readiness. Failure during the transactional migration preserves the prior prefix for retry; after successful application, recovery uses a later forward migration rather than editing/deleting 022 or ledger rows. Preserve both the historical020→021 fixture from173/#166 and actual021→022 populated upgrade/replay/contention evidence. Unreachable valid-fixture branches retain immutable whole-body/site proof; do not claim every guard was executed at runtime.

For capacity, existing explicit sequential mode is the operational workaround for a source regression. Source repair needs no database, new dependency, service, image, deployed policy or trust-store change. Selected/effective worker count, engine and exit results are local observations; this branch does not publish App Check Run command output or establish spare host capacity.

## Trust and primary-source boundaries

PR #173's #162 fix concerns local seven-kind vocabulary parity. The unchanged `trust-ci/src/adaptive_trust_ci/runner.py:32` and `trust-ci/holdout.example/change_spec_validate.py:27` still declare the older five kinds: verification/code/test/security/release. Their source successor and any deployed validation rollout stay separate. Use currently compatible typed references without relabelling actual data review; this combined route still requires a real data review/report/receipt, along with code/test/security/release. No Trust CI source, deployed holdout/policy/image, approval or key is in these imports.

The capacity analysis already includes the relevant primary documentation; no additional factual gap required browsing. Its archived `analysis-docs_researcher.md` has SHA256 `1f36fbdcc4fb0a32fea6caa32881a2da5afeeb552a10fa2617e4f4178ab3d96a`. Reuse its citations with the following bounded interpretation:

- [Kernel cgroup v2 CPU interface](https://docs.kernel.org/admin-guide/cgroup-v2.html#cpu) and [delegation model](https://docs.kernel.org/admin-guide/cgroup-v2.html#model-of-delegation) support quota/period and hierarchical restrictions; they do not prescribe the repository's worker rounding policy.
- [Kernel CFS bandwidth management](https://docs.kernel.org/scheduler/sched-bwc.html#management) and [hierarchical considerations](https://docs.kernel.org/scheduler/sched-bwc.html#hierarchical-considerations) support v1 quota/period and parent throttling. A quota is aggregate CPU time, not guaranteed throughput.
- [Linux cgroups membership](https://man7.org/linux/man-pages/man7/cgroups.7.html#NOTES), [mountinfo identity](https://man7.org/linux/man-pages/man5/proc_pid_mountinfo.5.html#DESCRIPTION), and [cgroup namespaces](https://man7.org/linux/man-pages/man7/cgroup_namespaces.7.html#DESCRIPTION) explain why actual controller membership, mount-root mapping and visible ancestors matter. Rejecting ambiguous traversal views conservatively is product policy, not a claim those namespace layouts cannot exist.

After actual PR #173 delivery, the coordinator must fetch and bind the real merged tree/base before the sole writer imports source. The current route's recorded base 839d3aa stays historical authority until legitimately routed otherwise; never hand-edit it. Only fresh integrated verification, all five selected independent reviews, current receipts and the exact App-owned external head/base check plus required scopes can qualify this successor for merge.

Shared-memory fact for coordinator adoption: exact source hashes allow reuse of historical measurements as provenance while preserving their failed runs and skips; they do not allow receipt reuse. The failed #163 historical-base fitness run is the concrete reason to keep source identity and current comparison-base eligibility separate.
