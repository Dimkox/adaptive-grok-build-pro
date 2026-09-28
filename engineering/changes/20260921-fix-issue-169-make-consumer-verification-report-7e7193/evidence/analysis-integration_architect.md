# Integration analysis — issue #169

## Identity and evidence boundary

- Role: route-selected `integration_architect`; route `7e7193c77d53`.
- Worktree: `/home/pall/grok-projects/adaptive-grok-build-consumer-coverage`.
- Observed source HEAD and route base: `21ced3709dff48abf3e15aff62e2493de75f2fa0`.
- Read the engineering contract, entrypoints, actual route, active brief, archived issue #169, prior consumer-coverage design, and relevant source/tests. Applied `adaptive-delivery`, `bugfix-workflow`, and `api-event-change` for this read-only analysis. The parent owns bootstrap/fetch, execution, implementation, reviews and delivery.
- This report is source inspection and a compatibility proposal, not an implementation, executed regression result, review approval, receipt, or external attestation. No tests, lint, compilation, native toolchain, Docker, dependency installation, deployment, credentials or external writes were used. The only authored file is this report.
- The inherited `START_HERE.md` / `PROJECT_STATE.json` still describe the earlier factory/tooling delivery; the actual route and this worktree's brief explicitly establish the new #169 analysis scope. Preserve the historical handoff and let the parent update current delivery fields after synthesis.

## Recommendation

Keep the live report and receipt status vocabulary `pass|fail`, keep check status `pass|fail|skip`, and add one required `product-coverage` check. Uncovered relevant product changes, unknown inventory, or unprovable analyzer scope make that check fail with the machine-readable finding code `incomplete_product_coverage`. This changes the previously misleading green result through the existing CLI/receipt failure path without adding an overall `incomplete` status or changing Trust CI status enums.

Use the intersection of required changed paths and observed analyzer paths as the evidence. Installed-stack checks cannot qualify unrelated consumer files through that intersection; no new installation identity registry or blanket directory exemption is needed. A source file in `scripts`, `tests`, `engineering` or `factory` remains eligible for a product obligation. In this repository the stack modules themselves are product; directory labels can explain scope, but must not exempt changed source from it.

## Current producer/consumer map

