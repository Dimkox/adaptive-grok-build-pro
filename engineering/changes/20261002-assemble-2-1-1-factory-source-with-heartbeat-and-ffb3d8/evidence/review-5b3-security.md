# Fresh Core security review — PASS

No blocking finding in A-E/H/HB plus test-only025 fixture scope. S1/S2 independently retested/repaired. F/G remain required, unaccepted successors. Local review confers no external acceptance, signed approval, merge, publication or live qualification.

## Exact identity and isolation

Source: `<local-path>`; route `ffb3d81e031f`; actual comparison base `63799f8760d3a55028d83ab5ff0116ececf8f7d1`.
HEAD before=after: `5b3ee0026f8d1a7166e3d1cf16d1511d261c4d0c`; Git tree `2c4675bf5ecd073a9c2c6ecdd5737f32c7d911f5`; canonical fingerprint before=after `2ff95b7c0b279b06b929b7d2079db4b937626783309f206736017bbb91b5efa9`. Source status empty before/after.

Private scratch: `<local-path>`. Runtime/reviewer parents mode0700, pall, non-sticky (`stat -c '%a %U %n'`). `git clone --quiet --no-hardlinks --no-checkout <source> <scratch>`; `git -C <scratch> checkout --quiet --detach <HEAD>` reproduced exact clean snapshot. Tests/probes/mutants only in scratch; mutations restored with patches. Final scratch fingerprint matches, status empty. Identity commands before/after: `git --no-optional-locks -C <root> status --porcelain=v1`, `git -C <root> rev-parse HEAD HEAD^{tree}`, bytecode-disabled `adaptive_grok.util.tree_fingerprint(Path(<root>))`.

reviewed-tree-modified: no

Startup capacity.md recorded before routing:14 physical/28 logical, affinity22, cpuset0-27, no observed finite ancestor quota, child widening28. CPU4,5/max2; sequential tests, private TMPDIR, no bytecode/subagents.

## Executed claims and commands

All commands below ran after `cd <scratch>`. Prefix P = `taskset -c 4,5 env PYTHONDONTWRITEBYTECODE=1 TMPDIR=<local-path>`.

`P python3 -m unittest tests.test_agent_lifecycle tests.test_architecture_model_preflight tests.test_governance.GovernanceInputBoundaryTests tests.test_governance.GovernanceLifecycleTests.test_repository_human_claim_cannot_confer_active_rule_authority tests.test_architecture_fitness.ArchitectureFitnessTests.test_change_separation_admits_bound_trust_ci_metadata tests.test_architecture_fitness.ArchitectureFitnessTests.test_change_separation_metadata_does_not_hide_implementation tests.test_hooks.HookTests.test_sensitive_external_and_protected_writes_cannot_borrow_session_grants tests.test_hooks.HookTests.test_sensitive_root_aliases_canonicalize_and_conflicts_fail_closed`

63 tests,43.391s,OK: generation/writer/ACK fences; malformed observer states; architecture traversal/alias/symlink/size refusals; bounded exact Git objects/filters/replacements/gitlinks/projections/races; repository human claims refused; metadata mixed/ref/security negative controls; exact-resource/root grant fences.

`P python3 -m unittest tests.test_verifier_recovery.DurableReceiptRecoveryTests tests.test_installer.InstallerTests.test_source_reads_are_nofollow_and_bounded_at_the_descriptor tests.test_installer.InstallerTests.test_installed_fixture_reset_leaf_is_byte_identical_and_importable`

5 tests,7.338s,OK: receipt durability/exact-head failures, bounded nofollow installer reads, installed fixture byte/import identity.

`P python3 ../boundary_probes.py` (independent reviewer script): baseline push/protected Write DENY; seven malformed state/active/history shapes14/14 DENY; RuntimeError/TypeError/AttributeError observer with normal/broken stderr12/12 sensitive decisions DENY,6/6 ordinary reads ALLOW, warning leaks no exception marker. Changed current change/session heartbeat/status-ACK/interrupt-ACK/resume8/8 REFUSE without state mutation; unchanged ASCII/Unicode change/Unicode session/route fallback4/4 ACCEPT. These evaluate hook decisions only, never perform a push/protected Write.

Mutant M1: narrow pre-tool observer catch to OSError/TimeoutError. Same probe exit1, sensitive decision became allow: KILLED. Restore, then M2: remove `_matching` current-task comparison. Same probe exit1, changed-change heartbeat accepted: KILLED. Restore; same probe passes again. No blanket mutation threshold claimed.

## Static assessment and limits

Inspected base..HEAD product diffs and surrounding lifecycle/pre-tool/policy/resource fences, receipts, Git/governance, architecture metadata, hooks/installer and approved scope. Local observations/governance claims confer no external authority. Generic warning is bounded/non-sensitive. Original-base diff for trust-ci/src, factory/src, factory/migrations, contracts, architecture, schemas and Actions returned no paths; F/G runtime and001-025 unchanged.

Unexecuted: full verifier/coverage/PG/process matrix, OS isolation, live App/policy/holdout/human gates, exhaustive contracts, deployment/publication. Controller full-pr-5b3.json PASS/full-pr-suite is prerequisite context only. No secrets/envfiles/credentials/keys/deployed trust materials/production services accessed; no external writes.
