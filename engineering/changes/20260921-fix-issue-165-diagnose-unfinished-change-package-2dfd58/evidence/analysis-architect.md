# Architecture analysis — issue #165

Route: `2dfd5804553e`. Change: `20260921-fix-issue-165-diagnose-unfinished-change-package-2dfd58`.
Repository: `/home/pall/grok-projects/adaptive-grok-build-issue-165`.
Inspected HEAD: `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`; branch: `fix/issue-165-interruption-status`.
This is source analysis, not implementation, test, review-receipt, or merge evidence. No tests, compilation, Docker operations, commits, or product edits were performed by this lane.

## Recommendation

Add one bounded package inspector and one bounded Git snapshot collector. Keep package completeness, accounting for intended evidence, receipt validity, and Git observations as distinct outputs. Feed the inspector the selected active package and an already-collected snapshot; do not let it discover other worktrees, invoke verification, or publish anything.

Adopt the supplied interruption-handoff packet with two explicit refinements: a valid draft has expected incompleteness rather than corruption, and a stacked branch needs a separately named package-start baseline to expose work that has no task commit. Neither finding proves that an agent crashed.

## Facts from the inspected implementation

| Source | Finding and consequence |
| --- | --- |
| `scripts/grok_status.py:17` | Status currently returns route, active-change pointer, agent state, and `validate_evidence()` gaps. It has no content-completeness or Git-work observation. Preserve these keys and their meanings. |
| `.grok-stack/adaptive_grok/change.py:33` | `start_change()` creates the durable package and a draft history event; a repeated start returns existing state. This is the right place for a first, immutable task-start observation. Do not replace that observation on resumed starts. |
| `.grok-stack/adaptive_grok/change.py:89` | All stage transitions are centralized and append history before an atomic state-file write. Add the first implementation checkpoint here instead of introducing a separate daemon or transition system. |
| `.grok-stack/adaptive_grok/spec.py:803` | Generated v2 specs intentionally have `UNKNOWN` objective metrics/targets and empty criteria. Those are legitimate draft defaults. |
| `.grok-stack/adaptive_grok/spec.py:684` | Gate validation already rejects unknown objectives, empty acceptance criteria, and unresolved red-risk obligations. Reuse these typed concepts for diagnostics; do not replace spec validation or enlarge its authority. |
| `.grok-stack/adaptive_grok/spec.py:459` | The spec reader bounds bytes and rejects a final symlink, but its ordinary pathname open alone does not protect symlinked ancestor directories. A new package scanner needs ancestor confinement as well. |
| `.grok-stack/adaptive_grok/receipts.py:570` | Current receipt reads already use descriptor-relative, no-follow opens through all components. This is a local example for a safe bounded package reader. Receipt reads themselves do not create receipt directories. |
| `.grok-stack/adaptive_grok/state.py:93` and `:309` | Existing read getters call `runtime_dir()`, which creates `.grok-stack/runtime`. A fresh-clone nonmutation test must include absent runtime state; merely leaving an existing tree's file bytes unchanged misses this effect. |
| `.grok-stack/adaptive_grok/util.py:119` | `git_default_base()` eventually falls back to `HEAD`. Reusing that fallback would manufacture zero-ahead findings when the true baseline is unavailable. |
| `.grok-stack/adaptive_grok/util.py:145` | `changed_files()` includes committed changes when given a base and recursively scans the tree without a Git HEAD. It is unsuitable as the new cheap working-tree snapshot primitive. |
| `.grok/hooks/stop_gate.py:20` | Stop is deliberately soft and marks a route complete after current receipt checks pass. Add package warnings before that completion path without turning Stop into a blocking hook. |
| `scripts/grok_review.py` | Review recording currently checks that the report exists and delegates receipt creation. Any new preflight belongs before receipt creation and must preserve the existing receipt format. |

The inspected package was still `draft` and the only untracked path was this change package. Its route base is `90078959ff816068af374ad42f4bb80fdbaec866`, while its actual start HEAD is the different SHA above. Inherited branch commits must not be counted as proof that this task's work has been committed.

## Additive diagnostic contract

Keep the four current top-level status keys. Add `package_completeness` and `worktree` objects, with an observation timestamp. Stable finding codes, package-relative locations, and short messages let both humans and hooks use the result without parsing English paragraphs. Optional additive fields do not require a receipt or external Trust CI schema change.

`package_completeness` should expose the package stage separately from an inspection classification, for example `draft`, `complete`, `incomplete`, or `unknown`. Findings should distinguish expected draft omissions from invalid structure, unavailable input, and missing information at a stage where it is required. A missing package pointer is a named unavailable state; it is not an invitation to scan all packages. A malformed or unreadable draft remains malformed or unreadable, even though a well-formed draft is allowed to have no acceptance criteria yet.