| Boundary | Source facts | Compatible #169 treatment |
| --- | --- | --- |
| Check producer | `verification.py:31` defines `CheckResult`; `to_dict()` serializes all dataclass fields. Existing `details` is `list[dict[str, str]]`. `_command_check` at line 353 treats process exit 0 as pass and retains only the final 12,000 characters of each output stream. | Preserve existing check fields and statuses. Use existing string finding fields for the actionable failure; place structured counts/path sets in additive report metadata. Parse and validate analyzer scope before output tails are discarded. Missing, malformed, truncated or unavailable scope is unknown, never zero proven failures or complete coverage. |
| Check selection | `verify()` at line 1070 always selects base/spec/architecture/governance/workflow/secret/contracts/SQL and `_python`; PHP/Bitrix/frontend have additional selection. `.grok-stack/config/quality-profiles/*.json` describes required/optional checks, but `verify()` does not generically interpret their arrays. | The coverage gate must be invoked in the real verification path; merely adding a profile JSON entry does not enforce it. Preserve optional irrelevant checks. Do not create a generic checker registry in this repair. |
| Live report | `verification.py:1134-1160` sets `schema_version=1`, `status=pass` unless any check fails, and serializes `changed_files`, inventory, profiles and checks. The source tree has no dedicated live-verifier JSON schema. | Add an explicit versioned `product_coverage` object while preserving current top-level fields and status semantics. Append the required coverage failure before the verdict is formed. Existing failures must remain visible. |
| CLI | `scripts/grok_verify.py:21-30` renders every check's status, summary, finding path/message, prints `RESULT`, and exits 0 only for report `pass`. JSON uses `ensure_ascii=True`. | A failed coverage check already yields `RESULT: FAIL` and exit 1 in both modes. Put the reason and safe remedy in summary/message, since text mode does not independently print finding `code`. Preserve escaped JSON and render hostile/non-UTF-8/control-character filenames safely and boundedly. |
| Receipt writer | `receipts.py:502-568` preserves route/spec/architecture/governance/tree bindings; `verify()` passes the entire report as receipt `details`. | The new scope metadata automatically round-trips in `details.product_coverage`. Do not add an evidence kind, alter signature/authority, or promote unknown coverage to a passing receipt. Preserve `--no-record`. Integrate with the separately delivered lifecycle finalizer rather than replacing it. |
| Receipt validators and local gates | `receipts.py:643-730` requires receipt status `pass|fail`; any non-pass is an evidence gap. `scripts/grok_status.py`, `.grok/hooks/stop_gate.py`, `deploy.py`, `grok_artifacts.py` and workflow validation consume `validate_evidence()`. | A normal failed verification receipt propagates the existing gap. Additive report metadata does not require changes to these consumers. A stale prior pass must not survive a new failed run; that persistence behavior is owned by the lifecycle branch and must be preserved after its actual delivery. |
| Demo/sample schema | `summarize_verification_report()` at line 1026 accepts exactly `schema_version`, `sample_id`, `status=sample_evidence`, and checks containing exactly name/status/summary. `tests/test_demo.py:184` intentionally rejects unknown fields and permits optional skipped samples. | This is a distinct sample format, not a validator for live verifier reports. Do not relax it, add live scope metadata to its fixtures, or make its optional skip fail as a shortcut. |
| Trust CI command adapter | The repository policy **example** invokes `python3 scripts/grok_verify.py --mode pr --no-record --json`. `runner.py:543-584` executes a `CommandSpec`, verifies unchanged source, and consumes `CommandResult.status`; `sandbox.py:197-207` derives status from exit code and stores bounded output plus its digest. | CLI exit 1 becomes a failed Trust CI command through existing behavior. No live-report JSON parser or receipt import was found in this path. There is no need to change the runner, policy example, deployed policy, App configuration, image, database or holdout to transmit failure. This does not claim what any deployed consumer policy actually runs. |
| External schemas/holdout | `trust-ci-attestation-envelope.v1.json` uses command `pass|fail` and attestation `passed|failed`. `holdout.example/validate.py` checks source/typed specs. `change_spec_validate.py` validates a closed receipt-kind set for typed-spec evidence references. | Keep those enums and evidence kinds unchanged. Use existing `verification`, `code_review`, `test_review` mappings. Additive local metadata is not an external attestation, signed approval or merge authority. |

## Minimum additive metadata contract

The writer and architect should freeze exact field names before implementation. A bounded object of the following shape is sufficient; it is not an instruction to introduce a new status enum:

```json
{
  "product_coverage": {
    "schema_version": 1,
    "complete": false,
    "inventory_complete": true,
    "required_changed_file_count": 2,
    "covered_changed_file_count": 1,
    "uncovered_changed_file_count": 1,
    "reasons": ["unsupported_language"],
    "uncovered_samples": [{"path": "Sources/Game.swift", "language": "swift"}],
    "omitted_sample_count": 0,
    "checks": [
      {
        "name": "ruff",
        "applicability": "applicable",
        "scope_known": true,
        "selected_file_count": 1,
        "matched_changed_file_count": 1
      }
    ]
  }
}
```

Constraints for the frozen contract:

1. Counts mean files, not LOC or a statement that all behavior was tested. Distinguish proposed targets, actual tool-selected files, covered changed files, and tool success. A nonzero count elsewhere in the stack does not cover an excluded consumer file.
2. Retain tool/check identity and the inventory's exact comparison-base provenance. Any uncertainty in enumeration or analyzer output prevents `complete=true`. A scan limit may report a bounded lower bound, but cannot silently turn a partial inventory into a complete one; choose an explicit unknown/null count representation where needed.
3. Bound the number of per-check rows, samples, reason codes, path display length and total metadata bytes. Compute required-set coverage using the complete bounded internal inventory, not the display sample. Overflow is visible and non-green, not a truncation that weakens the gate.
4. Use a finite reason vocabulary, for example unsupported language, missing applicable tool, empty selected scope, partial selected scope, unknown inventory and invalid scope output. The gate's stable public code is `incomplete_product_coverage`; specific reason fields explain the repair.
5. Keep optional irrelevant checks as `skip` with a not-applicable reason. For empty contract/SQL scope, report no applicable files rather than implying substantive product validation. Missing Ruff/Bandit may remain a check-level skip for compatibility, while the aggregate fails if this leaves a relevant requirement uncovered.
6. Preserve real analyzer failure statuses even when all files were selected. Selection completeness and clean-check success are different facts; coverage metadata cannot replace genuine diagnostics.
7. Generic successful unittest/pytest, Composer or `npm run` commands have no per-source-file scope proof in the current implementation. Treat that relationship as unknown; do not assign every changed source to an opaque command merely because the process exits 0. Per-file checks such as current PHP lint can establish precise scoped evidence. A future opaque/native checker contract is separate work unless the parent explicitly accepts a bounded design now.
8. A Swift source tree with no applicable supported checker must produce an actionable failure. State the unavailable verification and configured scope that needs attention; never run Swift/Xcode/package scripts or install tools merely to classify it. Native assets such as PNG/TMX and Apple bundles are not Python LOC and must not receive inferred build/runtime validity from an adjacent linter. Document exactly which source/resource classes the first gate qualifies.

