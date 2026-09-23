# Integration architecture — v2.0.19 factory bugfix release

Route: `4317e673390b`
Role: `integration_architect` (read-only analysis)
Observed base after `git fetch --all --prune`: `origin/main` = `130ce4a42d9f9bbd1b56772d40b19ae530283205`
Release worktree/branch: `/tmp/agbp-release-factory-bugfixes`, `release/v2.0.19-factory-bugfixes`

## Recommendation

Build one PR from the fetched `origin/main` base as a linear, auditable stack of the accepted issue commits, followed by a release-metadata commit only after the fix tree has passed focused and full local verification. Keep each retained issue's production change, regression tests, and issue-specific durable evidence in the same issue commit. Route #48 separately because `FIT-TRUST-CI-SEPARATION` forbids mixing its `trust-ci/**` paths with implementation changes. Do not squash the retained fixes locally and do not mix issue files between commits; GitHub may eventually create one protected-branch squash merge, but the candidate branch and PR must retain the review boundaries.

Do **not** base this work on, merge, or wholesale cherry-pick `release/v2.0.19-candidate-20260922`. Its current range from `origin/main` is an unrelated 11-commit/56-path release chain containing the earlier `b26dff` batch, M8/runtime and policy documentation, Trust CI example changes, and pre-existing v2.0.19 metadata. That violates this route's exclusion of unrelated M8/DEV work and would make the six issue fixes impossible to attribute.

At analysis time all six selected issue branches still resolve to the common base SHA and their changes are not committed into refs. Therefore no candidate SHA, path list, or prior green result exists yet that can safely be promoted. The write owner must treat each incoming slice as provisional until it has a commit SHA, exact path inventory, test inventory, and result bound to that SHA/tree; the #48 slice must additionally pass as a separate Trust CI-only change.

## Candidate composition

Use one integration manifest (for example `evidence/candidate-manifest.json`) as the release ledger. It should list base SHA, final SHA, tree fingerprint, and one record per issue containing source branch, adopted commit SHA, parent SHA, changed production paths, regression-test paths, issue evidence paths, focused commands/results, and whether integration changed the slice. Reject duplicate paths not explicitly adjudicated.

Recommended linear order:

1. **#35 — shell syntax discovery/checking.** Keep discovery and syntax-test coverage together. Its contract must prove every applicable discovered shell target is checked and an empty or partially checked set cannot pass.
2. **#36 — command recorder exit status.** Keep recorder behavior and failure-status regression together. It must preserve the original command's non-zero/exec-failure status rather than the status of negation, logging, or cleanup.
3. **#39 — lint scope.** Keep lint-scope selection and scope tests together. It must exclude non-product/generated/scratch/worktree content while refusing to report success when no required product target was actually checked.
4. **#73 — evidence digest naming/classification.** Keep schema/serializer/consumer changes and compatibility tests together. Preserve historical evidence byte-for-byte; do not globally suppress 64-hex secret detection. Any renamed forward field needs an explicit reader compatibility decision and tests for old and new records.
5. **#167 — bounded static landing verification.** Apply last because it changes verification selection. Its focused profile must only activate for the documented static-landing path set, prove its complete applicable scope, and fail toward the full PR profile on ambiguity or any extra product path. It must never weaken the full route gate or external Trust CI.

The exact order may change if the final path inventories show a dependency, but the manifest must record that dependency. A conflict resolution is not clerical: amend the affected issue commit (or add a narrowly named integration commit), rerun that issue's focused RED/GREEN proof, and mark all earlier results on the changed tree stale. Never resolve a conflict by dropping a regression test.

## Independence and evidence preservation

For each retained issue, require all of the following before adoption:

- deterministic pre-fix reproduction or a failing regression test, with the failure attributable to that issue;
- root-cause statement distinct from incidental cleanup;
- one minimal production delta and its tests in the same commit;
- focused GREEN output on that exact commit;
- `git diff --name-status <parent>..<issue-sha>` captured in the manifest;
- no release version, changelog, project-state, M8, deployment, or unrelated DEV edits;
- no claim that another issue's tests cover this issue unless the shared assertion is named and independently exercised.

After each adoption, rerun that issue's focused test on the cumulative branch. This preserves independent reviewability while detecting interactions. After all retained slices, run their focused union in one command/session and then `python3 scripts/grok_verify.py --mode pr` using the route-selected `base,contracts` profiles. The full verifier is mandatory even if #167 introduces a faster static-only profile: the release diff is not confined to `side-projects/seo-landings/**`.