At `scoped`, `approved`, `implementing`, `verifying`, `reviewing`, or `ready`, require a resolved objective and nonempty typed acceptance criteria. At `blocked`, use its recorded history to understand whether implementation has begun; do not erase prior obligations by moving to a blocked state. Terminal historical packages should not be selected or revalidated merely because they exist nearby.

Return explicit known template remnants only: the generated acceptance-criterion scaffold, unexpanded generated template fields, and a standalone current `<!--RUNTABLE-->` obligation marker. Do not reject arbitrary `TODO` or `TBD` prose, unchecked task boxes, examples, fenced code, quoted historical failures, or old run transcripts. Markdown is explanatory; typed criteria remain authoritative. The current mandatory section must be identified precisely rather than inferred from every occurrence of the word “mandatory.”

For evidence accounting, prefer small typed local metadata for each declared obligation: stable ID/kind, `not_run` with a nonempty reason, or `recorded` with a relative run/report reference. Render the accounting into the evidence README for a human reader. Derive initial receipt-kind obligations from the route's closed `required_evidence` list; additional run obligations must be explicitly declared. Do not invent obligations by crawling prose. Existing packages without the new metadata remain readable and can receive an explicit legacy-accounting diagnostic without automatic migration.

An explicit `not_run` explains the current state; it never proves that a run passed and never satisfies `validate_evidence()`. A `recorded` reference shows that evidence was recorded; it likewise does not establish a fresh passing receipt. Review preflight must not require the very receipt it is about to create or a later review kind that has not yet run. Failed reviews remain recordable even while package accounting is incomplete. The authoritative current receipt validator and external Trust CI stay unchanged.

## Bounds and read safety

Resolve only the selected package under `engineering/changes/<change-id>` and reject traversal, absolute external targets, and symlinked ancestors. Use descriptor-relative no-follow opens and regular-file checks; reject FIFOs, devices, inaccessible files, concurrent replacements, and invalid encodings with typed diagnostics rather than hangs or empty success results. Parse bytes already obtained safely instead of reopening a checked path through an unsafe pathname.

Inspect a fixed set of package files plus explicitly declared current evidence references. If compatibility requires looking for a legacy marker in evidence Markdown, cap traversal depth, file count, per-file bytes, aggregate bytes, and findings; never follow links. Suggested conservative initial limits are 64 candidate Markdown files, three evidence-directory levels, 256 KiB per Markdown file, and 1 MiB aggregate text, with the existing spec byte/depth/node limits retained. Exceeding any limit yields an incomplete inspection diagnostic, never a silently complete package. Do not read arbitrary logs, attachments, credential names, hidden scratch, or secret files.

The pure inspector must not call `validate_evidence()`: that function can compute fingerprints and architecture/governance bindings, and is a separate existing status concern. Avoid broad `rglob()` fallback, full product hashing, and receipt creation in the new path. Preserve the meaning of the existing `evidence_gaps` field while making the new inspection independently cheap and testable. The integration analysis also identified Python import bytecode as a mutation source: set `sys.dont_write_bytecode` before adaptive imports in the status entrypoint, and include ignored cache paths in the nonmutation fixture.

## Worktree observation and stacked branches

Collect current branch, exact HEAD, route base, initial checkpoint HEAD when present, selected diagnostic base, base source, commits ahead, and dirty product paths. Use bounded, timeout-limited Git commands with NUL-delimited path output, no shell interpolation, and optional locks disabled. Do not refresh remotes as a side effect of status.

Prefer the immutable package-start checkpoint HEAD for the task-local count when it exists and is valid; name its source `initial_checkpoint`. Retain the route base and, if reported, its separate ahead count. For an older package with no checkpoint, use an available validated route base with source `route_base`. Never substitute current HEAD for a missing or unreadable baseline. Missing Git, unborn HEAD, unavailable objects, failed commands, or an incomplete snapshot produce null/unknown values with a reason. A broken recorded checkpoint should be visible rather than silently replaced.

Report `uncommitted_product_zero_ahead` only when both the dirty-product observation and the selected-baseline count are known. Describe it as an interrupted-work candidate or work needing a checkpoint, not an orphan proved dead. The message must identify whether zero is relative to package start or route base. Include staged, unstaged, deleted, renamed, and relevant untracked product paths. Package evidence and runtime noise alone must not produce a product-work warning; do not exclude all Markdown indiscriminately because skills, rules, and templates can be product files.