The current CLI finding can remain entirely string-valued, for example `severity=error`, `code=incomplete_product_coverage`, escaped `path=Sources/Game.swift`, and `message=No applicable check established coverage for this changed Swift source; use an appropriate reviewed product check before claiming verification.` A generic “install a missing package” instruction must not be emitted when the actual problem is a consumer exclusion or unsupported platform.

## Inventory and installation hazards

- `_changed_file_inventory()` at `verification.py:545` unions worktree, route-base and locally selected PR-base ranges. Preserve this union: checking only staged/unstaged files would lose committed product changes and checking only the route base would lose the independent PR-target range.
- `util.changed_files()` at line 160 returns paths but suppresses individual `_git_paths()` failures; `[]` alone does not establish complete absence. The new bounded coverage inventory needs explicit failure/limit provenance. No Git, an unborn repository, invalid base, unavailable range, malformed NUL output, and permission failure need deliberate handling, not an empty-success fallback.
- Existing Git enumeration uses raw NUL-delimited bytes, filesystem decoding, no-renames, and preserves tracked scratch-looking paths. Retain this identity contract. Deletions have no present analyzer file; classify them explicitly instead of attempting a read or silently losing them. Renames across a scope boundary must preserve destination and relevant removal obligations. Symlinks/special files are not permission to traverse outside the root.
- `QUALITY_PY_PATHS` is an upstream-oriented fixed list (`verification.py:815-838`). It does not include arbitrary consumer source directories. Current Ruff/Bandit calls cannot establish consumer coverage just from exit 0; both target selection and tool exclusions matter.
- The actual installer explicitly delivers `ruff.toml`, `bandit.yaml`, `.coveragerc`. Their current source excludes `engineering`; `.coveragerc` measures only stack modules and `scripts`. They are real source facts behind the archived issue, but this analysis did not execute the reported external consumer or fetch its secret gist.
- `scripts/install_into.py:17-97` owns whole managed directories plus individual files. `scripts/` is not itself a wholesale managed directory, and `factory/src` can contain additional consumer code. Installer ownership is not analyzer scope and must not be used as a coverage exemption.
- `.grok-stack/AGBP_SYNC.json` is a consumer `kept_local` declaration with only `schema_version` and `kept_local`, not a delivered source inventory. The install plan exposes per-file hashes, but is not automatically persisted as a universal consumer identity registry. Do not invent that guarantee or import `scripts/install_into.py` from installed consumers: that installer script is not in the managed-file payload.
- Existing-target installation is read-only planning; `--force` is rejected and dependency advice does not execute installers. Preserve those protections and the consumer's exact lint/coverage/routing bytes. #169 can make misleading defaults honest without automatically rewriting them. If new-install defaults or disclosure text change, update the actual installed template and installation fixtures, not only the upstream README.

## Compatibility and acceptance matrix

These are proposed regression obligations for the parent's test plan, not executed results or final typed IDs.

