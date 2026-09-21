# #53: separate promotion policy from repository path safety

## Evidence and trust boundary

Fetched `main` has neither the malformed `trust-ci/C:...` path nor `trust-ci/tests/test_promotions.py`. The retained `policy/production-only-human-approvals` branch has a full promotion contract test, models, signing functions, migration `004`, API, store, provenance and operational changes. Its Trust CI diff is large; copying only the test to main would not make the contract executable. The issue's original path writer is unknown. Existing `scripts/install_into.py:_path_parts` rejects backslashes for managed paths, but that does not prove it owned the bad write. `.grok-stack/adaptive_grok/architecture.py:_tracked_dot_venv_paths` validates Git path canonicality for its drift inventory, not a general pre-commit path guard. Repository edits cannot deploy Trust CI policy, keys, holdout, branch protection or human approvals.

## Workstream A — path safety, independent of promotion feature

Implement a bounded read-only tracked-and-untracked path preflight in the relevant local structure/doctor check. Consume NUL-delimited Git inventory, reject literal drive prefixes (`C:` style), backslashes, parent traversal and control characters in repository-relative paths, and give the exact offending path and a remedy without reading file content. Test a temporary repository with a literal Windows-path directory and with benign colon usage if the rule allows it. Apply the guard at a point before local receipt/commit preparation; do not claim it intercepts all arbitrary file-writing tools. If the original writer is identified, separately fix its platform-aware path normalization at the input boundary. Do not delete a malformed file automatically: it might contain unique contract tests.

## Workstream B — retained promotion policy successor

First compare the retained branch against current main, decompose the policy into a current design and migration plan, and identify the exact active external Trust CI policy/holdout version. Rebase or reimplement bounded slices in a new PR-only branch with migration compatibility, canonical envelope validation, TTL/scope/tamper tests, database role tests, API error behavior, and recovery. The old test is candidate evidence, not merge authority. Review must include security, data, release and independent exact-head Trust CI; human-signed approvals remain outside the agent environment. No deployment, signing-key access, policy switch or production promotion is part of source delivery.

## Acceptance boundaries

- Path preflight catches the malformed-path class before a local commit; it does not alter any file.
- A future policy PR's tests actually run against its implementation and migrations; they do not pass as orphaned tests or because a branch once contained them.
- Current source policy and deployed policy are described separately, and promotion is not called active until the external rollout and required signed approvals occur.

The two workstreams should have separate routes and PRs. Path safety is small and reversible; production-only promotion is security-sensitive and requires a named human gate for external activation.
