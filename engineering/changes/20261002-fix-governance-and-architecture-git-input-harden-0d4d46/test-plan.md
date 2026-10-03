# Test plan — Fix governance and architecture Git input hardening: explicit repository object binding, controlled Git environment, filter-free committed reads and pinned bounded regular-file projections.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Ambient Git redirection, explicit root/directory binding and linked registration | GovernanceInputBoundaryTests |
| P0 | Commit format/kind, replacement/filter/gitlink and bounded output | GovernanceInputBoundaryTests |
| P0 | Projection special files, byte budget, identity/content/root races and final CLI refusal | GovernanceInputBoundaryTests |
| P0 | Hidden authority mutation, exact-head digest and external rule/example refusal | GovernanceHandoffTests, GovernanceLifecycleTests |
| P1 | Existing successful CLI fields and architecture consumers | GovernanceHandoffTests, test_governance_fitness, test_architecture_fitness |

## Automated checks

- RED: initial 12 boundary tests reported 7 failures/11 subtest errors; absent APIs and observable redirection/refusal/budget gaps were the causes. Four later publication/authority controls each failed before repair.
- GREEN: the final governance/governance_fitness run passed 83 tests in 93.051 s, architecture_fitness passed 131 tests in 132.197 s, and the final boundary class passed 19 tests in 1.237 s. The last boundary run includes the subsequently added real character-device descriptor characterization. Registration-after-read mutation, linked/ordinary common-directory redirect and exhausted-budget continued reads each produced a fresh RED before repair.
- Focused: taskset -c 10 env PYTHONPATH=tests python3 -m unittest test_governance test_governance_fitness; in parallel taskset -c 11 env PYTHONPATH=tests python3 -m unittest test_architecture_fitness.
- Static: git diff --check passed. These are local focused pre-commit results against base e5856acfd4bc7a186f40a740b54ec86459462db5 and the four-file candidate; they are not current receipts or merge authority. Full PR verification and routed reviews are controller-owned and pending on the final committed/integrated candidate.

## Manual checks

- Review the final four-file product inventory; verify historical source remained untouched; inspect tests for unsupported SHA-256 frozen-handoff refusal and retained clean/current-HEAD gates.
- Direct device-node creation is not executed by the unprivileged test process. The public device-path case uses a /dev/null symlink; a separate characterization supplies an actual /dev/null character-device descriptor to the reused pinned reader and asserts typed refusal. No direct device-node creation is claimed.