| Obligation | Required positive/negative controls | Existing compatibility to retain |
| --- | --- | --- |
| Non-green vacuous scope | Installed-style Python product under `engineering`; real applicable analyzer excludes all/part of changed product; unrelated stack scope nonempty; zero/partial scope fails. Matching included fixture passes and a deliberately invalid included file fails its analyzer. | Existing Ruff/Bandit defect propagation in `QualityContourTests`; an exit-only fake must not masquerade as real scope evidence. |
| Unknown/native product | Pure Swift, mixed Swift/Python, nested source, unsupported source language; Python success cannot cover Swift. No native execution during discovery. | Swift detection is #157; #169 consumes only its actually delivered interfaces. Existing recognized language/domain behavior remains intact. |
| Truthful change inventory | Committed route and PR-target union, staged/unstaged/untracked file, deletion/rename, unknown base, Git error, non-UTF-8/control bytes, overflow, symlink/special file. | `test_pr_changed_file_inventory_unions_route_and_local_target_ranges`, base-selection failure tests, and `test_receipt_roundtrips_non_utf8_changed_file_names`. Do not widen tracked-path exclusions. |
| Optional relevance | No SQL/contracts, no product-source changes, missing irrelevant optional tool, docs-only route: no automatic failure solely from an irrelevant skip. Missing applicable tool and unsupported/unknown coverage fail the aggregate. | `test_missing_ruff_is_skip_not_fail`, `test_missing_bandit_is_skip_and_secret_scan_remains`, Semgrep/Trivy optional tests, coverage fast-mode/optional behavior. Preserve these check-level contracts without preserving a false overall pass. |
| CLI/report/receipt | Text prints reason/remedy; JSON retains schema 1 and pass/fail; exit 1 for incomplete coverage; report metadata survives receipt details; `--no-record` writes nothing; failed run cannot leave usable old success. | `test_verify_records_receipt_for_active_route`, receipt status/binding/staleness tests, `test_contour_route_change_verify_review_has_no_evidence_gaps`, lifecycle failure/cancellation persistence once delivered. |
| No schema spillover | Live metadata does not modify strict demo/sample shape, external command enum or receipt-kind declarations. | `VerificationSummaryTests.test_report_summary_counts_real_checks_and_rejects_unknown_fields`; Trust CI signed command-failure/source-integrity behavior. No external schema migration is required for the proposed path. |
| Installed consumer behavior | Use an actual planned/materialized consumer payload plus product files; preserve all user config bytes during verification and existing-target planning; demonstrate actionable exclusions rather than automatic config rewriting. | Installer keep-list, deterministic portable templates, read-only target, exact manifest payload, no-follow bounds and rejected force tests. `project_copy()` alone omits many actual installed scripts/factory payload paths and is not complete install acceptance. |
| Finalizer and bounded work | Scope parsing failure, missing command, timeout, repeated cancellation and source mutation keep the existing failure/cleanup semantics. Neither scope collection nor display materializes unbounded file/output inventories. | Integrate after lifecycle and doctor delivery; preserve source-stability, negative receipt, process ownership, preflight early exit and collection diagnostics. |

The initial implementation need not broaden full factory discovery, prove an unexecuted native project build, replace tests with file counts, or infer that arbitrary assets received semantic validation. The typed acceptance criteria must state this boundary before code is written. Test fixture adjustments must add realistic scope evidence where behavior depends on it; do not weaken assertions or globally mock the new gate to regain old green contours.

## Related issues and actual-parent integration order

| Related work | Owned outcome and integration boundary |
| --- | --- |
| #51 / #63 | Full factory/delivery test discovery, tier/module accounting and runtime coverage are their scope. Current four-module `factory-unit` and repository-sandbox PostgreSQL skip are factual gaps, but expanding them is not a substitute for consumer path coverage and is not required in this repair. Keep the issues open unless their own source and deployed obligations are proved. |
| #167 | A future isolated static landing profile must use complete change eligibility and actual validators for changed HTML/assets. #169 should expose reusable truthful scope metadata; it must not introduce that fast path, exempt generated products, or treat the existing showcase test as proof for arbitrary landings. Mixed/unknown scope stays on full verification there. |
| #157 | Passive Swift/Apple detection changes repo/router/doctor metadata. Wait for actually delivered source, then use its real interface and reroute on the updated parent if necessary. Never copy unpublished sibling helpers or claim routing detection means verification. |
| #50 / #57 / #54 doctor slice | Earlier architecture validation, interpreter/dependency readiness, collection diagnostics and optional read-only Git audit overlap verifier helpers. Scope applicability is distinct from readiness: an installed tool can still exclude all product files. Preserve the accepted doctor preflight ordering and finite process budgets after actual delivery. |
| #59 / #95 / #119 / #128 lifecycle | Working-directory identity, locked dependency checking, cancellation/negative reports, child/Docker cleanup and progress paths overlap `verification.py`, `util.py` and receipts. This branch must integrate the delivered parent before editing those paths; no old sibling receipt or successful focused result is current evidence for the merged composition. |
| #110 / delivered #161 | Consumer ownership and portable installed documentation stay intact. No automatic configuration overwrite or upstream milestone copy. A new mandatory native toolchain is not an implied requirement of this source fix. |

