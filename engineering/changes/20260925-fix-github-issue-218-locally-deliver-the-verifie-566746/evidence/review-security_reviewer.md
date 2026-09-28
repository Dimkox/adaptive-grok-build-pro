# Independent security review — issue #218 delivery

## Review binding

- Verdict: **FAIL**
- Reviewed candidate: `cdad4de5cd9620a97d3919bc47c89ff923839623`
- Reviewed base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`
- Candidate tree: `49ec3bd103c7e22b9019b10e084bc7f9b4602d70`
- Route: `566746aef130`
- Reviewed-tree-modified: **no**
- Critical findings: **0**
- Important findings: **4**
- Minor findings: **0**

The candidate is a single-parent squash whose parent is the stated base. I reviewed the exact base-to-candidate diff and the surrounding Git execution, chain-scan, receipt-validation, and completion-binding logic. The coordinator reported the full pre-review verifier PASS. A focused independent run of the transient-secret, commit-bound, merge-parent, intermediate-whitespace, and scanless-receipt tests also passed (`Ran 5 tests ... OK`). Those successes do not exercise the bypasses below.

## Important findings

### I-1 — Selected graph and whitespace checks are not root-bound or configuration-isolated

Commit/ref resolution, PR-target selection, ancestry validation, and merge-base selection use the generic text runner (`verification.py:580-585`, `604-639`, `689-752`). The generic runner copies the complete ambient environment (`util.py:87-112`), including Git repository selectors and configuration controls. The later byte-oriented runner removes only a subset of selectors and does not disable replacement objects or isolate repository/system/global configuration (`util.py:128-145`). The worktree/index/range and chain whitespace checks also use the generic runner (`verification.py:1724-1758`).

Consequently, inherited `GIT_DIR`/`GIT_WORK_TREE` can redirect selection and diff validation to another repository, while replacement refs or hostile Git configuration can alter graph/object interpretation. Revalidating the stored scope does not close the boundary because `_scan_identity_matches_current` repeats the same selection and enumeration path (`verification.py:1648-1667`). This undermines the exact-HEAD/selected-base and fail-closed graph guarantees.

The repository already has the needed control pattern: a minimal environment, `GIT_CONFIG_NOSYSTEM`, null global config, `GIT_NO_REPLACE_OBJECTS`, `--no-replace-objects`, disabled attributes/excludes/hooks/fsmonitor/external diff, and an explicitly resolved repository root (`architecture_diff.py:159-206`, `211-228`). All selection, traversal, object, and diff commands in this security boundary should use one equivalent hardened seam. Add regressions for set-and-empty selector variables, replacement refs, hostile config, branches, and tags.

### I-2 — A receipt can claim complete scanning with forged coverage counters

`_scan_identity_matches_current` rederives and compares the graph identity, but it merely checks that `blob_count`, `bytes_scanned`, and `path_edge_count` are nonnegative integers (`verification.py:1648-1678`). Receipt acceptance relies directly on this predicate (`receipts.py:1047-1057`). A focused read-only probe built the genuine current identity, set `status` and `worktree` to `complete`, replaced all three counters with zero, and observed `forged_zero_counts_accepted=True`.

Thus the receipt does not prove the claimed blob/path coverage; a scope assembled without `_build_chain_scan` can satisfy current validation. Recompute the complete scan result during validation and compare all coverage fields, or bind a deterministic edge/path/blob/byte manifest digest and validate it exactly. Add mutation tests for every count/digest/status field and for a structurally valid but scanless scope.

### I-3 — Unsupported object/file types and dirty-file replacement races can be reported as complete

The history scanner records blob content only for modes beginning with `100`, silently excluding symlink (`120000`) and gitlink (`160000`) entries while retaining an otherwise complete scope (`verification.py:1497-1518`). The dirty-file scanner silently skips symlinks, missing paths, and all non-regular files (`verification.py:1815-1821`), then marks worktree coverage complete whenever no explicit coverage failure was appended (`verification.py:1839-1847`). This conflicts with the requirement to fail closed when complete inspection of symlinks, submodules, special files, deleted files, or unusual paths cannot be proved.

There is also a check/use race between `is_symlink`/`exists`/`is_file`, `stat`, and `read_bytes` (`verification.py:1815-1831`). A path can be replaced between those operations, allowing different bytes to be sized and scanned or a symlink target to be followed, then restored before the later tree-fingerprint check. Reject unsupported modes/types explicitly, define and safely scan symlink blobs if they are supported, reject gitlinks when their content cannot be covered, and use descriptor-relative no-follow opens plus stable pre/post identity checks for dirty regular files. Add symlink, broken-symlink, FIFO/special-file, gitlink, and replacement-race tests.

### I-4 — Raw `git diff --check` output can disclose secret values

For worktree, index, and selected-range checks, complete Git stdout and stderr are copied into the verification result (`verification.py:1724-1735`, `1793-1802`). `git diff --check` can include the offending added line after its location diagnostic. A line that contains both a credential and trailing whitespace can therefore place the credential value in local reports/receipts, contrary to the metadata-only and no-secret-value requirements. The later per-edge check is safer because it retains only a sanitized first-line path and fixed message (`verification.py:1750-1789`).

Do not retain unrestricted Git output. Parse only bounded path/line metadata and emit fixed diagnostics, with tests that place representative secret values on whitespace-error lines and assert the value is absent from serialized results and receipts.

## Controls that held

- Commit enumeration is bounded, strict-ASCII, exact-SHA based, includes every parent edge, deduplicates overlapping selected ranges, and binds per-range digests plus an aggregate chain digest (`verification.py:1342-1443`).
- Raw diff parsing is NUL-delimited, bounded, rejects malformed paths, and renders non-printable path bytes without emitting blob bodies (`verification.py:1316-1330`, `1460-1514`). Byte-oriented secret matching and bounded batch object reads are directionally sound for the regular blobs actually selected.
- The exact base-to-candidate path list contains no `trust-ci/**` change, so this delivery does not fold in the separate #219 Trust CI work.
- Local verifier results, grants, receipts, and this report remain workflow evidence only. They do not create merge authority; release still requires the external GitHub App-owned `adaptive-trust-ci/verified@<policy-sha12>` check for the exact pull-request head and any separately required signed approvals.

## Required disposition

Do not treat `cdad4de5cd9620a97d3919bc47c89ff923839623` as security-approved. Fix all four Important findings, add focused bypass regressions, rerun the full verifier on the resulting exact SHA, and obtain a fresh independent security review and external Trust CI decision.

---

## Bounded security re-review — repaired candidate

### Re-review binding

- Verdict: **FAIL**
- Reviewed candidate: `ddd9988e4b43fd1502796de42fdcc52170233c61`
- Reviewed base and candidate parent: `cb9af4073ba6c3d515145164d771c75ebdfa3224`
- Candidate tree: `9a1dab623ee74f9f1d65e56ed5e6564c94ca5310`
- Route: `566746aef130`
- Reviewed-tree-modified: **no**
- Critical findings: **0**
- Important findings: **1**
- Minor findings: **0**

This re-review was bounded to the four findings above and their regression coverage. The exact candidate remains a single-parent squash directly on the stated base. The coordinator-provided exact-head full verifier result is PASS for both the core and database phases. I independently ran the eight new bypass-focused selectors covering ambient Git controls, symlink/gitlink/special-file behavior, named-file replacement, diff-output confidentiality, scanless receipt forgery, and coverage-field mutation; all passed in 3.187 seconds. A separate focused hostile-configuration probe exposed the remaining I-1 bypass below.

### Prior-finding disposition

1. **I-1 remains Important — root binding is fixed, but whitespace policy still trusts hostile repository configuration.** `run_git_bytes` now gives every scan-boundary Git invocation a strict root-resolved command and a minimal environment that excludes inherited repository selectors and inline configuration, disables system/global configuration and replacement objects, and disables several external behaviors (`util.py:19-59`, `164-185`). Ref resolution, target selection, ancestry, merge-base, enumeration, object reads, and whitespace checks correctly share that seam (`verification.py:582-606`, `621-790`, `1382-1393`, `1488-1500`, `1744-1778`); set/empty selectors, inherited `GIT_CONFIG_*`, replacement refs, and branch/tag tests pass (`tests/test_verification_doctor.py:1332-1383`). However, Git still reads repository-local `core.whitespace`, and `core.attributesFile=/dev/null` does not disable tracked `.gitattributes`. Both inputs can disable whitespace classification for the exact `git diff --check` commands used by the verifier. In independent disposable-repository probes, a commit containing `credential_value` followed by two trailing spaces produced exit 0 and zero diagnostic bytes under each of:

   - local config `core.whitespace=-trailing-space,-space-before-tab`; and
   - tracked attribute `*.txt -whitespace`.

   The verifier can therefore report complete whitespace coverage while a selected parent edge contains prohibited trailing whitespace, violating AC-004 and AC-008. Make whitespace classification independent of local config and tracked attributes (for example, inspect the bounded raw patch bytes with a deterministic internal rule rather than relying on configurable `git diff --check` classification), and add regressions for both bypasses.

2. **I-2 resolved — exact coverage recomputation.** Complete-scope validation now rebuilds the full chain scan, rejects scan failures or secret findings, reruns the dirty-file scan, requires it to pass, and compares the stored scope to the entire recomputed scope (`verification.py:1672-1700`). The prior zero-counter forgery and mutations of every coverage/completion field are rejected (`tests/test_change_receipts.py:961-1027`). The receipt path still invokes this validation before accepting a verification PASS.

3. **I-3 resolved — explicit mode policy and stable no-follow worktree reads.** Committed regular-file and symlink blobs are scanned, while any other non-deletion mode, including gitlinks, makes coverage incomplete (`verification.py:1532-1542`). Dirty files are opened component-by-component relative to directory descriptors with `O_NOFOLLOW`; regular-file type, size, file identity, named-path identity, parent-directory identity, and pre/post state are checked, and unsupported platforms/types, symlinks, missing paths, special files, oversize objects, or replacement races fail closed (`verification.py:1824-1946`). Tests exercise symlink blob detection, gitlink rejection, live and broken symlinks, FIFO rejection, and named-file replacement (`tests/test_verification_doctor.py:1385-1491`).

4. **I-4 resolved — no raw diff diagnostic retention.** Endpoint and parent-edge whitespace checks retain neither stdout nor stderr. On failure they extract only the first diagnostic's bounded, escaped path and emit fixed metadata-only messages (`verification.py:1742-1821`). The regression places a representative credential value on a trailing-whitespace line and proves the serialized result omits it (`tests/test_verification_doctor.py:1493-1503`).

### Residual boundary and verdict

One Important security finding remains within the requested re-review scope; there are no Critical or Minor findings. The exact base-to-candidate path set still contains no `trust-ci/**` change, so issue #219 remains separate. Fail-closed behavior on platforms without the required descriptor-relative/no-follow primitives is intentional availability degradation, not a coverage bypass.

Do not treat `ddd9988e4b43fd1502796de42fdcc52170233c61` as security-approved. This FAIL is local, fingerprint-bound workflow evidence only. It does not authorize merge, publication, or any external action and does not substitute for the GitHub App-owned `adaptive-trust-ci/verified@<policy-sha12>` result on the eventual exact PR head or for any separately required signed approval.

## Historical final-review appendix — `de23e5da`

- Binding: base `cb9af4073ba6c3d515145164d771c75ebdfa3224`, reviewed HEAD `de23e5dac4cfe9fc8d832078ec867ae05e096db1`, reviewed-tree-modified **no**, verdict **FAIL**.
- Important I-1: the attribute-independent scanner called unbudgeted quadratic `SequenceMatcher(..., autojunk=False)`. An 8,000-line/16 KiB repetitive input took 12.732s after the 500/1,000/2,000/4,000-line series measured 0.039s/0.169s/0.705s/2.922s; the 2 MiB object and 512 MiB aggregate byte limits therefore did not provide a CPU bound.
- Closure required deterministic internal and aggregate work limits, typed fail-closed incomplete evidence on exhaustion, and no regression in metadata-only reporting or hostile repository isolation.

## Historical final-review appendix — `f2789117`

- Binding: base `cb9af4073ba6c3d515145164d771c75ebdfa3224`, reviewed HEAD `f278911796e843089cff33e2f8e59a963e79ffd8`, tree `5f3275e0eb81e82a68dd8419d18bd8b7b65fae70`, reviewed-tree-modified **no**, verdict **PASS** with no findings.
- The security review accepted the explicit shared operation ceiling, typed metadata-only incomplete failures, hostile repository isolation, and moved/duplicate detection. This historical PASS does not supersede the separate code/test/release findings or authorize closure.
