# Core security review — FAIL

Source readiness only: A-E/H/HB plus schema-025 test fixture. F/G remain pending successors. This local review confers no App acceptance, human approval, merge, release or live qualification.

## Identity and isolation

Original comparison base: `63799f8760d3a55028d83ab5ff0116ececf8f7d1`.
Source: `<local-path>`.
HEAD before/after: `e8a4cd02cdc8ae047c3d8e2b88146856fc5c17c0`.
Git tree before/after: `3cbdd03fb6403b6597bcd4acea4029e743f04de9`.
Canonical `adaptive_grok.util.tree_fingerprint` before/after: `2f947056c276408529f450c8026b2d3b41393d441b7cbba6789cf3efb1fc5225`.
Source status was empty before/after. Exact clean tracked HEAD independently cloned with `git clone --no-hardlinks --no-checkout`, then detached checkout of the exact HEAD.

Private scratch: `<local-path>`. Parent/role0700, pall, non-sticky. Scratch fingerprint matched source before/after, Git status empty. Synthetic copies used private TMPDIR; bytecode disabled; CPU14,15/max2; no DB/full suite/agents. Startup14 physical/28 logical, original affinity22, effective cpuset0-27, no finite readable ancestor quota, child widening succeeded28. Private snapshot preceded task inspection; copied to role `capacity.md` after brief supplied location.

reviewed-tree-modified: no

## Findings requiring repair

**S1 HIGH — lifecycle observation failure bypasses protected/external-write policy.** `.grok/hooks/pre_tool_use.py:249-253`, `.grok-stack/adaptive_grok/agent_lifecycle.py:275`.

New observation precedes sensitive policy, catches only OSError/TimeoutError, and assumes `agent-state.json.active` is a mapping. `{"active":[],"history":[]}` plus explicit child generation raises AttributeError; outer hook handler emits allow. In a synthetic Git project with valid route/no grants, baseline `git push origin feature` and Write to `.grok-stack/adaptive_grok/policy.py` were denied. Malformed state made both **allow**; removing generation restored denial. Only hook decisions were evaluated, never the push/write.

Required fix: validate lifecycle shapes and isolate all observer failures so mandatory authorization still runs/fails closed. Add malformed state/observer-exception regressions for protected and external writes. A narrow exception-list extension must not leave other failures reaching the permissive outer handler.

**S2 MEDIUM — stale current-task updates remain accepted.** `.grok-stack/adaptive_grok/agent_lifecycle.py:137-144`.

`_matching` never rederives current route task. Start `writer-1`, route `route-229`, task `task-229`; replace current `change_id` with `different-task`, same route ID; old task/generation heartbeat is **accepted**. Existing tests exercise caller mismatch only. Matching-backed ACK/resume likewise lack current task fencing; this creates no external authority.

Required fix: match rederived active change_id/session/route fallback, retaining Cyrillic opaque mapping. Add changed-current-task heartbeat/ACK/resume refusals and unchanged/Unicode/fallback positives. Intentional task rebinding needs an explicit generation-fenced transition.

## Executed checks and outcomes

Commands below ran in the exact private clone. Prefix `P` means `taskset -c 14,15 env PYTHONDONTWRITEBYTECODE=1 TMPDIR=<local-path>`.

`P python3 -m unittest tests.test_agent_lifecycle tests.test_architecture_model_preflight tests.test_governance.GovernanceInputBoundaryTests tests.test_governance.GovernanceLifecycleTests.test_repository_human_claim_cannot_confer_active_rule_authority tests.test_architecture_fitness.ArchitectureFitnessTests.test_change_separation_admits_bound_trust_ci_metadata tests.test_architecture_fitness.ArchitectureFitnessTests.test_change_separation_metadata_does_not_hide_implementation tests.test_verifier_recovery.VerifierRecoveryTests tests.test_verifier_recovery.DurableReceiptRecoveryTests tests.test_verifier_recovery.OwnedRunnerRecoveryTests.test_output_close_failure_fails_gate_with_completed_exit_visible tests.test_hooks.HookTests.test_sensitive_external_and_protected_writes_cannot_borrow_session_grants`

Observed:74 tests,65.774s,OK. Claims: stored generation/task mismatch/ACK and writer ownership; refusal+cancellation non-rebinding; receipt durability faults/exact-head staleness; hostile Git, pinned projections/byte budgets; architecture path/alias/symlink/size bounds; repository human claims confer no authority; metadata refuses executable/security/mixed changes.

`P python3 -m unittest tests.test_installer.InstallerTests.test_installed_fixture_reset_leaf_is_byte_identical_and_importable tests.test_installer.InstallerTests.test_source_reads_are_nofollow_and_bounded_at_the_descriptor tests.test_verifier_recovery.OwnedRunnerRecoveryTests.test_signal_during_output_close_keeps_completed_result tests.test_verifier_recovery.OwnedRunnerRecoveryTests.test_output_close_keeps_primary_cancellation_and_result tests.test_hooks.HookTests.test_sensitive_root_aliases_canonicalize_and_conflicts_fail_closed`

Observed:5 tests,12.945s,OK. Claims: installed helper byte/import identity, bounded nofollow reads, output-close signal/failure retention, sensitive root conflicts refused.

`P python3 <local-path>`

Observed: baseline push/protected write deny; malformed lifecycle no generation deny; with generation both allow; changed-current-task old heartbeat ACCEPTED task-229. S1/S2 reproduced. No mutants (security role; mandatory only code/test).

Identity commands: `git --no-optional-locks status --porcelain=v1`; `git rev-parse HEAD HEAD^{tree}`; `taskset -c 14,15 env PYTHONDONTWRITEBYTECODE=1 python3 -c 'import sys; from pathlib import Path; r=Path.cwd(); sys.path.insert(0,str(r/".grok-stack")); from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(r))'` (source call used its explicit absolute root).

## Static assessment and limits

Inspected original-base product diffs and surrounding receipts/verifier/runner/lifecycle/hooks/architecture/governance/installer/fixture, plus required design/package. `git diff --name-only 63799f..e8a4 -- trust-ci/src factory/src factory/migrations engineering/contracts architecture schemas .github/workflows` returned no paths. F/G runtime and migrations001-025 unchanged. Deployed policy/holdout/branch binding/human scopes remain external. Governance explicitly refuses repository-originated active authority; metadata exception is local source fitness. Additive compatibility inspected, metadata negative controls executed.

Unexecuted: full verifier/coverage/PG, OS isolation, live App/human gates, deploy/publish, exhaustive process/additive-contract matrix. Controller full PASS is context only, not independent execution/external acceptance. No secrets/.env/keys/credentials/deployed policy/holdout/trust store or approvals accessed; no external writes. Reported pthread/fork FIFO warnings not rerun, retained as environment limitations.

S1 blocks security readiness. S2 needs repair or explicit bounded lifecycle ruling/evidence. Repairs require fresh exact-tree verification/review; external App acceptance and signed scopes remain separate.
