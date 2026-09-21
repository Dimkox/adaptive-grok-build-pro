# Independent security review — PASS

Reviewed on 2026-09-21 as the route-selected `security_reviewer`; the reviewer did not implement the source change.

- Route: `cf23849faca6`.
- Exact base: `5674c369c4a427d42bde2a5fb3a3e2f73c853cd0`.
- Exact reviewed head: `c8ed34d0731e12e65f75f568d8fb3e9f0f64b2d5`.
- Reviewed head tree: `5f481c6555b22df363f14d5d2d96d6d03a2c624c`.
- Verified source head in the coordinator's completed run: `4bc43cb7876d92b11efb289a121dcfef0a0355ac`.
- Working tree was clean before this report. The six files changed between the verified source head and reviewed head are `PROJECT_STATE.json`, `START_HERE.md`, and this package's `state.json`, `tasks.md`, `evidence/combined-full-initial-report.json`, and `evidence/combined-full-initial-summary.json`; none changes executable source or tests.

No blocking security finding was identified in the actual base-to-head source diff. This is local review evidence, not a merge authorization or a claim that current final receipts are complete.

## Scope and trust boundaries

Read `AGENTS.md`, the bootstrap/current handoff, the active route, the active package's scope/design/requirements/test/recovery records, adaptive-delivery, verification-evidence and the selected domain skills. Inspected all nineteen manifest paths and surrounding implementations, including existing receipt validation, bounded Git subprocess handling, semantic service authorization, database capability setup, HTTP error handling and test-process cleanup. Earlier candidate reviews were not substituted for this inspection.

The nineteen reviewed source/test/guide paths are:

- #165: `.grok-stack/adaptive_grok/change.py`, `.grok-stack/adaptive_grok/package_status.py`, `.grok-stack/adaptive_grok/state.py`, `.grok-stack/templates/change/evidence/README.md`, `.grok/hooks/stop_gate.py`, `scripts/grok_review.py`, `scripts/grok_status.py`, `tests/test_package_status.py`, `docs/package-status.md`.
- #163: `factory/src/adaptive_factory/resources/022_semantic_repair_plan_rejection_reasons.sql`, `factory/src/adaptive_factory/semantic_repair.py`, `factory/src/adaptive_factory/store.py`, `factory/tests/test_execution_persistence_postgres.py`, `factory/tests/test_migrations.py`, `factory/tests/test_postgres_integration.py`, `factory/tests/test_semantic_repair_lifecycle.py`.
- #62/#118 subset: `.grok-stack/adaptive_grok/_cpu_capacity.py`, `.grok-stack/adaptive_grok/python_test_runner.py`, `tests/test_python_test_runner.py`.

Repository package files, evidence claims and filesystem names remain untrusted observations. Receipt validity remains a separate local check; external Trust CI and signed approval scopes remain outside repository control. Semantic callers cross the existing operator/repository authorization boundary and the isolated coordinator database capability. Automatic worker selection uses process-visible kernel cgroup metadata; it grants no host or database capability.

## Security findings

### #165 — bounded package and worktree diagnostics

PASS. Package selection is restricted to `engineering/changes/<change-id>`. Selected reads use descriptor-relative opens, reject every symlink component and nonregular files, avoid blocking on FIFOs, and compare file/directory identities after reading. Per-file, aggregate-byte, file-count and finding limits turn exhaustion into an explicit incomplete result. Current evidence references are bounded package-relative Markdown/JSON paths; traversal, hidden and named secret/credential references are rejected. The inspector does not crawl unrelated evidence.

Git observations use argument vectors, restricted Git configuration/environment, capped output and bounded subprocess time. Exact SHA validation prevents a diagnostic base from becoming a command option. NUL-delimited status parsing preserves rename endpoints and raw filename identity; invalid UTF-8 uses tagged hexadecimal records distinct from literal text names. Count/representation overflow and failed or partial queries produce unknown observations instead of a truncated clean result. An invalid initial checkpoint does not silently select another base.

`grok_status.py` remains observational, including no runtime-directory creation and no bytecode writes. Known unsafe selected inputs prevent legacy receipt readers from reopening them and produce an evidence gap. Package completeness and `not_run` accounting cannot satisfy passing receipts. Review preflight refuses a passing receipt on package errors, and the Stop adapter remains nonblocking while surfacing those errors before its existing local completion transition. No external approval or merge authority is added.

The regression source covers outside-path sentinels, ancestor/leaf symlinks, FIFOs, replacement during a read, aggregate limits, malformed state, raw-byte collisions, representation overflow, immutable checkpoint recovery, stale/missing receipts and Stop/review behavior. Checkpoint mirroring explicitly preserves a pending recovery flag; it is not represented as a two-file atomic transaction.

### #163 — planning refusal channel and PostgreSQL boundary

