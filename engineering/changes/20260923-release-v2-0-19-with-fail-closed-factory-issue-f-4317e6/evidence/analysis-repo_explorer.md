# Repository exploration: issues #35, #36, #39, #48, #73, and #167

Observed 2026-09-23 after `git fetch --all --prune`. The comparison base is `origin/main` at `130ce4a42d9f9bbd1b56772d40b19ae530283205`. Each issue branch and the release branch points at that same commit; all issue work described below is uncommitted worktree content. There are no issue-branch commits to cherry-pick.

## Exact worktrees and candidate files

| Issue | Worktree / branch | Repository-owned candidate files outside its change package | Disposition visible in worktree |
|---|---|---|---|
| #35 | `/tmp/agbp-issue35-bash-syntax` / `fix/issue-35-bash-syntax-20260922` | `.grok-stack/adaptive_grok/verification.py`; `tests/test_verification_doctor.py` | Adds `_bash_syntax`, runs it for changed `.sh` files, and tests a syntax error in a later file. |
| #36 | `/tmp/agbp-issue36-recorder-status` / `fix/issue-36-recorder-status-20260922` | None | Only the untracked issue change package exists. Its brief records a no-op/cancelled disposition because no repository-owned shell recorder was found. |
| #39 | `/tmp/agbp-issue39-lint-scope` / `fix/issue-39-lint-scope-20260922` | `.grok-stack/adaptive_grok/verification.py`; `tests/test_verification_doctor.py` | Changes Ruff/Bandit scope selection and summaries; adds changed-file and deep-owned-root tests. |
| #48 | `/tmp/agbp-issue48-silent-green` / `fix/issue-48-silent-green-20260922` | `trust-ci/scripts/smoke.sh`; new `trust-ci/tests/test_smoke.py`; `decisions.md`; `mistakes.md` | Historical candidate only; its `trust-ci/**` paths are not imported because `FIT-TRUST-CI-SEPARATION` forbids mixing them with this release's implementation paths. |
| #73 | `/tmp/agbp-issue73-evidence-digest` / `fix/issue-73-evidence-digest-20260922` | `.grok-stack/adaptive_grok/state.py`; `tests/test_history.py`; `tests/test_policy.py` | New grants write `grant_binding_digest`; reads remain compatible with legacy `tree_fingerprint`; records containing both fields fail closed; historical probe evidence is hash-pinned. |
| #167 | `/tmp/agbp-issue167-static-scope` / `fix/issue-167-static-scope-20260922` | `.agents/skills/adaptive-delivery/SKILL.md`; `.grok-stack/adaptive_grok/util.py`; `.grok-stack/adaptive_grok/verification.py`; `.grok-stack/adaptive_grok/workflow_artifacts.py`; `AGENTS.md`; `scripts/grok_verify.py`; `tests/test_util_fingerprint.py`; `tests/test_verification_doctor.py`; `tests/test_workflow_artifacts.py`; `decisions.md`; `mistakes.md` | Adds fail-closed Git status/provenance inventory and an explicit `focused-static-seo-landing` verifier mode, CLI/allowlist support, tests, and workflow documentation. |

Every worktree also contains one untracked `engineering/changes/20260922-fix-issue-.../` package. Those packages are workflow evidence, not implementation. The release worktree already has its separate route package.

## Overlap and conflict assessment

- #35, #39, and #167 all modify `.grok-stack/adaptive_grok/verification.py` and `tests/test_verification_doctor.py`.
- Their current base-line hunks do not directly overlap: #35 inserts near verifier base lines 693 and 1124 and test lines 30/294; #39 changes verifier lines 858-936/1135 and inserts tests near 1354; #167 changes verifier inventory/control flow near lines 2-606/1087 onward and inserts tests near 21/321. They are logically adjacent and large #167 insertions shift later locations, so the release owner should compose them in one current-base edit and rerun the combined tests. No independent branch commit exists to preserve review boundaries automatically.
- #48, #73, and #167 share no implementation or test paths with one another. #48 is excluded from this release by the Trust CI separation rule; its append-only records are not imported.
- #36 has no product delta and therefore no code conflict.
- No candidate changes `VERSION`, `README.md`, `PROJECT_STATE.json`, release metadata, M8 qualification code, or a `DEV` tree.

## Scope and unrelated-change findings

### #35

The product edits contradict the same worktree's durable brief. That brief says the repository has no owning multi-file `bash -n` seam, dispositions #35 as no-op/cancelled pending #186, and explicitly lists “adding a new shell verifier” and changing the Python verifier as out of scope. The `_bash_syntax` implementation and its test are therefore speculative/unrelated to the recorded #35 repository scope and should not be imported as #35 without replacing that disposition with evidence that the generic verifier is the approved owner.

### #36

No unrelated product changes exist because no product changes exist. Importing its change package would record only the historical no-op/handoff, not a fix.

### #39

The product edits also contradict the same worktree's durable brief. The brief says #39 concerns an external JavaScript/ESLint workspace, dispositions it as no-op/cancelled pending #186, and explicitly excludes reinterpreting local Ruff/Bandit behavior as the fix. The Python Ruff/Bandit changes and tests are therefore unrelated to the recorded #39 owner scope and should not be imported as #39 without a new approved repository-owner mapping.

### #48

The #48 worktree contains a bounded smoke hardening core plus a separable command-discovery
expansion, but every implementation path is under `trust-ci/**`. Since this release also changes
implementation prefixes, `FIT-TRUST-CI-SEPARATION` excludes the entire #48 slice from the final
tree; its code and tests remain available on the separate issue branch and the disposition stays
linked through #186.

### #73

The three source/test files are internally aligned with the package's proposed neutral-name and compatibility design: current grant creation changes one field, legacy reads remain accepted, conflicting dual fields fail closed, and historical artifacts are not rewritten. No unrelated source change was found. The package brief still states a pending `scope_and_design_approval` gate; the current release route has no human gate, but that does not by itself rewrite the issue worktree's recorded gate status.

### #167

All eleven modified files map to focused static-landing verification: status provenance, fail-closed scope classification/execution, CLI and workflow-command allowlisting, contract tests, and operator documentation. The `decisions.md` and `mistakes.md` additions are related workflow records. No unrelated M8/DEV or release-metadata change was found. This is the broadest candidate (1,130 insertions and 8 deletions across tracked files at observation time) and is the principal integration surface for #35/#39 because of the two shared files.

## Integration facts

1. The independently reviewable implementation units currently available are worktree diffs, not commits.
2. #36 supplies no implementation unit.
3. #35 and #39 currently supply implementation units that conflict with their own recorded no-op scopes.
4. #48 has a bounded in-scope core plus a separable command-discovery expansion, but neither is
   eligible for this mixed release because of `FIT-TRUST-CI-SEPARATION`.
5. #73 is path-disjoint but retains a documented gate-status discrepancy that must be resolved by the coordinator.
6. #167 is self-contained but must be composed carefully with any accepted #35/#39 verifier changes because the same source and test files are modified.
