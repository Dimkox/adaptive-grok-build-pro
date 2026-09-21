# Independent test re-review — PASS

Reviewer: selected `test_reviewer`, route `bcc1d645c438`, 2026-09-21. Reviewed base `839d3aa26bc90417424d814ee48d8b5cd3be367e` through frozen head `af7fb4ad3436e9c98cb7f07e570b7ff7e649207e` in `/home/pall/grok-projects/adaptive-grok-build-reviewed-batch`. The reviewer did not implement the change. This is local preflight evidence, not external merge authority.

**PASS.** Prior P1 finding T1 is resolved by a bounded security-alias repair and meaningful regression assertions. No remaining blocking test-adequacy finding was identified in the integrated eight-issue source. The original FAIL remains unchanged in [test-review-first.md](test-review-first.md), SHA-256 `c67a2a84d8a84e401be8c218c387875e705ca15dfed206c3e09d9b545e1a77aa`; it is not relabeled as a passing review.

## T1 resolution and regression strength

Sources: `.grok-stack/adaptive_grok/router.py:40`, `:241`, `:286`, `:322`, `:395`, `:428`, `:451`, `:458`; `tests/test_repo_router.py:46`, `:89`, `:99`.

The finite alias table explicitly recognizes authentication/authorization forms, US/British spellings, `authn`, `authz` and `ролью`. Each alias uses the same Unicode word-boundary predicate as the configured short term. Other domain matching, risk calculation, owner selection, reviews and gates are unchanged. Aliases report the canonical configured keyword (`auth` or `роль`), so they neither copy unbounded prompt input into the new metadata nor multiply the keyword score when several aliases appear. This interpretation is documented in source and the repair record.

The positive regression uses literal expectations independent of the alias table and calls the real route builder in empty repositories. It asserts no repository-derived domain exists, then checks 42 prompts covering existing standalone controls, the reported longforms, representative inflections, uppercase and punctuation. Each route must have exactly the security task/domain, high risk and high-risk complexity, the existing general writer, security workflow skill, security/release reviewers and receipts, and the scope/design gate. Supported base/fingerprint overrides only remove irrelevant Git metadata work; they do not mock domain matching or obligation selection.

The second method calls `is_development_prompt` with eight neutral observations, avoiding an implementation-intent shortcut such as `Fix`. The third checks thirteen unrelated or embedded words (`author`, `authority`, `authorship`, `authentic`, `xauthentication`, `authorizationx`, underscore-adjacent aliases and `гастролью`, among others); both routing and neutral prompt detection must remain generic/non-security. The original embedded-short-token and specialist/persistence tests remain present. These controls directly address the previous green-suite blind spot.

Read [router-security-repair/red.json](router-security-repair/red.json): the same three methods, before the product repair, exited 1 with **46 assertion failures and no errors**. The failed headers and output identify lost route obligations and neutral-prompt detection; the four existing standalone positive cases and negative controls did not manufacture a setup failure. [green.json](router-security-repair/green.json) records the three methods passing, exit 0; [adjacent.json](router-security-repair/adjacent.json) records **61 router/artifact tests passing**, exit 0. Both GREEN records preserve their before/after fingerprint and file hashes.

The current source hashes independently read during this review match those GREEN records:

| File | SHA-256 |
| --- | --- |
| `.grok-stack/adaptive_grok/router.py` | `cc8a7e973657ad1d1664dc250c4bc09cda04e3c077e296171db99ac3f779e4ac` |
| `tests/test_repo_router.py` | `fba5d5d6b78cf00bef25bfa0ca20a113e66eb112da1e622e455081a8887e7a3d` |

The tests cover representative forms of the finite vocabulary, rather than claiming unrestricted language recognition. Additional listed plurals/inflections use the same inspected word-matching path; returning to a general `auth` substring is not required and would fail the negative controls.

## Integrated test coverage retained

