# Independent security review — issue #218

Verdict: FAIL. Critical: 0. Important: 2. Minor: 0.

## Source and isolation

- Candidate: `/home/pall/grok-projects/adaptive-grok-build-issue218-delivery`.
- Route: `566746aef130`.
- Base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`.
- HEAD before and after: `e824fb1551ff37ab647c52b00a1fce38ede79213`.
- HEAD tree: `0e1c4b188503793d48d61ded35afedf109170e3d`.
- Candidate fingerprint before and after: `4e84b701ed15ca39741205a37517b18306ef5a7708ccfd0d5e83ad7e945f2104`.
- Dirty snapshot: only `engineering/changes/20260925-fix-github-issue-218-locally-deliver-the-verifie-566746/state.json`, preserved in the scratch copy.
- Private scratch: `/home/pall/security-review-218.DxnK40jl`, created by `mktemp -d` with mode 0700 under owned, non-sticky `/home/pall` (mode 0750). Snapshot: `candidate/`; probe source: `probes.py`; this report: `security-review.md`.
- Scratch fingerprint before probes exactly matched the candidate fingerprint above. Only disposable fixture repositories and in-memory mutants were changed by the probes.

reviewed-tree-modified: no

This is a read-only independent review. No fetch, remote operation, external write, secret/private-key read, Trust CI configuration operation, or merge/publication action was performed. The offline-review instruction overrides the routine fetch entrypoint. A local clone accessed only the supplied filesystem repository.

## Important findings

### I-1: Endpoint blob limits are checked only after unbounded capture

`.grok-stack/adaptive_grok/verification.py:2030` (`_load_git_blob_contents`) invokes `cat-file --batch` and captures its entire output before parsing object sizes and enforcing `_MAX_SCAN_BLOB_BYTES` and `_MAX_SCAN_TOTAL_BYTES`. `util.py:188` uses `subprocess.run(capture_output=True)` without an output-byte ceiling. `_endpoint_whitespace_findings` reaches this helper for index/worktree comparisons during `_git_diff_check`.

A contributor-controlled oversized indexed blob can therefore make the verifier allocate its whole uncompressed body before returning the intended incomplete/failure response. Multiple objects compound the same issue. A subprocess timeout does not impose a memory bound. The history-scanning path already checks batch metadata before fetching bodies; the endpoint path lacks that protection.

Executed bounded probe P1 stored one synthetic 2,097,153-byte blob, with the production per-blob limit at 2,097,152. Instrumentation around the real Git runner observed exactly one call, `['cat-file', '--batch']`, capturing 2,097,208 stdout bytes. Only afterwards did the helper return `diff blob content exceeds its bound`. No metadata-preflight command was issued. This proves the ordering defect without an unsafe OOM experiment.

Required repair: validate all endpoint object metadata and aggregate sizes before requesting bodies, and/or stream through a hard output bound. Add regressions asserting oversized and aggregate-overlimit endpoint objects are rejected before any content retrieval. Preserve metadata-only errors.

### I-2: Dirty-worktree secret scanning has no aggregate resource budget

`.grok-stack/adaptive_grok/verification.py:2345` (`_secret_scan`) loops over every supplied worktree path and reads each supported file up to the per-file ceiling. It neither accounts for `_MAX_SCAN_TOTAL_BYTES` nor caps the worktree path count. It can therefore read arbitrarily many individually acceptable files and still report `coverage=complete`, defeating the scanner's aggregate resource-bound claim. New untracked and dirty files enter the inventory independently of the bounded committed-chain path-edge inventory.

Executed bounded probe P2 lowered `_MAX_SCAN_TOTAL_BYTES` to 16 and supplied two synthetic regular files containing 12 bytes each. The scanner read all 24 bytes and returned `status=pass`, `summary='0 potential secrets; coverage=complete'`, with no details. At the production limit, the same missing check allows worktree reads past 512 MiB. This is an availability/resource-bound defect; it is not a demonstrated secret-detection bypass for files actually read.

Required repair: introduce an explicit aggregate worktree byte/path budget, enforce it before further content reads, and return typed incomplete coverage on exhaustion. The worktree scope must never claim complete after the budget is exceeded. Add meaningful aggregate tests involving multiple files, including coverage recomputation.

## Threat model and controls assessed

Assets are source confidentiality, exact-repository scan identity, complete selected-chain coverage, local receipt integrity, and verifier availability. Actors include a contributor controlling commits, blobs, attributes and paths; a local process supplying inherited Git controls or changing files during inspection; and a caller supplying forged local scope data. Entry points are selected-base/ref resolution, raw Git edge inventories, object loading, endpoint/index/worktree inspection, and receipt validation. The host executable and local Git administrative directory remain trusted; this is not an OS isolation boundary.

Read AGENTS.md, the active route, adaptive-delivery/security-sensitive-change/bugfix-workflow/api-event-change skills, current requirements and architecture, the complete historical #218 security report (including the four original findings, hostile-whitespace follow-up, quadratic-comparison finding, and later historical PASS), and the cumulative #227 security report. Inspected the cumulative changed-file inventory and surrounding implementations for Git execution, range selection, graph enumeration, object and whitespace scanning, scope recomputation, and descriptor-based worktree reads.

Prior findings have effective corresponding controls in this candidate:

- Root binding: selected-base, graph, object and whitespace Git operations share the explicit-root runner, minimal environment, disabled replacements, and relevant local-command overrides. Focused ambient-selector/config/replace-ref regression passed.
- Hostile whitespace configuration/attributes: deterministic internal classification supplements Git's configurable checks; chain and endpoint hostile-attribute regressions passed.
- Scope forgery: the validator reconstructs scan coverage, rejects findings and incomplete results, rescans current worktree bytes and compares the whole scope. Coverage-field and add-then-delete/scanless-forgery regressions passed; M3 killed.
- Object and filesystem types: committed symlink blob inspection, gitlink rejection, dirty symlink/broken-link/FIFO rejection, and named-file replacement regression passed. Descriptor-relative no-follow reads and identity comparisons were inspected; M2 killed.
- Confidentiality: secret-bearing whitespace diagnostics regression passed. Reports contain location/code metadata rather than matched body lines.
- CPU classification: explicit shared operation accounting, monotone clean anchors and bounded matching replace the historical unbudgeted quadratic matcher. Chain/endpoint exhaustion and shared-budget regressions passed; M1 killed. This does not close I-1/I-2.
- Chain completeness: transient-secret, commit-bound, every-merge-parent, and intermediate-whitespace regressions passed.
- `git diff --name-only cb9af4073ba6c3d515145164d771c75ebdfa3224 HEAD -- trust-ci` returned no paths. No `trust-ci/**` change was present in the reviewed cumulative commit.

## Executed commands and results

Source identity, run before and after review in the candidate:

```text
git rev-parse HEAD HEAD^{tree}
PYTHONDONTWRITEBYTECODE=1 python3 -c 'import sys; from pathlib import Path; sys.path.insert(0,".grok-stack"); from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))'
git status --short
git diff --name-only cb9af4073ba6c3d515145164d771c75ebdfa3224 HEAD -- trust-ci
```

Observed identities match the source binding above; status contained only the stated dirty state.json; Trust CI path output was empty.

Snapshot setup:

```text
stat -c '%a %U %n' /home/pall /home/pall/grok-projects
mktemp -d /home/pall/security-review-218.XXXXXXXX
git clone --no-hardlinks --no-checkout /home/pall/grok-projects/adaptive-grok-build-issue218-delivery /home/pall/security-review-218.DxnK40jl/candidate
git checkout --detach e824fb1551ff37ab647c52b00a1fce38ede79213
cp /home/pall/grok-projects/adaptive-grok-build-issue218-delivery/engineering/changes/20260925-fix-github-issue-218-locally-deliver-the-verifie-566746/state.json engineering/changes/20260925-fix-github-issue-218-locally-deliver-the-verifie-566746/state.json
```

Checkout/copy ran in scratch, not the candidate. The fingerprint command then returned the exact same fingerprint as the candidate.

Executable probe command, with all temporary repositories under private scratch:

```text
PYTHONDONTWRITEBYTECODE=1 TMPDIR=/home/pall/security-review-218.DxnK40jl python3 /home/pall/security-review-218.DxnK40jl/probes.py
```

`probes.py` selects VerificationTests whose source lines fall in 1225..2010, plus `ReceiptTests.test_identity_only_scan_scope_cannot_hide_add_then_delete_secret` and `ReceiptTests.test_scan_scope_coverage_and_completion_claims_must_match_recomputation`. Exact observed output:

```text
baseline tests=25 failures=0 errors=0
M1-reset-shared-budget tests=1 failures=1 errors=0
M2-trust-unsafe-worktree tests=1 failures=3 errors=0
M3-trust-forged-scope tests=1 failures=5 errors=0
P1-oversize-endpoint: limit=2097152 payload=2097153 captured_stdout_bytes=2097208; error=diff blob content exceeds its bound
P2-worktree-aggregate: aggregate_limit=16 bytes_read=24; status=pass coverage=complete
```

The script itself exits 0 after recording expected mutant failures and probe observations; its exit code is not a suite-pass claim.

## Mutation results

- M1, reset the whitespace budget to a fresh 36 operations for every comparison: killed by `test_chain_wires_one_aggregate_whitespace_budget_across_edges`, which observed incorrect complete coverage.
- M2, replace the safe file reader with an unconditional clean-content result: killed by `test_worktree_scan_rejects_symlinks_broken_links_and_fifos`, with three failing subcases.
- M3, replace complete-scope validation with unconditional True: killed by `test_scan_scope_coverage_and_completion_claims_must_match_recomputation`, with five failing field-mutation subcases.
- No surviving or inconclusive implementation mutants in this bounded set. P1/P2 are adversarial probes of unchanged production code and expose the two findings above; they are not mutation-score successes.

## Unexecuted claims and limits

The complete PR verifier was not rerun by this reviewer; its reported preliminary PASS is coordinator-provided evidence. No OOM, 512-MiB worktree, or wall-clock exhaustion test was attempted; bounded instrumentation demonstrates the missing controls. No independent production-scale CPU benchmark, full platform matrix, arbitrary filesystem race schedule, or malformed Git-object fuzz campaign was executed. Other predecessor-stack modules received only review context, not a fresh exhaustive security audit. External Trust CI, deployed policy, signed approvals, and branch protection were not queried. Static inspection is not represented as executable proof.

The candidate remains FAIL pending resource-bound repairs and affected re-review. This report is local workflow evidence only and authorizes no push, merge, tag, release, deployment, or external action; App-owned exact-SHA Trust CI and required signed approvals remain separate.
