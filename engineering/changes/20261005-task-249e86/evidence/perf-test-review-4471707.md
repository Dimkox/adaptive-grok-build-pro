# Affected test review — frozen 4471707

Coordinator projection: complete out-of-band report, public path prefix substituted only; original absolute paths retained in the controller record. This is bounded source review at the stated identity, not a fresh final receipt.

Verdict: PASS for the bounded affected-test refactor. Fresh full verification and external App check remain pending; this review establishes no timeout guarantee.

Source:
- Candidate: <project-root>/.review-scratch/trust-public-checker
- Reviewed delta: 5886e734b170307c6026f98c026f5e1a0e6ae834..4471707447570b0bc020e3764aa4066f6a008672
- HEAD before/after: 4471707447570b0bc020e3764aa4066f6a008672
- Fingerprint before/after: d6232a5eb10c276f47a02b1d53c7b668de41d25e473b0d1eab25ee9b967bcd7d
- Both source status checks empty.
- reviewed-tree-modified: no

Capacity discovery recorded first in /tmp/grok-review-capacity/test-review-startup.txt.
Commands: date -u, lscpu -p=CPU,CORE,SOCKET,ONLINE, nproc --all, nproc, taskset -pc $$, /proc/self/cgroup, /proc/self/mountinfo, ancestor cpu.max and cpuset.cpus.effective reads.
Observed 2026-10-05 06:29 UTC: 14 physical cores / 28 online logical CPUs; process capacity 22, affinity 0,1,8-27.
Actual membership /user.slice/user-1000.slice/session-2050.scope; mount /sys/fs/cgroup; effective cpuset 0-27; all available ancestor quotas max 100000.
Bounded child probe: taskset -c 6-7 bash -c 'nproc; taskset -pc $$; cat /proc/self/cgroup' returned capacity 2, affinity 6,7, same membership.
Chosen allocation: two CPUs, child-only affinity 6–7. Controller affinity unchanged.
Initial findmnt request used an unsupported column; /proc/self/mountinfo resolved the mount without uncertainty.

Isolation:
- Trusted parent .review-scratch: owner pall, mode 0700.
- Private scratch: <project-root>/.review-scratch/test-perf-review-VKue6L, created by mktemp -d.
- Snapshot command: git -C <candidate> archive 4471707447570b0bc020e3764aa4066f6a008672 | tar -x -C <private-scratch>.
- Candidate clean inventory established that this exact archive includes its relevant tracked candidate bytes.
- An initial copy command used relative paths from the private working directory and failed before copying; its unittest invocation failed import. Corrected absolute-path copy succeeded. These failed setup commands are not passing evidence.

Executed controls:
taskset -c 6-7 env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_change_separation_admits_only_exact_paired_public_contracts tests.test_architecture_fitness.ArchitectureFitnessTests.test_reviewed_public_migration_refuses_drift_and_incomplete_history
Working directory: private scratch.
Observed: Ran 2 tests in 22.877s, OK.
These exercised five paired-contract positive vectors and thirteen migration rejection vectors.

Mutation command:
taskset -c 6-7 env PYTHONDONTWRITEBYTECODE=1 python3 review_probe.py
The private probe creates distinct (0,) and (1,) fixture heads, retains both loaded snapshots, and leaves the second head checked out.
Observed:
- Correct earlier snapshot with last head checked out: PASS.
- Wrong retained snapshot: KILLED by architecture-digest assertion.
- Wrong returned diff head identity, injected with patch.object and dataclasses.replace: KILLED by head_sha assertion.
No surviving or inconclusive mutants.

Static coverage checks:
AST comparison used git show <base>:tests/test_architecture_fitness.py and git show <head>:tests/test_architecture_fitness.py, then compared test names, nonempty literal case vectors and assertion-call method inventories.
Observed 145 test methods before and after, no removed methods.
All six modified test methods preserve their nonempty literal case vectors and assertion-method inventories.
Diff inspection confirms unchanged existing test bodies outside these six, preserving prior added/activated cases and original Git cases.
New prepared=[] lists account for the initial raw literal-vector comparison mismatch; excluding empty setup lists produces equality.
No assertion replacement weakens the exercised status or qualified-path expectations.

Reasoning:
Every prepared snapshot is loaded at its corresponding committed head; qualification uses that retained snapshot with explicit base/head/digest binding.
Mutable systems are deep-copied before each envelope mutation; prepared migration registries are separate per iteration.
Migration predecessor cases retain each case's own base, including gapped history and previously admitted bytes.
Preparation remains inside subTest: preparation errors are reported by unittest, so omitted prepared tuples cannot silently pass.
Existing assertion counts and case vectors remain intact; qualification remains independently labelled by case.

Unexecuted claims:
Remaining methods, PostgreSQL, full verifier and external App check were deliberately outside the bounded assignment.
Full 59+9+3 case execution and 61+4 contract behavior were not re-executed; preservation was inspected statically relative to the exact prior head.
No benchmark proves external runner timing or resolves its timeout by itself.