The full 19-path product/test diff and its surrounding implementation were inspected in the first review. This renewal inspected the complete repair delta and statically confirmed that the other 17 paths remain identical to that reviewed source. The integrated conclusions below therefore apply to the frozen head, with T1 corrected.

| Area | Actual assertions and boundaries |
| --- | --- |
| #156 router/runtime reader | `tests/test_repo_router.py:126` onward retains exact archived #155 wording, embedded-token negatives, punctuation/Unicode neighbors, specialist routing, phrase/stem ordering, repository fallback and route/archive/change-package persistence. `tests/test_workflow_artifacts.py:36`, `:50` accept old/empty/new optional metadata and refuse malformed, oversized, duplicate or non-NFC values and unknown top-level fields. The added security tests close T1 without changing this reader. |
| #162 receipt schema | `tests/test_change_spec.py:98`, `:107`, `:117` compare the enum against both runtime registries, validate complete specs for every runtime kind and reject an unknown kind. This establishes local schema compatibility only; the separate Trust CI vocabulary successor remains excluded. |
| #153/#161 installer | `tests/test_installer.py:81`, `:95`, `:128`, `:148`, `:173`, `:756`, `:817` exercise materialized generic/Bitrix documents, missing/escaping-link controls, deterministic output and manifest hashes, explicit reusable template inputs, read-only existing-target planning, preserved arbitrary user bytes, kept-local conflicts and descriptor safety. The relocation test has a successful unrelocated control and an exact binding-refusal diagnostic. |
| #168 fingerprint/receipts | `tests/test_util_fingerprint.py:48` onward covers real Git ownership, staging, tracked noise edits/deletions, recreated staged deletion, rename endpoints, base-relative deletion, configuration/lookalikes, tracking/diff failures, unborn/non-Git repositories, literal backslashes and byte-valued names/targets. `tests/test_change_receipts.py:585`, `:607` check actual receipt validity during scratch churn, staleness on concurrent product changes and non-UTF-8 filename roundtrip. |
| #147/#148 schema references | `tests/test_architecture_model.py:2946`, `:2986`, `:3009` distinguish real-path narrowing from ID claimants, including duplicate/same-target IDs, nested paths/fragments and unsafe-looking registered aliases with no-ID/duplicate refusal controls. `tests/test_architecture_fitness.py:4315`, `:4414`, `:4946`, `:4977`, `:4986`, `:5001` retain both closure candidates, check raw and final diagnostic expansion at zero/one/five/eight unique entries, exact omitted counts, independent referrers, out-of-scope silence, inherited signals and late head-only fatal ambiguity after the presentation limit. |
| #166 current PostgreSQL prefix | `factory/tests/test_execution_persistence_postgres.py:1849` onward uses real packaged 001–020 SQL/ledger identities and actual 021 application. Assertions bind prior ledger timestamps, six populated tables, function OID/owner/ACL/SECURITY DEFINER/search path, effective privileges, old/new rejection behavior and idempotence. A deliberately corrupted real ledger digest must fail without changing the snapshot, then restoration permits upgrade. Contention tests observe the exact advisory blocker before release-success or timeout/unchanged-snapshot/retry checks. |

Cross-component assertions remain meaningful: new routing metadata passes the strict reader and persistence path; escaped filesystem identities pass actual receipt validation; installed template inputs reproduce the generic payload; schema precedence is evaluated together with conservative closure and presentation limits. Historical RED/control evidence inspected during the first review remains preserved, including the installer fixture repair, fingerprint byte-path repair and schema fallback repair. Their corrected individual full runs are not invented or inferred from earlier initial passes.

## Actual corrected full verification

