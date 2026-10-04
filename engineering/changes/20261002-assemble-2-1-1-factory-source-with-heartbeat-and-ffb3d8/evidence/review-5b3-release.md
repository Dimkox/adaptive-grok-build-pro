# Fresh release review — Core source only

Verdict: PASS for local Core acceptance; no Core blocker found. This is not 2.1.1 release, merge, deployment or publication approval. F/G remain required and not accepted.

Route ffb3d81e031f; selected release_reviewer. Read shared brief, agent, adaptive-delivery/release-readiness/verification-evidence/route skills; inspected original-base product diff, approved design/scope ledger/topology/requirements/release/rollback, Russian README and watchdog. No agents spawned.

Source `<local-path>`: agreed base `63799f8760d3a55028d83ab5ff0116ececf8f7d1`; HEAD before/after `5b3ee0026f8d1a7166e3d1cf16d1511d261c4d0c`; Git tree `2c4675bf5ecd073a9c2c6ecdd5737f32c7d911f5`; canonical fingerprint before/after `2ff95b7c0b279b06b929b7d2079db4b937626783309f206736017bbb91b5efa9`; both statuses clean.

Scratch `<local-path>`; `stat -c '%a %A %U %n'` proved both parent directories0700/non-sticky/pall. `git clone --no-hardlinks --no-checkout <source> <scratch>`; `git checkout --detach <HEAD>` reproduced exact clean snapshot/fingerprint, also matched after scratch restoration. Startup snapshot `<local-path>`:14physical/28online, initial22affinity, inherited0-27cpuset, no exposed finite quota, successful child0-27probe. Probes CPU6,7/max2; no PG/Docker/full/external/secret reads.

reviewed-tree-modified: no

## Evidence and probes

Executed in scratch `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack:factory/src taskset -c 6,7 timeout 180s python3 -m unittest tests.test_project_state tests.test_manifest_package tests.test_agent_lifecycle -q`: exit0,93tests/24.653s,OK. Probes candidate/unbuilt/unpublished/default-off/not-qualified/F-G-negative bindings, historical2.1.0 custody digest, published artifact/packaging and lifecycle warning/ACK/resume/one-writer contracts.

Scratch-only mutants via apply_patch: M1 changed one current F obligation from not_accepted to accepted; M2 made resume retain its old generation. Executed the same environment/affinity/timeout prefix with `python3 -m unittest tests.test_project_state.ProjectStateTests.test_current_core_source_has_no_artifact_or_successor_acceptance tests.test_agent_lifecycle.AgentLifecycleTests.test_interrupt_ack_resume_fences_old_executor_and_preserves_workspace -v`: exit1, 2 failures/0.102s. M1 KILLED at state line830; M2 KILLED at lifecycle line177. Restored both via apply_patch. Reexecuted those two plus `tests.test_structure.StructureTests.test_version_identity_matches_readme tests.test_workflow_sources -q`: exit0, 9 tests/0.372s, OK. Raw logs remain beside this report, private. No blanket mutation score asserted.

Inspected `full-pr-5b3.json` with jq: same fingerprint, full-pr-suite/out-of-scope-or-invalid-paths; actual route and origin/main bases both63799f; range inventory274, dirty0, no selection findings, digest `5cbed7bb78b9a1295b43e3db1a41b4f030a84ace84a4cbd128ec1e0cbfc5de65`, no selector skips. 17 checks PASS; workflow-artifacts SKIP because not configured, not PASS. Retained root tail: 1143 passed/2018 subtests/178.80s, 2 warnings; coverage81.47%. PostgreSQL exit0: 1016 tests/521.738s, OK(skipped=2); stdout reports disposable identity preflight, two restarts and role/reconciliation checks. The retained tails omit identities/reasons of both conditional DB skips and details of both warnings: individual claims UNEXECUTED/unassessed; no inference they passed. This reviewer did not rerun the full/DB suites.

## Findings and remaining gates

VERSION/README/module/state bind 2.1.1 source candidate. Russian instructions disclose effects/setup/native ACK/followup and incomplete177+3s timeout; full180s completion unproved/disclosed. Architecture links exist/tests bind them. Watchdog never kills/replaces/releases writers; generation fences records, not OS executors. Resume preserves workspace/ownership. Rollback via PR; no live migration. Future F026 retains rows/forward recovery; old migrations immutable.

`git diff --name-only 63799f..HEAD -- trust-ci factory/migrations factory/src factory/contracts architecture/rules.yaml` returned empty. c761054..HEAD fixture comparison: reset seam and two callers exact; test module alone randomizes synthetic password using uuid. Archived join equivalence is historical, not current exact test-byte proof. No guard/budget/runtime/migration waiver inferred.

Static/live claims UNEXECUTED: deployment, external pilot, M8/M9 qualification, F lookup/G authority acceptance. PR238/e413 App timeout failure and private e413 serial1143/743.241s three nested Bandit failures are coordinator-supplied historical observations. Persist reviews/freeze HEAD/refresh full receipts/obtain exact-head App and signed scopes before Core merge; separately accept F/G, build reproducible merged-source artifact child, obtain its gate, and use delegated tag/release/download-hash operations. Local PASS authorizes none.
