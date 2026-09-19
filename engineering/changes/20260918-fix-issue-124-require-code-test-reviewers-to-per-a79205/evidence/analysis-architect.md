# Architecture analysis — issue #124

## Required invariant

Code and test reviewers perform destructive/mutating experiments only against a private scratch snapshot outside the submitted worktree. The reviewed source worktree remains read-only to the reviewer except for the review report itself. A review must identify the exact source snapshot it assessed; scratch state is disposable and never flows back into the product tree.

## Source identity and snapshot integrity

- Record the reviewed repository's `git rev-parse HEAD` and `adaptive_grok.util.tree_fingerprint(root)` before creating the scratch copy. HEAD alone is insufficient because the candidate commonly contains uncommitted changes; the existing tree fingerprint binds HEAD plus relevant tracked, staged, and untracked file content while excluding designated runtime/cache noise.
- The scratch copy must represent that same worktree snapshot, including candidate modifications required by the review. A bare `git archive HEAD` is insufficient for a dirty candidate unless the reviewed diff and relevant untracked files are applied and verified. Do not treat a synthetic scratch commit or scratch HEAD as the identity under review; it is only a mechanism for executing tests.
- Capture and compare the source fingerprint around snapshot creation and again before completing the report. If the source changes during copying or review (for example, because the write owner continues work concurrently), discard/restart the snapshot or mark the review stale; never issue a passing current-tree verdict for a different fingerprint. The report file is the sole reviewer-authored exception in the worktree and should be written after the final source-integrity observation.
- Report source HEAD and fingerprint separately from scratch path/identity. Scratch mutations must not be copied, cherry-picked, restored, or otherwise applied to the reviewed tree.

## Trusted scratch parent

Create a unique per-review directory with mode `0700` beneath an owner-controlled cache such as `$HOME/.cache`. Validate canonical path ancestry before creating or using it: ancestors must be owned by root or the effective user and must not grant group/world write or rename authority. Require a trusted non-sticky parent; do not rely on a sticky shared directory as the trust boundary. The final scratch directory must be owned by the reviewer and private (`0700`). Do not place mutable test copies directly under `/tmp` or another shared writable parent. Fail closed when ownership, symlink resolution, or permissions cannot be established.

## Evidence and rollback boundaries

The durable report should state `reviewed tree modified: no`, the source HEAD and pre/post fingerprint, canonical scratch path, the claims actually exercised, exact commands, exit status, and concise output/result for each claim. “No” refers to reviewer mutations of product inputs; the report itself is the explicitly allowed worktree write. Distinguish static inspection from execution in the report and do not claim that a scratch run proves claims it did not execute.

Mutant files, generated artifacts, caches, and any failed intermediate state stay under the private scratch directory. Cleanup may remove only the exact reviewer-owned scratch leaf after evidence is captured; cleanup failure is reported and does not authorize touching the reviewed worktree. If a mutant run changes the reviewed source tree, the review is invalid, must fail closed, and must not be repaired by an automatic restore from scratch or by an unreviewed reverse patch. The writer/coordinator then compares the original and current fingerprints and recovers source changes through normal version-control review.

## Compatibility and scope

Update both code/test reviewer role briefs and the shared report guidance/template so the same invariant and report fields apply to each role. Test the instructions/report contract in the repository's existing prompt/template tests. Keep mutation tooling, automated copying, scratch cleanup, and receipt schema changes out of scope unless needed by current tests: issue #124 requests a mandatory reviewer procedure and report evidence, not a new executor or authority mechanism. Existing fingerprint-bound review receipts remain the authority for current local state; they must be recorded only after the report is complete and the exact reviewed tree is still current. External Trust CI remains independent and is not replaced by local scratch evidence.
