# Issue 227 Git Environment Grant Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent inherited `GIT_DIR`/`GIT_WORK_TREE` from making a delegated grant authorize a Git push whose execution repository differs from the explicit policy root.

**Architecture:** Apply two independent controls. Internal read-only Git probes receive a copied environment with repository selectors removed, while the production Git-push policy rejects selector presence before consuming any grant. Tests use disposable local repositories and inspect `pushurl`; they never execute push or use the network.

**Tech Stack:** Python 3 standard library, `unittest`, local Git fixtures, repository policy/hooks.

**Spec:** `engineering/changes/20260925-fix-issue-227-inherited-git-dir-or-git-work-tree-177f5d/change-spec.yaml`

## Global Constraints

- Local-only implementation; no push, GitHub write, merge, deployment, network access or Daybreak dependency.
- Preserve grant schema v2, legacy binding-field reads and `has_valid_approval(...) -> bool`.
- Denials may name `GIT_DIR`/`GIT_WORK_TREE` but never their values.
- Root-local `pushurl` mutation without inherited selectors remains out of scope.
- Exactly one write owner changes application code.

## Review Focus

- Empty selector values must deny just like non-empty values.
- Selector values and foreign paths must not leak in denial text.
- Sanitizing probes without denying execution would recreate split-brain authorization.
- Clean-environment exact-action grants must keep working.
- All direct Git probe paths, including binary `-z` inventory helpers, must use the same sanitized environment.

---

### Task 1: RED tests for root-bound Git probes

**Files:**
- Modify: `tests/test_util_fingerprint.py`
- Test: `tests/test_util_fingerprint.py`

**Interfaces:**
- Consumes: `adaptive_grok.util.git_head`, `changed_files`, `changed_file_statuses`, `tree_fingerprint`.
- Produces: regression expectations that every probe stays bound to root A under foreign selectors.

- [ ] **Step 1: Add a disposable foreign-repository test**

Create root A with a dirty tracked file and root B at a different HEAD. For each environment case (`GIT_DIR`, `GIT_WORK_TREE`, both), patch `os.environ`, then assert literal equality with A's clean-environment HEAD, changed-file set/statuses and fingerprint.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python3 -m unittest tests.test_util_fingerprint`

Expected: FAIL because at least one probe selects B or returns an inventory derived from B.

- [ ] **Step 3: Do not edit production code yet**

Record the failing assertion and command in `evidence/implementation-general_implementer.md`.

### Task 2: RED tests for policy and hook denial

**Files:**
- Modify: `tests/test_policy.py`
- Modify: `tests/test_hooks.py`
- Test: `tests/test_policy.py`
- Test: `tests/test_hooks.py`

**Interfaces:**
- Consumes: `evaluate_pre_tool(root, event) -> tuple[bool, str | None]` and the real pre-tool hook subprocess.
- Produces: fail-closed behavior before grant lookup whenever a selector key is present.

- [ ] **Step 1: Add the same-tree foreign-pushurl policy fixture**

Create grant repository A, clone it locally to B, retain the expected fetch URL, set only B's push URL to a literal foreign URL, and patch inherited selectors to B. Evaluate `git push origin feature` without executing it. Assert `allowed is False`, the reason names the selector, and neither the selector value nor foreign URL appears.

- [ ] **Step 2: Add table cases for `GIT_DIR`, `GIT_WORK_TREE`, both and empty values**

Use literal expected variable-name fragments and assert the existing clean-environment grant still allows only `git-push-branch`.

- [ ] **Step 3: Add hook-level subprocess coverage**

Pass the inherited selector through the hook test environment with payload cwd=A. Assert nonzero/deny output and secret-safe reason; do not include a push executor.

- [ ] **Step 4: Run the focused tests and verify RED**

Run: `python3 -m unittest tests.test_policy tests.test_hooks`

Expected: FAIL because current policy returns allow for the crafted matching foreign checkout.

### Task 3: GREEN root-bound probes and early denial

**Files:**
- Modify: `.grok-stack/adaptive_grok/util.py`
- Modify: `.grok-stack/adaptive_grok/_policy_legacy.py`
- Test: `tests/test_util_fingerprint.py`
- Test: `tests/test_policy.py`
- Test: `tests/test_hooks.py`

**Interfaces:**
- Produces: one private Git-probe environment helper that removes exactly `GIT_DIR` and `GIT_WORK_TREE`.
- Preserves: public `run`, `git_output`, `has_valid_approval` and `evaluate_pre_tool` signatures.

- [ ] **Step 1: Implement one private root-bound Git environment helper**

Copy `os.environ`, remove the two selector keys by presence, and pass the resulting complete environment to every internal read-only Git subprocess used by `git_output`, `_git_paths` and `_git_name_status`. Do not change arbitrary command execution semantics.

- [ ] **Step 2: Implement early production Git denial**

After classifying a branch/tag push but before human-gate/grant lookup, inspect `os.environ` by key presence. Return false with a bounded message such as `Inherited GIT_DIR/GIT_WORK_TREE repository selectors are not allowed for Git push; unset them and retry.` Include only the names actually present.

- [ ] **Step 3: Run focused tests and verify GREEN**

Run: `python3 -m unittest tests.test_policy tests.test_hooks tests.test_util_fingerprint`

Expected: all tests pass; no network or push command appears in test execution.

- [ ] **Step 4: Run nearby contract tests**

Run: `python3 -m unittest tests.test_structure tests.test_change_receipts`

Expected: all tests pass.

### Task 4: Verification and evidence

**Files:**
- Modify: `engineering/changes/20260925-fix-issue-227-inherited-git-dir-or-git-work-tree-177f5d/evidence/implementation-general_implementer.md`
- Modify: `engineering/changes/20260925-fix-issue-227-inherited-git-dir-or-git-work-tree-177f5d/tasks.md`

**Interfaces:**
- Consumes: final source/test tree.
- Produces: exact RED/GREEN evidence, changed-file list and residual-risk statement.

- [ ] **Step 1: Run static checks**

Run: `git diff --check`

Expected: no output, exit 0.

- [ ] **Step 2: Commit the implementation before final receipts**

Stage only the issue-227 change package, plan, source, tests and required decision/mistake entries. Commit locally with `fix(policy): bind git grants to explicit repository root`.

- [ ] **Step 3: Run route verification on the committed tree**

Run: `python3 scripts/grok_verify.py --mode pr`

Expected: `RESULT: PASS` and a current fingerprint-bound verification receipt.

- [ ] **Step 4: Request independent reviews**

Dispatch exactly the route's code, test, security and release reviewers against the same head. Any source change after review requires fresh verification and affected reviews.

## Self-review

- Spec coverage: AC-001 is Tasks 1/3; AC-002 and AC-003 are Tasks 2/3; AC-004 is the clean-environment compatibility arm in Task 2.
- Placeholder scan: no implementation placeholders or deferred scope are present.
- Type consistency: public tuple/bool APIs remain unchanged; the new helper is private.
- Review focus: all five listed failure modes are exercised by Tasks 1-3.