[combined-full-security-repair-meta.json](combined-full-security-repair-meta.json) records `GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr --json` at tested head `28514bf0e3d7aa1812aa7d459136f0ca60989885`, exit **0**, from `2026-09-21T10:29:00.108421+00:00` to `2026-09-21T10:37:44.736961+00:00`. The inspected [report](combined-full-security-repair-report.json) records route `bcc1d645c438`, PR mode, `base/contracts/data/integration` profiles, both route/target bases at `839d3aa26bc90417424d814ee48d8b5cd3be367e`, and stable fingerprint `3937be09e0f83ba702cd3f50675e6ce01a850620497e02e57d0035b49e0e26ad`.

The report's independently read SHA-256 is `cb43ed9a06b748693414e4a55e5fa279e759a321454a7868f46b47971271ed4c`, matching the stored [result](combined-full-security-repair-result.json). Results are:

- **831 root tests and 1331 subtests passed**, with two reported warnings; coverage **80.29%** against the 74% threshold.
- **44 pilot tests**, with **one skip** requiring an explicit pinned local Codex sandbox. That sandbox test is not claimed as executed.
- **56 factory unit tests passed** in the direct unit check.
- **782 factory-wide tests** under disposable PostgreSQL, with **two recorded skips**, followed by the recorded actual restart/reconciliation check. This is not a claim of 782 PostgreSQL-only cases. The stored factory stderr is a tail and does not identify the two skipped methods or individually list the three prefix tests; the preserved zero-skip focused prefix log and unchanged full-discovery command provide the latter evidence.
- All applicable static/spec/architecture/governance checks and source stability passed. The separate workflow-artifacts profile check remains **skipped because it is unconfigured**; runtime-reader unit coverage is present.

This corrected full run supersedes the earlier `4bbbad34` full result for the repaired source. The original documentation-related failed full run, original first-review failures and initial candidate runs remain historical facts, not retrospectively passing evidence.

## Read-only checks and limitations

`git diff --exit-code` confirmed all 19 product/test paths are identical between tested `28514bf0` and reviewed `af7fb4ad`, and between reviewed head and the working tree. A separate comparison confirmed the other 17 paths are unchanged since the first review; only router source and router tests intentionally differ from the imported candidates, as the separate integration-correction record declares. The full tested-to-reviewed commit delta contains only handoff/evidence/state/task documentation.

Base-to-head comparison returned zero for Trust CI source, all factory production source/resources, the disposable runner/restart probe, architecture model/rules/generated views and GitHub workflows. No migration022 or separate #162 trusted-validator implementation is included. Read the active route, updated scope, handoff, preserved first review, source-identity correction, measured RED/GREEN records and actual corrected full report. No tests, imports/probes, lint, compilation, Docker, database commands, subagents or external operations were executed during this review. No source, receipt, grant or commit was changed; this renewed report is the only write.

Residual limitations do not block this bounded source repair:

- The prefix contention tests assume a three-second observation window, twelve-second worker join and under-fifteen-second observed duration against the existing five-second server timeouts. Overloaded runners can fail these scheduling bounds. Exact wait observation and failure cleanup are substantive controls, but the small PostgreSQL 17 fixture does not establish production downtime, interruption at every SQL statement or live function-call locking.
- The template-link helper covers the inline local links in the current templates, not remote availability, fragment targets or all Markdown syntax. Bitrix materialization uses an explicit payload through the real writer; it does not establish a new public profile-selection API or live hook registration.
- CLI JSON serialization uses a synthetic verifier report; separate tests establish actual fingerprint and receipt behavior. POSIX path cases do not prove every filesystem/platform combination.
- The schema diagnostic cap bounds presentation after complete traversal; it is not a new temporary-memory bound or support for additional JSON Schema semantics.
- The separate #162 Trust CI validator successor and deployed compatibility are still pending. This local review does not establish external acceptance or authorize delivery operations.

Recommendation: **PASS for the reviewed source and test adequacy**. The saved full result is source-equivalent evidence for this reviewed head, not a current fingerprint-bound receipt after report writes. The coordinator must freeze final evidence and obtain current receipts; the exact-head App-owned external check and applicable approvals remain independent merge requirements.
