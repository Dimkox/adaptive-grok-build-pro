# Independent test review — issue 227 Git environment grant boundary

Reviewer: route-selected `test_reviewer`, independent of the sole implementation owner.

## Verdict

**FAIL.** The implementation at the reviewed commit behaves correctly in the executed baseline and focused regressions, but the suite can false-pass regressions against two explicit acceptance requirements: clean-environment tag-grant compatibility and denial before approval lookup. The selector matrix also omits the both-present/both-empty case. Do not record a passing `test_review` receipt for this snapshot.

## Exact review binding

- Base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`
- Head: `5f4e8fef003271a9b62198d181ad6be1f1838158`
- Git tree: `eb0e0f649e0e17d55f93be8ab46b859e436d56f7`
- Clean committed-tree fingerprint before review: `4f1fce294a4c85af9db462daa8a7a33acca5636781cdbfaef9800a1f58eceba3` (the repository's fingerprint algorithm on a clean worktree is SHA-256 of the HEAD text).
- Reviewed worktree: `/home/pall/grok-projects/adaptive-grok-build-issue227`
- Private mutation scratch: `/tmp/issue227-test-review.pma8jW/review`, parent mode `0700`, locally cloned with `--no-local --no-hardlinks`, checked out at the exact head above.
- Scratch was clean and restored byte-for-byte after every mutant. Final scratch `git status --porcelain=v1 -uall` and `git diff --check` produced no output.
- The reviewed source/test files retained these SHA-256 values: `util.py` `80ce05c87fae83c892067f5b38cbefb09d146afb48a5d506609cfdd652e8bd75`; `_policy_legacy.py` `d4e7db99b64297f41d0684422e15f52e836c29f8614e035139ddfc30b5ec5e98`; `test_util_fingerprint.py` `9a1728b5a2f50b97c333f6f65c0e4f909ef2cbff22e2938ffb995d6cca32b295`; `test_policy.py` `615d8b121c0151d93019a920f36fef6e73871a4e93bd26b60ba94367dbb04f05`; `test_hooks.py` `8b3bbe323330916769cbc1032662c166fc572aace114c08a7ad32e34a6a41ac7`.
- During review, three other reviewers' untracked evidence reports appeared concurrently. They are outside the requested base-to-head diff and did not change HEAD, the Git tree, or any reviewed source/test hash. This reviewer wrote only this assigned report in the candidate worktree.
- `reviewed-tree-modified: no`

## Findings

### Critical

None.

### Important

#### I-01 — Clean-environment compatibility is not tested for a valid tag grant

The new table creates a grant containing both `git-push-branch` and `git-push-tag`, but the only clean-environment allow assertion executes a branch push (`tests/test_policy.py:147-164`). Its sole tag case has inherited selectors and therefore expects denial (`tests/test_policy.py:166-184`). The older exact-action test grants only branch and expects tag denial (`tests/test_policy.py:282-289`). Consequently no test proves the requirements' clean-environment matching-grant guarantee for `git-push-tag`.

Mutation evidence: inserting an unconditional `git-push-tag` denial after the inherited-selector branch left the complete `tests.test_policy` module green: `Ran 27 tests in 5.501s — OK`. This survivor violates requirements AC-005 and typed AC-004 while the suite passes.

Required repair: in a selector-free environment, create an exact `git-push-tag` grant and assert `git push origin v2.1.0` is allowed. Keep branch and tag compatibility assertions separate enough that either action can regress independently.

#### I-02 — Tests do not prove selector denial occurs before approval lookup

Requirements AC-002 and the implementation plan require denial before approval lookup/consumption. The foreign-push regression establishes a valid grant and checks the final denial (`tests/test_policy.py:106-145`), but it does not spy on or forbid `has_valid_approval`. The selector table likewise checks only the returned decision and message (`tests/test_policy.py:147-192`).

Mutation evidence: adding `has_valid_approval(root, 'production', action=action)` before the selector-presence check left all three new denial paths green: the foreign exploit, selector matrix, and real hook test reported `Ran 3 tests in 1.783s — OK`. This matters because lookup is not a pure contract boundary: `has_valid_approval` also prunes expired approvals.

Required repair: patch the symbol used by `_policy_legacy.evaluate_pre_tool` to raise or use `assert_not_called`, then exercise branch and tag pushes with inherited selector presence, including empty values. The policy result must remain the selector-specific denial without touching approval lookup.

#### I-03 — The selector table omits both selectors present with empty values

The table covers each selector non-empty alone, both non-empty together, and each empty alone (`tests/test_policy.py:166-192`). It never covers `{'GIT_DIR': '', 'GIT_WORK_TREE': ''}`, even though AC-002 says either key's presence must deny, including empty-string values.

Mutation evidence: special-casing exactly the both-present/both-empty combination to skip selector denial left the same three new policy/hook denial tests green: `Ran 3 tests in 1.501s — OK`.

Required repair: add both-empty to the core table and preferably to the hook subprocess table so the real environment handoff is covered as well.

### Minor

#### M-01 — Real hook coverage is not hermetic against a future hook-only push/network side effect

The core exploit test wraps `subprocess.run` and rejects a Git argv containing the `push` subcommand (`tests/test_policy.py:120-135`). The hook integration test runs the real subprocess and compares repository snapshots (`tests/test_hooks.py:168-233`), which proves the current repositories were unchanged but would not itself prevent or reliably identify every network attempt introduced only in hook-layer code. The current exact implementation did not make such an attempt: the independent `strace` run below saw zero Git `push` executions and zero network syscalls.

Suggested hardening: execute the hook test with a controlled Git shim that forwards read/local setup commands but fails and records any `git push`, and with a network-denied test sandbox where available.

## Coverage assessment

- Root-bound probes: strong. `tests/test_util_fingerprint.py:141-196` uses distinct local repositories and compares root, top-level, remote identity, HEAD, dirty/untracked inventory, name-status inventory, and fingerprint under `GIT_DIR`, `GIT_WORK_TREE`, and both. Removing selector scrubbing killed all three subtests.
- Foreign matching repository/pushurl exploit: strong for the current policy path. `tests/test_policy.py:44-64,106-145` constructs a same-commit local clone, preserves the expected fetch URL, installs a foreign `pushurl`, creates a valid grant, denies the command, checks value secrecy, and rejects any direct `subprocess.run` Git push.
- Presence and secrecy: strong for single empty values and non-empty single/together values. Truthiness-based presence checking was killed by two empty-value failures; leaking selector values was killed by both policy and real-hook assertions.
- Clean environment: branch allow is covered in core policy and existing real-hook tests; valid tag allow is missing and is blocking per I-01.
- Real hook: the test invokes `.grok/hooks/pre_tool_use.py` as a subprocess with inherited selectors, validates both output schemas, denial-ledger placement, secret-safe text, and unchanged repositories. Single-selector and empty-selector hook cases are absent.
- No push/no network: current execution is clean and the core policy test has a push tripwire. The hook-level hardening limitation is M-01.

## Commands and observed results

All commands used `env -u GIT_DIR -u GIT_WORK_TREE`; no fetch, push, remote access, GitHub write, Daybreak call, commit, merge, or deployment was performed.

1. Candidate focused suite:

   `python3 -m unittest tests.test_policy tests.test_hooks tests.test_util_fingerprint`

   Result: `Ran 80 tests in 40.504s — OK`.

2. Nearby contract suite:

   `python3 -m unittest tests.test_structure tests.test_change_receipts`

   Result: `Ran 49 tests in 20.434s — OK`.

3. Five issue-specific regressions under syscall/exec tracing in private scratch:

   `strace -f -qq -e trace=execve,network -o /tmp/issue227-test-review.pma8jW/exec-network.trace python3 -m unittest <five exact issue-227 tests>`

   Result: `Ran 5 tests in 7.011s — OK`; exact `execve` search for `["git", "push"` returned `0`; `AF_INET`/`AF_INET6` connect count `0`; all traced network syscall count `0`. Local `git clone --no-local` and local configuration reads/writes were observed, but no remote transport or push occurred.

4. Static diff check:

   `git diff --check cb9af4073ba6c3d515145164d771c75ebdfa3224..5f4e8fef003271a9b62198d181ad6be1f1838158`

   Result: exit `0`, no output.

5. Scratch restoration baseline after mutation work:

   The five exact issue-227 tests reran as `Ran 5 tests in 2.281s — OK`; scratch status and diff-check were empty.

## Mutation probes

| Claim | Mutant | Result |
| --- | --- | --- |
| All Git probes ignore inherited selectors | Removed both `environment.pop(...)` operations from `_root_bound_git_environment` | **Killed**: the explicit-root probe failed for `GIT_DIR`, `GIT_WORK_TREE`, and both. |
| Empty selector values deny by key presence | Replaced membership with `os.environ.get(name)` truthiness | **Killed**: empty `GIT_DIR` and empty `GIT_WORK_TREE` cases allowed and failed. |
| Denials do not leak selector values | Rendered `NAME=value` in the denial | **Killed**: policy and hook secrecy assertions both failed. |
| Selector denial precedes approval lookup | Added a no-op `has_valid_approval(...)` call before selector inspection | **Survived**: three new denial tests all passed; finding I-02. |
| Both selectors empty still deny | Exempted exactly the both-present/both-empty combination | **Survived**: three new denial tests all passed; finding I-03. |
| Clean exact tag grant remains allowed | Added unconditional clean `git-push-tag` denial | **Survived**: all 27 policy tests passed; finding I-01. |

## Unexecuted claims and limits

- A mutant that actually executes `git push` or opens a network connection was intentionally not run because both are expressly forbidden. Current absence was established with exec/network tracing instead.
- The already-reported full verifier PASS was not treated as proof of test adequacy and was not rerun by this reviewer. Focused and nearby suites were independently executed as listed above.
- External Trust CI, branch protection, pull-request delivery, and merge eligibility are outside this local test review.

---

## Re-review — repaired test matrix

Re-review date: 2026-09-25.

### Final verdict

**PASS.** At repaired HEAD `57c249d2b8543742bdfdcbaba364797a86ab489f`, all three blocking findings from the initial review are closed and their equivalent mutants are killed. The initial FAIL above remains historical evidence for HEAD `5f4e8fef003271a9b62198d181ad6be1f1838158`; it does not describe this repaired head.

No Critical or Important finding remains. Minor finding M-01 remains applicable: the real-hook tests observe safe behavior but do not impose a hermetic process-level push/network prohibition. Independent tracing again observed no Git push and no network syscall in the repaired tests.

### Re-review binding

- Base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`
- Repaired head: `57c249d2b8543742bdfdcbaba364797a86ab489f`
- Git tree: `2ac21d83a525ab70187045e19b682dea953fe208`
- Clean committed-tree fingerprint before re-review: `e50bf7e4d44594a60f8558646c7f3f988c93b4a0f463250a9a6323a0d2c08ce3`
- Repaired test hashes: `tests/test_policy.py` `090e873380370cd79a7efc6aeb14d47beab74a72edb21be189e2b2905924ed82`; `tests/test_hooks.py` `8999813656e4c1914fc88783e6765708a85c4cdfe81c436a4a4f0f662eb26bd9`.
- Production policy hash remained `d4e7db99b64297f41d0684422e15f52e836c29f8614e035139ddfc30b5ec5e98`; this repair changes regression tests, not production behavior.
- Fresh private scratch: `/tmp/issue227-test-rereview.g0q8Iu/review`, parent mode `0700`, local `--no-local --no-hardlinks` clone checked out at the repaired head.
- Scratch was restored after every mutant; its final status and `git diff --check` were empty.
- A concurrent modification to another reviewer's evidence report appeared during this re-review. It did not change HEAD, the Git tree, or any reviewed production/test hash and was not modified by this reviewer.
- `reviewed-tree-modified: no`

### Closure evidence

#### I-01 closed — selector-free valid tag grant

`tests/test_policy.py:224-240` explicitly removes both selector keys, creates a grant containing only `git-push-tag`, evaluates `git push origin v2.1.0`, and requires allow. An unconditional clean tag denial was **killed**: the dedicated test failed with `False is not true: Production action git-push-tag denied.`

#### I-02 closed — selector denial precedes approval lookup

`tests/test_policy.py:197-222` patches the exact legacy-policy lookup symbol with an exception and `assert_not_called()`. It separately covers branch push with non-empty `GIT_DIR` and tag push with empty `GIT_WORK_TREE`, while retaining selector-specific and secret-safe denial assertions. Inserting `has_valid_approval(...)` before selector inspection was **killed**: both branch and tag subtests failed at the forbidden lookup.

#### I-03 closed — both selectors empty in core and real hook

The core table now contains `empty-both` at `tests/test_policy.py:174-176`, and the subprocess integration at `tests/test_hooks.py:235-255` passes both empty variables through the real pre-tool hook and requires the complete denial output. Exempting exactly the both-present/both-empty combination was **killed** by both layers: core unexpectedly allowed and hook returned `allow` instead of `deny`.

### Re-review commands and results

All commands used `env -u GIT_DIR -u GIT_WORK_TREE`; no fetch, push, network request, Daybreak call, external write, commit, merge, or deployment was performed.

1. `python3 -m unittest tests.test_policy tests.test_hooks tests.test_util_fingerprint`

   Result: `Ran 83 tests in 40.146s — OK`.

2. Repaired four-test set under `strace -f -qq -e trace=execve,network` in restored scratch:

   - selector-free exact tag grant;
   - branch/tag denial-before-lookup;
   - complete selector-presence table;
   - both-empty real-hook integration.

   Result: `Ran 4 tests in 3.931s — OK`; exact Git push exec count `0`, `AF_INET`/`AF_INET6` connect count `0`, and total traced network syscall count `0`.

3. `git diff --check cb9af4073ba6c3d515145164d771c75ebdfa3224..57c249d2b8543742bdfdcbaba364797a86ab489f`

   Result: exit `0`, no output.

The coordinator-reported full `grok_verify --mode pr` PASS was considered supporting context, not substituted for this independent source inspection and mutation work.
