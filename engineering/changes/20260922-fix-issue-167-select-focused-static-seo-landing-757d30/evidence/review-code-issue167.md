# Code review — issue #167

Decision: PASS. No blocking code findings.

## Exact candidate identity

- Worktree: /tmp/agbp-issue167-static-scope
- Branch: fix/issue-167-static-scope-20260922
- HEAD reviewed: 526255f4ec7fd3ef00d45641da571c54f40cbe0f
- Route/base: 130ce4a42d9f9bbd1b56772d40b19ae530283205
- Repository fingerprint: 9cdee9f712cc80dd5ce16636788716bcb621581589d5fc8553a2d81d1c4d44bd
- Git tree: 7251b1fc383aca958f0803683a6187522fc50d37
- Worktree at review: clean
- reviewed-tree-modified: no
- Scratch: not used in this read-only re-review; no mutation claim is made from a private scratch.
- This report records the candidate before the report itself and final receipt were persisted.

## Scope probes

    git diff --name-status origin/main..HEAD
    git diff --check origin/main..HEAD
    git status --short --branch
    rg -n 'focused-static-seo-landing|select_static_seo_landing_scope|_verification_command' .grok-stack scripts tests

The 26-path candidate contains the focused verifier, status/provenance utilities, workflow allowlist, regression tests, AGENTS/skill wording, decisions/mistakes, and the change package. It contains no side-project landing, showcase, package, architecture, Trust CI deployed-policy, or GitHub Actions change.

## Reviewed behavior

- Focused classification accepts only a positive product inventory under side-projects/seo-landings plus one explicitly named focused test in one landing directory; active change-package evidence is excluded from product classification.
- Mixed or unknown paths, multiple landing directories, missing or ambiguous tests, malformed paths, unsafe Git statuses, and invalid provenance fail closed.
- A rejected focused scope does not dispatch the landing contract subprocess.
- --mode pr remains the full path and never silently downgrades.
- Workflow dispatch accepts the exact focused command and rejects extra arguments.
- Trust CI remains the external exact-SHA merge authority.

## Claim outcomes

- Current HEAD, base, tree, and repository fingerprint: killed stale-identity mutant; values matched the candidate.
- Full-PR downgrade from focused mode: survived; explicit mode branches remain separate.
- Unsafe status/provenance accepted as focused: survived; deleted, renamed, copied, malformed, and ambiguous records are rejected.
- Rejected scope executes a landing contract: survived; subprocess is suppressed.
- Workflow allowlist accepts arbitrary focused flags: survived; exact command is required.
- Trust boundary weakened by local focused mode: survived; no deployed Trust CI or merge authority path changed.
- Unexecuted mutation probes in this re-review: private-scratch mutation testing was not repeated because the prior scratch report covered the same pre-persistence implementation; the current review independently checked the exact committed tree and current focused tests.

## Limitations

- The reviewer did not validate the external App-owned Trust CI check.
- The final verification receipt must be rerun after this report and tasks file are persisted because that persistence changes the repository fingerprint.

## Final assessment

The issue #167 implementation is bounded and fail-closed. It provides a fast contract-only path only after positive classification and retains the full PR verifier for every mixed or uncertain change.
