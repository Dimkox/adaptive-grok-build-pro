# Affected code review — frozen 4471707

Coordinator projection: complete out-of-band report, public path prefix substituted only; original absolute paths retained in the controller record. This is bounded source review at the stated identity, not a fresh final receipt.

Verdict: PASS for the bounded affected code review; no blocking finding in 5886e734b170307c6026f98c026f5e1a0e6ae834..4471707447570b0bc020e3764aa4066f6a008672.

Source candidate: <project-root>/.review-scratch/trust-public-checker
HEAD before/after: 4471707447570b0bc020e3764aa4066f6a008672
Fingerprint before/after: d6232a5eb10c276f47a02b1d53c7b668de41d25e473b0d1eab25ee9b967bcd7d
Git status before/after: clean.
reviewed-tree-modified: no

Startup capacity recorded at .review-scratch/code-review-capacity-20261005.txt: 14 physical / 28 online logical CPUs; inherited affinity 0,1,8–27; effective cpuset 0–27; applicable cgroup ancestors max 100000; successful child-only affinity probe 4,5, nproc=2. One bounded process used those two CPUs.

Private scratch: <project-root>/.review-scratch/perf-code-review.irT6Xq
Parent .review-scratch verified mode 0700, owner pall. Scratch reproduced the clean exact HEAD using:
git clone --quiet --no-hardlinks --no-checkout <candidate> <scratch>/repo
git -C <scratch>/repo checkout --quiet --detach 4471707447570b0bc020e3764aa4066f6a008672
Scratch HEAD remained exact; source candidate was never used as an execution worktree.

Inspected actual diff, complete affected fixture loops, _frozen_fixture_diff, _public_trust_baseline, _public_trust_binding_repo, _migration_result, unchanged separation predicates, Git materialization, SQL inventories/readers and predecessor handling.

Findings:
- Production code is unchanged; delta is only the fixture test file and decisions.md.
- All 145 test methods remain; AST comparison reported no added/removed test methods. Existing mutation labels, assertions and distinct SQL predecessor construction remain in the affected loops.
- Real model and all registered baseline contracts are copied. Public descriptors retain exact paths, owners, roles and compatibility.
- Shared baseline/common model dictionaries are deep-copied before mutation; parsed snapshots are retained per committed head.
- SQL history_gap, primary_deleted, and mirror_only retain their own comparison bases.
- Commit-mode architecture materialization, migration inventory and read_diff_files bind to diff.head_sha, so the last fixture worktree does not supply earlier heads’ source bytes.
- New helper asserts exact base/head and architecture digest; no production cache or acceptance-map changes.

Executable claim: retained snapshots discriminate earlier prepared heads from the last worktree HEAD.
Exact command:
taskset -c 4,5 env PYTHONDONTWRITEBYTECODE=1 python3 <project-root>/.review-scratch/perf-code-review.irT6Xq/probe.py
Control ran unchanged test_change_separation_admits_only_exact_paired_public_contracts: 1 method / five index cases, OK, 6.378s.
Private mutant substituted fixture rev-parse HEAD for each requested head: KILLED, four architecture-digest assertion failures, zero errors, 2.919s.
Final probe output: CONTROL PASS; LAST-WORKTREE-HEAD MUTANT KILLED; failures= 4 errors= 0.

Unexecuted: full negative matrices, PostgreSQL, full verifier, external Trust CI, timeout qualification, and production predicate mutants; intentionally excluded by bounded review instructions. Static preservation observations are not fresh full-suite results. No claim of merge eligibility or external-timeout success.
