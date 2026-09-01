# Independent final test review — milestone state reconciliation

## Verdict

**FAIL**

- Route: `944abd96ddb3`
- Base: `origin/main` / `8ab4e57038dec2e07f01aaa0b207813a387358f4`
- Reviewed HEAD: `8439f62180f0df3b60498174a121450ea58eaa51`
- Reviewed range: `origin/main...8439f62180f0df3b60498174a121450ea58eaa51`
- Verification receipt fingerprint: `e5950a781ca5eae1b5ac5f5bc4086f6aeb602c2c2e228e0602ae789033d99f9e`
- Critical findings: none
- Important findings: 3

The checked-in snapshot currently agrees with live GitHub and local ref evidence, and the focused/full suites pass. PASS is blocked because the new tests do not protect the exact branch/PR/SHA facts they label truthful, the graph test does not protect exact node identity, and the verifier's passing diff check does not cover the committed PR range.

## Findings

### Important — `tests/test_project_state.py:31-59,76-91` permits false exact-SHA, branch-base, and gate facts

The milestone test asserts axis status strings but not the commits, PR bases, merge targets, heads, or ancestry that justify those statuses. The inventory test asserts only the set of four open PR numbers and a few membership facts; it does not validate the recorded PR branches, bases, heads, statuses, dispositions, all PRs, or the complete local/remote branch inventory.

An in-memory adversarial mutation changed all of the following while preserving every current assertion exercised for those records:

```text
PR #17 base: milestone/m2-executable-architecture -> main
PR #17 head: 8e650416... -> 0000000000000000000000000000000000000000
PR #17 status: open_current_epoch_and_gitguardian_failure -> success
M2 implementation commit: 022411b... -> 0000000000000000000000000000000000000000

wrong_pr17_base_head_status_and_m2_commit_pass_current_assertions=TRUE
```

These are the contract's essential distinctions: stack integration versus main delivery and exact-head external authority. A synchronized error in `PROJECT_STATE.json` and the few duplicated constants can therefore pass. Add an immutable observed-inventory fixture or explicit assertions for every material PR's number/base/head/state/merge SHA/check conclusion, every milestone evidence SHA/target, and the exact branch inventory captured by the audit. Where a Git object is locally available, also assert existence and ancestry/merge-parent relationships.

### Important — `tests/test_project_state.py:93-109` calls the graph exact while deriving node identity from the graph itself

The test builds `nodes` from the current edges and then computes the expected K16 from that same derived set. It verifies topology and count, but not that the set is the required 16 core nodes or that it equals the 16-row node-role table.

I replaced every `GitHubApp` edge token with `FakeApp` in memory while leaving the role table unchanged. The current algorithm still passed all four claims: 16 nodes, 120 edges, 120 unique edges, and complete pair coverage:

```text
graph_wrong_node_identity_passes_current_algorithm=TRUE
```

Assert the explicit node set `{Route, Skills, Agents, Hooks, Policy, Verify, Packages, Contract, Decisions, Mistakes, TrustAPI, TrustWorker, Postgres, Runner, Holdout, GitHubApp}` and parse the node-role table to require exact identity equality. This is required for the repository's README graph contract, not merely cosmetic coverage.

### Important — committed PR diff fails whitespace validation while the full verifier records PASS

The exact reviewed range fails:

```text
git diff --check origin/main...8439f62180f0df3b60498174a121450ea58eaa51

engineering/changes/.../evidence/analysis-architect.md:3: trailing whitespace
engineering/changes/.../evidence/analysis-architect.md:4: trailing whitespace
engineering/changes/.../evidence/analysis-integration-architect.md:3-5: trailing whitespace
engineering/changes/.../evidence/analysis-repo-explorer.md:3-5: trailing whitespace
```

The current verifier receipt nevertheless records `git-diff-check: pass`, because its invocation observes no uncommitted work in this clean worktree rather than validating `origin/main...HEAD`. The change test plan likewise lists bare `git diff --check`, which is a no-op for committed changes. Remove the whitespace defects and make the PR-mode verifier bind diff validation to its resolved base/head range so the receipt cannot false-positive a committed diff.

## Passing evidence and current-fact audit

### Focused tests — PASS, subject to coverage gaps above

```text
python3 -m unittest tests.test_project_state tests.test_structure -v
Ran 15 tests in 0.028s — OK
```

The four new state tests themselves ran in 0.003s and passed. JSON parsing, schema version 2, five axis keys for M0-M9, documented status values, current-section epoch/App text, selected inventory membership, and K16 topology/count are exercised.

### Full verifier receipt — PASS result, invalidated as completion evidence by finding 3

Receipt `.grok-stack/runtime/receipts/944abd96ddb3/verification.json`:

```text
created_at: 2026-09-01T19:01:18+00:00
status: pass
tree_fingerprint: e5950a781ca5eae1b5ac5f5bc4086f6aeb602c2c2e228e0602ae789033d99f9e
profiles: base, integration, infra
python-unittest: Ran 214 tests in 47.626s — OK
ruff / bandit / coverage / secret-scan / contract-structure / sql-safety: PASS
git-diff-check: reported PASS, contradicted by exact-range reproduction above
```

Before this report write, `grok_status.py` accepted verification as current and reported only the three review receipts missing.

### Live GitHub, epoch, App, and PR state — PASS at review time

Read-only GitHub queries independently confirmed:

- default branch `main` at `8ab4e57038dec2e07f01aaa0b207813a387358f4`;
- current open PRs exactly #12, #13, #15, and #17, with recorded bases/heads matching `PROJECT_STATE.json`;
- PR #19 merged into main as the recorded `8ab4e570...` commit;
- protected main strictly requires `adaptive-trust-ci/verified@06ecf1c875bc` from GitHub App ID `4694114`;
- PR #17 head `8e650416...` has failed Trust CI and GitGuardian Check Runs, and the Trust CI Check Run is owned by App ID `4694114`;
- the four milestone implementation commits named for M0-M4 are present as Git objects.

The current local branch count is 25 and remote non-PR branch count is 26, matching the complete named inventories in the analysis evidence. The analysis reports are timestamped observations at the earlier pre-PR-19-merge main and should remain historical evidence; `PROJECT_STATE.json`, README, and `START_HERE.md` correctly carry the later final observation.

### Schema compatibility — PASS with explicit version transition

Repository search found no executable consumer of `PROJECT_STATE.json` beyond the new test. The version 1 to version 2 change is intentional and documented as replacing ambiguous milestone fields with five explicit axes. Bootstrap readers are directed to the new `active_delivery` and `work_inventory` model, so there is no silent in-repository parser break. The coverage gap in finding 1 still needs repair so malformed or inaccurate v2 snapshots fail deterministically.

### Scope isolation — PASS

The exact diff changes state/bootstrap documentation, the root-cause log, the route's change package, and the new state test only. It does not modify Trust CI implementation/configuration, `DARK_FACTORY_ROADMAP.md`, historical `decisions.md`, GitHub Actions, or external state.

No product file was modified by this reviewer. This report is the only review-owned write.
