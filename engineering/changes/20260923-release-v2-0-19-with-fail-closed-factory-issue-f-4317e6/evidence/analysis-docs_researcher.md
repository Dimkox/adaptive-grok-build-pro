# Docs/release research — v2.0.19 issue-fix candidate

Role: `docs_researcher` (read-only analysis)
Route: `4317e673390b`
Repository/worktree: `/tmp/agbp-release-factory-bugfixes`
Observed base/HEAD: `130ce4a42d9f9bbd1b56772d40b19ae530283205`
Observed: 2026-09-23 UTC

## Executive finding

The next `v2.0.19` release must not reuse the readiness or publication claims of open PR #189. PR #189 is a separately verified release-sync candidate whose source inventory stops at `130ce4a4` and does not contain the requested fixes for issues #35, #36, #39, #48, #73 and #167. At observation time all six issues are open, each named local issue branch resolves exactly to `130ce4a4`, and each branch has an empty diff against `origin/main`.

Therefore the correct preparation order is: evaluate all six requested issues, implement and independently review only the accepted repository-owned slices, keep #48 for a separate Trust CI-only change, assemble and verify the combined bugfix tree, then update candidate release metadata; deliver that exact release-sync tree through a protected PR; and leave artifact creation, tagging and GitHub Release publication to later exact-SHA stages. Until those stages occur, `v2.0.18` remains the latest published release.

## Current release truth

- `VERSION` and `.grok-stack/adaptive_grok/__init__.py` are `2.0.18`.
- README identifies `2.0.18` as current and published; CHANGELOG starts with the published `2.0.18` entry dated 2026-09-16.
- `PROJECT_STATE.json` names `v2.0.18` as `latest_published_release` and binds its immutable artifact-child target `e7d0f72bf834b75eb543d9424ee47c7829cc65c0`, tag object, ZIP and sidecar digests.
- `packages/README.md` likewise names `v2.0.18` as latest published. It states that tracked artifact presence alone does not establish a tag or GitHub Release, production packaging requires a clean exact Git `HEAD`, and `.env`/private keys are excluded.
- The release convention is the three-stage R/A/SR chain demonstrated by `v2.0.18`: release-sync **R** establishes candidate identity and pending artifact state; artifact child **A** builds the deterministic ZIP and sidecar from merged R and is itself protected/verified; successor record **SR** records publication facts after the external actions actually occurred.
- README architecture links are currently present for `architecture/system.yaml`, `architecture/rules.yaml`, and `architecture/generated/`; the release edit must preserve them and refresh the current-state text to the actual final bugfix source.

## Open PR #189: reusable precedent, not this release's evidence

Observed GitHub state for PR #189 (`release/v2.0.19-candidate-20260922`): open, non-draft, mergeable/clean, head `1a432785d0a7e85f8a0cb829b4de555c27ce01f0`. Its exact head has successful GitGuardian and App-owned `adaptive-trust-ci/verified@06ecf1c875bc` checks. Those are historical exact-head facts for PR #189 only.

PR #189 updates identity to `2.0.19` and records fifteen post-`v2.0.18` pull requests through PR #185. Its changelog explicitly calls `2.0.19` a candidate/unpublished release; README keeps `v2.0.18` as latest published; and its package states that ZIP, sidecar, tag, GitHub Release and deployment remain pending. These wording boundaries are good precedent.

However, PR #189 is unsuitable as completion evidence for the current route because:

1. Its release input is the pre-fix source `130ce4a4` (plus earlier evidence closure), not a tree containing the six requested repairs.
2. Its local verification and review reports are bound to its own route, HEAD and fingerprints. They cannot be carried to a different base or changed tree.
3. Its successful external check authorizes only its exact head under that policy epoch; it does not attest future fix commits, a rebased PR, an artifact child, a tag or publication.
4. Merging it unchanged would consume the `2.0.19` identity before the stated six-fix scope exists. The coordinator should supersede/replace it, or update it only after rebuilding all claims and evidence against the final six-fix tree; no old receipt/check should be represented as current.

## Six-issue documentation scope

At observation time issues #35, #36, #39, #48, #73 and #167 are all open and have no closing PR references. Release notes should describe only behavior proven in the final diff/tests, not copy broad issue prose as if every example were fixed.

| Issue | Minimum truthful release-note claim after implementation | Evidence boundary |
| --- | --- | --- |
| #35 | Shell syntax gates validate every intended script and refuse an empty input set. | Regression must demonstrate a later broken operand is detected; do not claim all shell invocation classes are audited unless shown. |
| #36 | Step recording preserves the executed command's non-zero status instead of the status of `!`, with evidence that the command ran. | Include a failing command/launch failure regression and recorded status/output or duration evidence. |
| #39 | Lint scope excludes generated/out-of-band trees and exposes or bounds processed scope. | Name only the actual ignored paths/scoping behavior implemented; avoid a universal performance claim without measured final evidence. |
| #48 | Not included in this mixed implementation release; route the Trust CI smoke seam separately under `FIT-TRUST-CI-SEPARATION`. | No `trust-ci/**` change may be mixed with implementation paths; retain the #186 disposition until a separate Trust CI-only change is reviewed. |
| #73 | Committed digest naming/scan convention avoids the known GitGuardian generic 64-hex false positive without weakening real secret detection. | Confirm the chosen key migration/allow-list approach, compatibility for retained evidence, and real-secret detection tests; GitGuardian remains informational, not merge authority. |
| #167 | Static side-project-only changes use focused landing contract tests, while runtime/contracts/Trust CI/packages/workflow diffs still require full PR verification. | Preserve the exact focused-scope rule already present in AGENTS.md; do not imply reduced external merge authority. |