Store issue-level evidence as provenance, not as current merge authority. Only verification and review performed on the final candidate fingerprint are current. Any committed evidence/report changes the fingerprint, so the coordinator's required sequence is: persist analysis/implementation/review reports, freeze the tree, run final verification, record fresh code/test review receipts as prescribed by the route, then make no repository change before external delivery. If recording a receipt itself changes tracked content, repeat the freeze/verification cycle according to the repository tooling's receipt model.

## Release metadata boundary

Use two checkpoints inside the same PR:

- **F (fix tree):** retained issue slices only; #48 has no path in this tree. Run all focused tests plus full PR verification. No `VERSION`, package archive, changelog, README, `PROJECT_STATE.json`, or release identity edits yet.
- **R (release candidate):** after F is green, add only the v2.0.19 release metadata required by current repository release tests. Update `README.md` to match the tree as required by `AGENTS.md`; update changelog/state/version/package indexes consistently. Then rerun the complete focused union, release/manifest tests, and full PR verification on R.

Do not copy metadata or attestations from the older v2.0.19 candidate. Historical `v2.0.18` records remain immutable. If this repository's package contract requires an artifact-child commit because the ZIP must describe a prior sealed source snapshot, preserve that established two-snapshot binding explicitly; do not pretend a ZIP can contain the commit that adds itself. Such a child changes the exact PR head and therefore requires fresh final verification/reviews and a fresh external check.

## API/contract impact

The route is classified `api`, although the expected fixes are verifier/tooling behavior. Freeze the affected CLI/JSON/evidence contracts before implementation:

- exit codes and status labels for checked, failed, skipped, unavailable, and not-applicable states;
- selected-path lists and reasons emitted by lint/static profiles;
- evidence digest field names and backward-read behavior;
- machine-readable verification/receipt schema consumed by installers, scripts, tests, or Trust CI.

No silent semantic change under an existing schema is acceptable. Additive fields are preferred; a rename needs dual-read or a versioned migration. No network producer/consumer, database migration, queue, or runtime deployment is implied by this release.

## Exact-SHA Trust CI gate

Local tests, issue evidence, review reports, receipts, and delegated grants are preflight evidence only. Merge authority remains the GitHub App-owned policy-epoch check currently identified by repository state as `adaptive-trust-ci/verified@06ecf1c875bc` from App ID `4694114`, on the exact up-to-date PR head SHA.

Operational sequence:

1. Push/open the single PR only under an exact delegated local grant for those operations.
2. Ensure the PR base is current protected `main`; if `main` advances, update the branch, rerun all final verification/reviews, and discard the old check as stale.
3. Wait for the App-owned check with the exact required name, App ID, final head SHA, and `SUCCESS`. A success on F, an issue branch, the older candidate, or a prior R head is irrelevant.
4. Any commit—including review evidence, metadata correction, conflict fix, package artifact, or base update—invalidates the prior exact-SHA result and external approvals and starts the final gate again.
5. Do not add GitHub Actions, alter deployed Trust CI policy/holdouts, synthesize a human approval, or treat a local grant as merge authority.

## Rollback and recovery

There is no planned data migration or production runtime mutation, so source rollback is commit-based:

- **Before merge/publication:** close or supersede the PR; no protected source or release identity changes.
- **After merge but before tag/publication:** prepare a new PR reverting the exact protected-branch merge (or the affected issue commit after dependency analysis), run the full route and obtain a new exact-SHA Trust CI success. Never push directly to `main`.
- **After immutable `v2.0.19` publication:** do not move/delete/rebuild the tag or overwrite its archive. Publish a forward-fix release (normally `v2.0.20`) from a separately verified PR and record v2.0.19 as affected/superseded.
- **Selective rollback:** only safe if the manifest proves no later slice depends on the reverted contract. Any future separate #48 change must be evaluated independently, and reverting #73's writer while retaining a new-format-only reader is unsafe.

Rollback acceptance is the same as rollout acceptance: focused regression suites for all retained slices, full `grok_verify --mode pr`, independent code/test review, and an App-owned success on the rollback PR's exact head. Because these changes intentionally close false-green paths, rollback can reintroduce unsafe success reporting; prefer a minimal forward fix when already published.

## Go/no-go decision

**NO-GO now.** The selected refs contain no adopted commits beyond base, the change specification is still a placeholder, and no final-tree verification/review/Trust CI evidence exists.

Move to **GO for PR submission** only when the retained-slice manifest is complete, every included issue retains its own reproduction/test/evidence boundary, F and R have passed as described, unrelated old-candidate/M8/DEV paths are absent, README/release metadata match the final tree, and final receipts bind to the frozen fingerprint. Move to **GO for merge** only after the exact final PR SHA has the required App-owned success and any separately required signed approval scopes.
