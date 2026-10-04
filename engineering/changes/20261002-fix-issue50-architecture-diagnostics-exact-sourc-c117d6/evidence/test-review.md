# Independent test review — route c117d6185b7f

Status: PASS. No blocking test findings in the scoped changes. Completed 2026-10-02T23:47:21Z.

Candidate: <local-path>
Comparison base: 63799f8760d3a55028d83ab5ff0116ececf8f7d1
HEAD before and after: 0de557769e48879820b883537fe42b1d55b56f5b
Candidate fingerprint before and after: 294ebeb2b3ea12df661ba019338d1172d58d711581693ddf31ab37497b1cf4b9
Staged, unstaged, untracked inventory: empty before and after (git status --porcelain=v1).
reviewed-tree-modified: no

Reviewed actual base..HEAD diff, surrounding architecture loader/preflight, verifier refusal branch, doctor adoption, acceptance criteria, test plan, route, and regression fixtures. Scope is exact source coordinates, raw path/alias refusal, bounded preflight and disclosure of skipped/not-recorded consumers. Review is local preflight evidence; it establishes no external check or merge authority.

## Resource and scratch identity

Startup measured lscpu, nproc --all, nproc, taskset -pc $$, /proc/self/cgroup, cgroup2 mounts, inherited cpu.max/cpuset.cpus.effective, and a child-only taskset -c 0-27 probe. Snapshot saved locally before repository inspection at .review-scratch/test-review-startup-20261002T234441.txt. Physical cores 14; online logical CPUs 28; initial affinity 0,1,8-27 / nproc 22. Actual cgroup /user.slice/user-1000.slice/session-2050.scope; session/user-1000/user.slice quotas max 100000; inherited effective cpuset 0-27, root quota absent. Child widening succeeded with nproc 28 and affinity 0-27. Verified host capacity 28; test commands pinned CPU 9. Two single-worker probe processes briefly overlapped on CPU 9; no extra CPU allocation was consumed.

Scratch parent and private directory both owned by pall, mode 0700, non-sticky:
 <local-path>
Scratch snapshot:
 <local-path>
Exact snapshot command: git clone --quiet --no-hardlinks --no-checkout .worktrees/v211-d-architecture .review-scratch/d-test-o2sx5B/candidate
Then: git -C .review-scratch/d-test-o2sx5B/candidate checkout --quiet --detach 0de557769e48879820b883537fe42b1d55b56f5b
Initial scratch Git status was empty. Candidate dirty inventory was empty, so detached clone reproduces the complete relevant snapshot. No candidate edits/restores/artifacts; tests, mutations and generated temporary projects ran only from scratch. PYTHONDONTWRITEBYTECODE=1 prevented candidate bytecode during identity reads.

## Executed claims and observed results

From scratch candidate:
 taskset -c 9 env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_architecture_model_preflight tests.test_architecture_model tests.test_architecture_fitness -q
Observed: Ran 230 tests in 83.836s; OK; exit 0.

This covers the new refusal/location regressions and nearby model, contract and fitness compatibility. The fixtures calculate physical positions independently from source rows and structural anchors, assert actual exception document/line/column, and use an executable root-discovery marker. Active-route refusal asserts receipt absence and explicit not_recorded metadata. Valid-model coverage compares digests and rendered views before/after preflight.

Independent mutation/fault command, from scratch candidate:
 taskset -c 9 env PYTHONDONTWRITEBYTECODE=1 python3 reviewer_probes.py
Observed: exit 0 after three expected failing mutant test executions and three passing independent fault probes. The complete reproducible probe script is in scratch candidate/reviewer_probes.py. Mutations are temporary in-process mock replacements restored after each run.

M1 physical-newline-coordinate-loss: replaced _source_coordinates with splitlines-based line counting. KILLED by test_unicode_line_lookalikes_do_not_shift_coordinates. Expected architecture/system.yaml:44:9, observed mutant :45:9; one assertion failure.

M2 authority-contract-alias-gap: wrapped load_architecture to discard the shared _input_identities map. KILLED by test_referenced_contract_cannot_alias_an_authority_input. Expected one refusal finding; mutant returned zero.

M3 refusal-gate-disabled: replaced verifier _architecture_preflight_check with an unconditional passing CheckResult. KILLED by test_verifier_discloses_skip_and_blocks_root_discovery_on_refusal. Executable marker appeared, triggering "root discovery started after an input refusal".

No scoped mutants survived or were inconclusive.

F1 PR-mode refusal with factory test/exit paths present: _python patched to raise if called; verify(mode='pr', record=False) returned five explicit skips for governance, python-unittest, coverage, factory-unit and factory-postgres-exit. _python was not called; architecture.receipt_status was not_recorded. PASS.

F2 canonical model runtime.network=42: independently computed source value position; preflight returned schema finding at architecture/system.yaml:48:20 with "$.nodes[0].runtime.network: value 42 not in enum". PASS.

F3 dangling authority symlink: architecture_inputs_present returned true; preflight returned io finding naming architecture/system.yaml. PASS.

Candidate identity commands before/after:
 git -C .worktrees/v211-d-architecture rev-parse HEAD
 git -C .worktrees/v211-d-architecture status --porcelain=v1
 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.worktrees/v211-d-architecture/.grok-stack python3 -c 'from pathlib import Path; from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path(".worktrees/v211-d-architecture")))'
Observed unchanged HEAD, empty inventory, and the fingerprint quoted above.

## Limits and unexecuted claims

Full PR suite, complete tests.test_verification_doctor module, external Trust CI, approval and operational workflows were not executed by this reviewer: controller owns full-suite evidence and delivery, and the review was explicitly bounded. Doctor configured/absent distinctions and active-route refusal are exercised by the changed regression module. No exhaustive mutation score, OS-enforced read-only isolation, arbitrary filesystem-race resistance, or production qualification is claimed. Static examination of unchanged surrounding behavior remains inspection, not additional executable evidence.

The in-scratch mutation script/report are reviewer artifacts and were not added to the candidate. The controller must persist this report and refresh fingerprint-bound verification/receipts after doing so.