Each accepted issue fix should remain independently reviewable (separate commit or otherwise unambiguous per-issue diff/test mapping) even if delivered by one final release PR. Issue #48 remains separately reviewable under its Trust CI route. Issue-closing language (`Fixes #…`) belongs only on the delivery PR after the corresponding implementation is present and verified; closing an issue is not evidence that publication occurred.

## Release metadata to update only after the combined bugfix tree passes

The release-sync owner should derive, rather than pre-fill, the final source SHA, merge/check IDs and dates. Expected coupled surfaces from the established convention are:

- `VERSION` and `.grok-stack/adaptive_grok/__init__.py`;
- README H1, identity/current-state table and release-chain wording, retaining the architecture links;
- a new top CHANGELOG section marked `candidate, unpublished`, listing the accepted five-slice scope and the separate #48 disposition precisely, while preserving all `2.0.18` facts unchanged;
- `DARK_FACTORY_ROADMAP.md`, `START_HERE.md`, `GROK_BUILD_HANDOFF.md`, and `packages/README.md` where their current identity/source handoff text is coupled;
- `PROJECT_STATE.json`, with `product_version=2.0.19` but `latest_published_release`/`published_release` still `v2.0.18`, a pending byte-free `2.0.19` candidate, exact included PR/head/merge/check provenance only after those facts exist, and `operational_activation=false`;
- coupled assertions in `tests/test_structure.py`, `tests/test_project_state.py`, and `tests/test_manifest_package.py`.

Do not insert placeholder SHAs, future merge times, tag objects, artifact digests, publication timestamps, issue closure claims, deployment claims, M8 qualification, or DEV work. The current change package is still a generated draft with placeholder outcome/scope/acceptance/test/release sections; those must be made concrete before implementation transitions, but this analysis does not mutate them.

## Recommended fail-closed delivery sequence

1. Preserve `130ce4a4` as the route base and keep unrelated M8/DEV commits out of the diff.
2. For each accepted issue, establish deterministic reproduction/root cause, add the failing regression first, apply the smallest fix, and retain a clear issue-to-files/tests mapping. Route #48 separately under the Trust CI separation rule.
3. Assemble the accepted five-slice release without release identity edits. Verify focused tests and then the route-required `python3 scripts/grok_verify.py --mode pr`; obtain fresh route-selected code/test reviews on the frozen combined tree.
4. Only after step 3 passes, create the release-sync R edit in lockstep across identity, README/CHANGELOG/state and coupled tests. Re-run full verification and fresh independent reviews because metadata/report persistence changes the fingerprint.
5. Open/update the protected release PR and require the App-owned policy-epoch check on its exact current head. A changed head/base/policy/holdout invalidates the prior check. Do not describe local receipts or PR #189's check as merge authority for the new tree.
6. After R actually merges, build the ZIP and sidecar twice byte-identically from that exact merged R source in a separate artifact-child A. Track the pair only in A, verify/review A, and require A's own exact-head App check before merge.
7. Tag only A's exact merged commit and publish a GitHub Release carrying both assets, each under separately delegated named actions and any required external approvals. No deployment is implied.
8. After publication exists, use SR to record the actual tag object/target, artifact digests, release timestamp and check provenance. Before then, all publication fields remain null/pending and README/CHANGELOG must continue to say candidate/unpublished.

## Go/no-go wording

**Current verdict: NO-GO for a v2.0.19 release or publication claim.** No six-fix implementation is present in the observed issue branches, the six issues remain open, and PR #189 attests a different pre-fix candidate.

The tree may be called a `v2.0.19 candidate` only after the six-fix combined tree and release-sync metadata are verified together. It may be called `published v2.0.19` only after the artifact child is merged, tag and GitHub Release actually exist with the ZIP/sidecar pair, and the successor record captures those observed facts. Until then, the rollback and public truth is immutable `v2.0.18`.

## Read-only evidence commands

- `git fetch --all --prune`; observed `origin/main` and worktree HEAD at `130ce4a4`.
- `git diff --stat origin/main...<issue-branch>` for all six named issue branches; each produced no diff and each branch resolved to `130ce4a4`.
- `gh issue view 35|36|39|48|73|167 --json ...`; each was `OPEN` with no closing PR reference.
- `gh pr view 189 --json ...` and read-only fetch of `refs/pull/189/head`; observed exact head/check/file claims above.
- Read `README.md`, `VERSION`, `CHANGELOG.md`, `PROJECT_STATE.json`, `packages/README.md`, prior v2.0.18 R/SR packages, release scripts/tests, and PR #189's release package/diff.

No product file, issue, pull request, tag, release, deployment or approval state was changed by this analysis.