Read-only analysis can proceed now. Before implementation, fetch/observe actual delivered parents, reconcile their changes normally, regenerate a real route if required, preserve adopted report provenance, and run fresh verification for the actual composition. No early sibling adoption is proposed.

## Rollout, rollback and closure obligations

1. Freeze a bounded metadata/check contract and concrete typed criteria in this package. Use the sole selected `general_implementer`; the initial source implementation should remain local to scope extraction, verifier integration, necessary CLI disclosure, tests and installed documentation/defaults only if the parent accepts them.
2. Run the negative/positive consumer and compatibility fixtures in the parent's serialized lane, then `python3 scripts/grok_verify.py --mode pr` and both independent route reviewers. Bind current receipts after the final tree is frozen. Inspect all regressions before changing fake-command fixtures.
3. Deliver through an isolated PR and require the current App-owned policy-epoch check on the exact head/current base plus any actual external approval scopes. Repository policy examples and this report cannot establish deployed policy or merge authority. No service, data migration, human key, operator action or native toolchain installation is part of this analysis.
4. Explain the intentional observable change: previously unqualified product modifications now fail with path/language/tool/configuration reasons, while unrelated optional skips remain allowed. This is compatible serialization with stricter truthfulness, not a promise that every historic consumer still prints green.
5. Existing consumers receive source changes through their normal reviewed update process. Keep their config bytes and provide a bounded remedy for exclusions or unsupported checks. No automatic refresh or configuration reset is required. A source merge does not prove deployed consumer adoption or a platform-specific native build.
6. Source rollback can revert the scope gate and additive metadata without data migration; preserve delivered lifecycle/process/locked-read fixes. Record that rollback removes the new coverage guarantee and never reuse the old pass as proof of product coverage. Old receipts become stale through normal fingerprint binding.
7. Close #169 only after its accepted source outcome is actually delivered with real consumer regression evidence. Do not close #51, #63, #167, pending native-operational qualification, or sibling issues through this report.

## Follow-up: can current test results qualify changed test files?

The parent requested this additional static inspection because Bandit and the Core coverage configuration deliberately omit tests. Requiring every changed Python source to appear in Bandit would therefore block ordinary source development, while treating the `tests/` directory as exempt would recreate the consumer blind spot. The independently researched Ruff candidate list also cannot supply that missing positive proof: the docs researcher's tagged implementation analysis identifies a later lint-exclusion stage.

### What the actual runner currently exports

`python_test_runner.py:90-106` defines `ProcessResult(command, returncode, stdout, stderr, seconds)` and `CoreTestRun(tests, coverage, workers, versions, coverage_metadata)`. Neither contains executed test IDs, source modules, node IDs, file paths, skip outcomes, or a scoped test manifest.