PASS. The Python parser accepts only the exact single-key `repair_plan_rejection` mapping. Its fifteen-entry closed vocabulary includes the fixed unknown fallback `planning_rejected`; arbitrary reason text and nonstring values are not echoed. Mixed envelopes continue through corruption handling. SQL/JSON null has a separate stable legacy-refusal message. Successful repair/escalation results still pass the existing digest, task, fence, head, writer, context, authority and request bindings.

Response classification occurs after both transaction and connection contexts exit. Normal-return side effects therefore retain their existing commit semantics; the PL/pgSQL exception block retains rollback of its protected statements. The SQL exception channel returns a fixed code without SQL error text. The existing HTTP `StoreError` handler still emits the fixed `store_conflict` envelope, and the service still checks operator kind, semantic scope and task repository access before coordinator work. Refusal prevents broker/binding calls.

An independent byte comparison confirmed that all SQL resources `001`–`021` exactly match the base. Independently normalizing `022`'s fifteen named refusal expressions back to `NULL` and removing `OR REPLACE` reproduced the original `018` planning function exactly; its original function SHA-256 is `5ceffc2373c2cb7849f3accc79ed9b6b9b51024ce7b36f975c50ca71530e7d32`. This preserves all predicates, lock placement, replay lookups and lifecycle writes. The new resource retains the existing signature, `SECURITY DEFINER`, fixed `search_path=pg_catalog,factory`, PUBLIC revocation and coordinator-only execute grant. It adds no table, role, privilege scope or dynamic SQL.

Reviewed regressions exercise closed parsing, channel smuggling, legacy null, post-transaction refusal, exception rollback, normal-return directive persistence, both idempotency lookup paths, deadline escalation and replay after expiry. Populated-prefix tests preserve the historical `020→021` proof and add the real `021→022` upgrade, comparing ledger/data, function identity/owner/ACL/configuration and role privileges. Applied-resource recovery remains an additive forward migration; no operational migration was performed by this review.

### #62/#118 subset — worker capacity and platform fallback

PASS. Capacity input is limited by bytes, line count, path length/depth, mount count and control-read count. Membership and mount parsing reject relative/traversal/ambiguous paths and invalid escapes/numbers. Mount roots are matched by path components; ancestors are inspected only within each visible matching mount, including wider mounts that expose a tighter parent. V1/hybrid CPU-controller selection and V2 absence handling preserve the distinction between visible unlimited capacity and unknown/malformed input. Unknown input selects one worker; finite quotas use a conservative floor.

Discovery is limited to Linux automatic selection. Default-off, explicit integers, child suppression and other-platform selection remain distinct. Hosts without the runner's parallel cleanup capability select the disclosed serial engine before launch. Supported parallel execution retains dependency pins and process-group ownership; failed parallel execution is not retried serially. Existing cancellation, timeout, output-limit, descendant cleanup and coverage-failure behavior remains unchanged. New tests exercise prelaunch fallback, one collection, serial failure propagation, current-run coverage, and empty-discovery behavior on the tested interpreter.

## Evidence checked and limits

- Independently recomputed and matched all nineteen candidate file SHA-256 values and all twenty-one immutable SQL resource bytes against the exact base; the SQL function normalization described above also passed.
- Ran thirty-nine small in-memory assertions against the reviewed modules: package/cgroup path rejection, closed refusal values, mixed-envelope rejection, lossless invalid-UTF-8 names, truncated Git status rejection and conservative capacity fallback. All passed. These probes created no fixture files, subprocess test suite or database operation.
- Recomputed the committed complete-verifier report SHA-256 and matched `d797b047c16090a7b4869a30d27edc3b5a2b2a5cf6936bcfd9b82164b779d32f`. The actual report records exit 0 for `GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr --json` at source head `4bc43cb7876d92b11efb289a121dcfef0a0355ac`: 877 root tests and 1,426 subtests, 81% reported coverage, 804 factory/PostgreSQL tests with two conditional skips, 60 factory unit tests, and 44 pilot tests with one pinned-sandbox skip. Workflow artifacts were unconfigured and skipped. Secret scan, Bandit, SQL safety and source stability passed in that report.
- `python3 scripts/grok_status.py` at the reviewed head reported package completeness, stale verification bindings and all five review receipts missing. This review does not reinterpret that as current completion. The coordinator must freeze reports/handoff, run final verification and create current fingerprint-bound receipts.
- No full test suite, lint, compilation, Docker operation, external write, credential/key access, live service action or deployed-policy inspection was performed by this reviewer. Native Windows, older Python, hidden cgroup ancestors and PID/memory headroom are not qualified by the Linux fixture evidence. Worktree diagnostics remain observations rather than an atomic content fingerprint.
- No `trust-ci/`, `.github`, architecture, governance or schema path changed in the reviewed base-to-head diff. The bounded App Check Run command-output portion of #62, #158 and trusted-validator compatibility remain separate. Issue #62 must stay open for its remaining output work. Local PASS does not replace the exact-head App-owned external check, required signed scopes or named delegated delivery operations.