The snapshot is an observation at a named time, not a content fingerprint or atomic proof across arbitrary concurrent edits. It must not alter route base, receipts, grants, branch state, or eligibility for external merge.

## Durable checkpoints through existing transitions

At creation, record change ID, route ID, branch, actual HEAD, time, and `draft; implementation not started` in the evidence README and small additive local state metadata. If Git is unavailable, record unknowns explicitly. A repeated `start` preserves the first checkpoint.

On the first successful transition to `implementing`, record a WIP observation with dirty-product state and paths, without committing or pushing. The state history can carry this observation in the same atomic write as the stage transition; the README is its human-facing append-only presentation. Preserve previous entries on resume. Document any two-file partial-write handling rather than promising crash-atomic publication. Failure to write the README must not erase the canonical checkpoint or masquerade as a successful durable mirror.

This improves continuation in the same worktree and makes committed checkpoints useful elsewhere. It cannot make an uncommitted tree visible from a fresh clone. Cross-host recovery still depends on explicitly authorized commit/publication; this change supplies neither automatic publication nor crash immunity.

## Acceptance criteria for the write owner

1. A freshly created valid package reports `draft`, identifies expected unresolved fields, and does not claim corruption or passing evidence.
2. The same unresolved objective/criteria at an implementation stage produces typed incompleteness before full verification runs.
3. Missing, malformed, inaccessible, symlinked, oversized, or otherwise unsafe selected inputs produce precise diagnostics without reading outside the package or hanging.
4. Current explicit unexpanded markers are detected; quoted/fenced historical markers and arbitrary TODO/TBD prose do not fail completeness.
5. A declared mandatory obligation lacking either a real recorded reference or `not_run` with a reason is visible. `not_run` remains unable to satisfy a passing receipt.
6. A Git fixture at zero task commits with dirty product files reports a candidate. An inherited-commit stacked fixture proves the distinction between route base and package-start base.
7. Missing Git/base/HEAD and failed or truncated status queries produce unknown, never zero or clean success.
8. Package-only paperwork and ignored runtime noise do not produce the product-work candidate. Staged, untracked, deletion, and rename cases remain observable.
9. Repeated status/inspector calls leave contents, metadata relevant to the asserted guarantee, Git index, package state, and absent runtime directories unchanged.
10. Start records the first checkpoint; first implementation transition appends WIP; repeated start/resume preserves prior observations and the original baseline.
11. Stop remains non-blocking and surfaces relevant package/work warnings. Review diagnostics appear before receipt creation, preserve fail/pass receipt shape, keep failed reviews recordable, and avoid circular review prerequisites.
12. Existing status keys, receipt validation, delegated grants, exact-head external Trust CI, and PR-only delivery retain their current meanings.

## Minimal file surface and delivery order

- One focused package-inspection module under `.grok-stack/adaptive_grok/`, plus the minimum safe read-only getter/helper adjustment needed by the existing status output.
- `scripts/grok_status.py` for additive output, `.grok/hooks/stop_gate.py` for soft warnings, and `scripts/grok_review.py` for pre-recording diagnostics.
- `.grok-stack/adaptive_grok/change.py` and the existing change evidence README/state templates for initial metadata and transition checkpoints. Keep receipt/Trust CI schemas unchanged.
- Focused fixtures in existing change/hook suites or one dedicated package-status suite; use existing spec tests for typed semantics rather than reproducing the open PR141/PR134 work.
- Relevant README/CLI documentation and the active change package. Finish checkpoint and delivery documentation before the controller's full verification/review receipt wave, since later repository edits stale local evidence.

## Risks, rollout, rollback, and shared-memory facts

Main risks are false positives from historical prose, false zero-ahead claims from a fabricated baseline, accidental mutation by read helpers, and unsafe or unbounded evidence traversal. The typed-stage split, explicit source-labelled baseline, bounded descriptor-safe reads, and missing-runtime regression fixture address those risks directly. Full existing status can remain costlier than the new inspector because receipt bindings are preserved; do not claim to have optimized all receipt verification.

Roll out as additive CLI diagnostics and additive checkpoint metadata for newly started or explicitly transitioned packages. Do not rewrite the archive of existing change packages. Rollback is a source revert of the diagnostic wiring/templates; existing appended observations remain historical text/local metadata and must not be deleted. No database migration, deployed policy change, trust-store change, or external approval format is involved.

For the controller to record in shared memory after validation: (1) preserve authority baselines separately from task-start diagnostic baselines on stacked branches; (2) distinguish accounted-for `not_run` from successful execution evidence; (3) prove nonmutation from a repository whose runtime directory is absent. These are design recommendations pending implementation evidence, not already-proven successful decisions.