| Existing lane | Returned provenance | What it cannot prove |
| --- | --- | --- |
| Opt-in Core xdist | `_pytest_command()` invokes pytest with `-q`, controlled plugins/root/import mode, distribution and `tests`; `execute()` returns bounded process output. | Argument `tests` and exit 0 do not identify which changed module actually executed or whether a particular file had only skips. |
| Opt-in Core sequential | `run_core_tests()` uses `python -m unittest discover -s tests`; measured mode prefixes this with coverage. | Default nonverbose unittest output has no complete executed module/file inventory. A successful loader can omit a nested file or discover no relevant test. |
| Opt-in Core measured coverage | `run_core_tests():274-290` reads this invocation's private `coverage.json`, verifies nonempty `files` and expected branch mode, then stores only `totals`, `branch_coverage`, and sorted file keys. | Coverage source discovery may include unexecuted files. File-key presence alone is not positive execution evidence. Per-file `executed_lines`/summary are discarded. The root `.coveragerc` both restricts source and omits `tests/*`, so this output cannot recover test-file execution after the fact. |
| Legacy unittest/coverage | `_python()` executes coverage/unittest commands directly through `_command_check`; the coverage report is text, with no JSON export in this branch. | It has even less structured scope provenance than the opt-in runner. Opt-in-only instrumentation would not repair default CLI behavior. |
| Consumer-owned pytest | The project-marker branch runs `pytest -q`, keeps its authority and returns early from `_python()`. | No current-run node/file outcome metadata exists; a successful consumer runner must not implicitly cover all Python files. |
| Pilot and factory lanes | Pilot uses verbose discovery; factory selects four module names and the disposable harness has a separate process. | Named command inputs or arbitrary output tails are not a complete executed-file proof. Expanding factory discovery still belongs to #51, and a skipped database lane cannot supply product coverage. |

Current coverage also explicitly fails qualification when the export fails, the tests fail, or a worker fails to return coverage. Retain that behavior. Do not count a coverage JSON file key as successful execution merely because its document came from a fresh temporary directory; freshness proves invocation ownership, not file execution.

### Smallest honest test-lane extension, if accepted

There is **no already available runner fact** that can be safely re-labelled to solve this gap. A bounded extension could collect actual same-invocation test outcomes through a controlled unittest result adapter and pytest runtest-report adapter, then expose additive execution metadata. It must cover the default sequential path as well as opt-in xdist; otherwise the external default CLI remains unable to qualify changed tests.

The useful unit is an actual non-skipped completed test case tied to its source file inside this checkout, with per-file executed/skipped/failed counts and an explicit completeness flag. Use real result callbacks, not a second collection run, command argv, glob selection, import presence, test-module-looking names, or stdout-tail guesses. All-skipped modules, collection errors, dropped worker results, malformed/oversized/missing metadata and cancellation cannot qualify a file. Keep the runner's original exit status and never rerun failing tests to gain scope evidence.

The metadata must live in a private invocation-owned temporary path outside the product tree, be bounded/validated, and survive long enough for the parent verifier to inspect it before cleanup. Final reporting should distinguish `test_case_executed` from analyzer inspection and from line/branch coverage. An executed case demonstrates an applicable test check, not that every line in its file was exercised. Keep the already delivered lifecycle cancellation/result callbacks, child cleanup, signal exit mappings and source-stability behavior intact when integrating this extension.

This extension can qualify changed test modules that actually execute. It **does not automatically qualify helper-only modules** such as `tests/_support.py`, fixture data, skipped-only tests, or unrelated product modules imported by tests. Those need actual analyzer evidence or actual qualified execution coverage; changing root coverage source/omit rules, importing consumer modules for detection, a syntax-only fallback, and exempting test/managed directories are not equivalent repairs. If the first design cannot support these cases, state the residual and fail honestly rather than claiming universal Python support.

A narrower alternative is a demonstrably complete positive Ruff adapter under a finite supported configuration/tool-version contract. That is not available from the current candidate-list fact alone and must preserve consumer exclusion semantics; it cannot silently override force exclusions or reset rules. The parent should compare these bounded source options before dispatching implementation. Introducing a general plugin registry or treating upstream repository identity as permission to bypass scope is unnecessary.

### Consumer identity result

There is no trustworthy installed-consumer discriminator in the inspected installer state. `.grok-stack` exists in both source and consumers; `AGBP_SYNC.json` only declares kept-local paths; upstream names, remote URLs, `VERSION`, copied templates, directory names and presence of factory code are not a defensible bypass. Keep qualification based on actual changed-path/check intersections in both source and consumer trees.

## Pattern lesson for shared memory

Trace the verdict through every consumer before adding a status: this tree already transports a required failed check through CLI exit codes, fingerprint-bound receipts and Trust CI command results. Keeping additive scope metadata inside that path isolates the truthfulness repair from strict sample schemas and external attestation enums; the parent can promote this lesson to `decisions.md` when implementation evidence confirms it.
