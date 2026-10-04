# Code review — PASS for frozen Core SOURCE scope

No blocking correctness finding identified in the reviewed original-base product diff. This is bounded independent local source review, not final 2.1.1 release acceptance or merge authority. F durable evidence and G current-authority endpoint remain pending successors.

## Identity and isolation

Original comparison base: `63799f8760d3a55028d83ab5ff0116ececf8f7d1`.
Candidate: `<local-path>`.
Before/after HEAD: `e8a4cd02cdc8ae047c3d8e2b88146856fc5c17c0`.
Before/after canonical `adaptive_grok.util.tree_fingerprint`: `2f947056c276408529f450c8026b2d3b41393d441b7cbba6789cf3efb1fc5225`.
Candidate status empty before/after. Exact tracked clean snapshot reproduced by independent `git clone --quiet --no-hardlinks`; scratch canonical fingerprint matched before mutation and after restoration.
Scratch: `<local-path>`. Its mktemp-created parent and enclosing review parent are owner-pall mode0700. Mutations used apply_patch only in scratch; no source worktree edits/restores/generated artifacts.

reviewed-tree-modified: no

Startup snapshot was recorded before brief/route inspection at `<local-path>` (private mktemp0700 directory; location predates reading the brief's preferred parent). Observed 14 physical cores,28 online logical CPUs, process22 allowed CPUs, effective cpuset0-27; session/user ancestors cpu.max=max100000, no finite ancestor quota. Child-only widening to0-27 succeeded with28 CPUs and same cgroup. Review commands used CPU10,11, serial test process; no subagents or PG/full suite. No remote fetch performed: review binds the supplied frozen original-base commit, and assignment prohibits external writes.

## Review assessment

Read candidate contract, selected code_reviewer role, adaptive-delivery/verification-evidence skills, routeffb3d81e031f and Core requirements, typed change-spec.yaml, tasks, test-plan, rollback, release-scope-ledger and delivery-topology-addendum. Examined actual `git diff 63799f..HEAD` product changes and surrounding implementations, not just historical reports.

- A/D: verification retains completed checks and owned child results through cancellation; preflight refusal clears receipt eligibility before later consumers can cancel. Receipt publication uses complete temporary bytes, fsync/replace and invalidation on publication failure; exact HEAD and tree/binding comparisons remain. Runner owns a new process session and bounded TERM/KILL/reap; cleanup diagnostics are retained separately from original exits.
- HB: useful progress remains separate from heartbeat/activity; bounded activity suppresses only progress warnings. Matching generation/route/task checks, request identity ACKs, acknowledged interruption before resume, generation rotation, writer-slot retention and stale stop controls align with requirements. Local diagnostics explicitly do not control the native harness. Unicode task sources receive opaque bounded IDs.
- Hooks/install union: explicit child generation is propagated; tool observations do not become useful progress; stop output remains empty. Installer adds lifecycle CLI and frozen fixture helper without replacing either contour.
- D/E: model preflight gives located structural/path errors and reads referenced contracts before heavyweight consumers. Git operations bind repository/worktree registration, exact object format/commit and no replacement objects; governance projection reads pin regular files and compare content, with unique consumed-byte budget and final revalidation. Local active-rule metadata does not confer external authority.
- H: additive OpenAPI schema names are admitted while removal and existing schemas still compare. Trust CI metadata qualification is derived from paired ownership/envelope states with the narrowly named store.py correction; actual implementation path mixing is still checked. Original-base diff has no Trust CI runtime, factory runtime/migrations or architecture/rules.yaml modification.
- B/C: operational routing takes explicit request precedence while retaining incident precedence and descriptive/negated/history controls. Language scanning bounds files, directory entries/depth and bytes, discloses unknown/incomplete states, excludes vendor/generated paths and retains PHP-location confirmation controls.

## Executed evidence and mutation probes

All test commands ran from scratch with `taskset -c 10,11 env PYTHONDONTWRITEBYTECODE=1`.

Baseline command: `python3 -m unittest tests.test_agent_lifecycle tests.test_architecture_model_preflight tests.test_verifier_recovery -q`. Result:63 tests in38.000s, OK. These exercise lifecycle/ACK/watchdog/writer ownership, architecture refusal, cancellation retention, child reaping and receipt faults.

M1 generation fence: removed only `record.get('generation') != generation or` from `_matching` in `.grok-stack/adaptive_grok/agent_lifecycle.py`. Command: `python3 -m unittest tests.test_agent_lifecycle.AgentLifecycleTests.test_interrupt_ack_resume_fences_old_executor_and_preserves_workspace -q`. Result:1 test, failure at test line127, `AssertionError: ValueError not raised`; stale progress after resume was accepted. **KILLED**. Restored scratch before next mutant.

M2 A/D non-rebinding: changed only `state.receipt_eligible = False` to True in architecture preflight refusal branch of `.grok-stack/adaptive_grok/verification.py`. Command: `python3 -m unittest tests.test_architecture_model_preflight.ArchitectureInputTests.test_refusal_followed_by_cancellation_never_rebinds_receipt -q`. Result:1 test, failure at test line258, expected `_record_verification_receipt` not called but called once with SIGTERM cancelled report. **KILLED**. Restored scratch afterward.

Restored control command: `python3 -m unittest tests.test_agent_lifecycle.AgentLifecycleTests.test_interrupt_ack_resume_fences_old_executor_and_preserves_workspace tests.test_architecture_model_preflight.ArchitectureInputTests.test_refusal_followed_by_cancellation_never_rebinds_receipt -q`. Result:2 tests in0.108s, OK. `git diff --exit-code` clean. Canonical fingerprints recomputed with dont_write_bytecode enabled and `tree_fingerprint(Path(...))`; scratch and candidate both matched identity above. Candidate `git rev-parse HEAD` and `git status --porcelain` unchanged.

## Limits and gate boundaries

Only the two named mutations were executed; no blanket mutation score or exhaustive correctness claim. Router/language-disclosure, H fitness/compatibility, governance hostile-object/projection, full installer and DB claims received static review here and were not independently rerun/mutated. Full suite/PG were prohibited by reviewer assignment. Those claims rely additionally on controller-owned exact-candidate evidence, not new reviewer execution.

Inspected selected fields of `full-pr-e8a4.json`: statuspass, matching canonical fingerprint, full-pr-suite because inventory is outside admitted focused scope, selector skipped_checks empty;18 checks comprise17pass and workflow-artifacts skip. The latter is a disclosed skip, not a pass. Reported fork/thread deprecation warnings remain a portability/future-runtime limitation; this review did not independently reproduce those warning paths or establish live harness recovery. No safety limit, code budget or verifier skip changed by this review.

Coordinator must persist all independent reports together and rerun final verification/receipts for that resulting tree. External exact-head App Trust CI and required signed approval scopes remain separate prerequisites. No release, artifact, deployment, pilot qualification, F/G acceptance or merge authority is asserted.
