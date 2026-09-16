PASS

Independent security review of commit `8d45b31` (`docs(release): record the published v2.0.17 release identity (SR)`)
against base `c86b1a1989ace899a4450bde558fcd8adc00e4e2`, route `7c56479f61d3`, receipt kind `security_review`.
Method: read-only inspection of the commit, the tracked blobs and `engineering/changes/20260916-docs-release-record-the-published-v2-0-17-identi-7c5647/evidence/command-evidence.txt`
(quoted below as "evidence"), plus two independent live `gh` reads and local digest recomputation. No file was written except this report.

## Critical

None.

## Important

None.

## Minor

1. **Minor — stale "observed main" prose left one merge behind the record it just advanced.**
   `START_HERE.md:7` still reads "Repository `main` was observed at `78082a290f8b90cade88685351fbb2ba263689b9` (PR #98)" and
   `GROK_BUILD_HANDOFF.md:304` still reads "`main` was observed at `78082a29…`; the artifact child rides its own branch on that base",
   while this same commit sets `PROJECT_STATE.json:6` `observed_main_sha` to `c86b1a1989ace899a4450bde558fcd8adc00e4e2` (the child's
   merge, no longer "its own branch"). Verified unchanged: both lines appear only as diff context. This *understates* the delivered
   state (it does not claim an install/activation, so FORBID-001 is not breached) and START_HERE hedges with "fetch refs before
   assuming it is still the tip". Recommend a one-line follow-up in the successor paperwork.
2. **Minor — the archived v2.0.16 block was spliced in with the file's non-standard indentation.**
   `PROJECT_STATE.json:68-96` uses 2-space key indentation while every other object in the file uses 4-space, i.e. the block was
   inserted textually rather than re-serialized. Cosmetic only: the file parses (`json.load` OK) and the identity values were
   verified field-by-field equal to the base record (see "Checks performed" §3).
3. **Minor — evidence-capture defect in the supplied raw evidence.**
   Evidence section "blob digests from HEAD" contains two `cut: invalid decreasing range` / `Try 'cut --help' for more information.`
   errors before each digest line, so the pipeline that produced that section is partly broken. The surviving `sha256sum` output is
   well-formed and I independently recomputed both digests (see "Checks performed" §2), so no information was lost; the collection command should be fixed.
4. **Minor — the successor's own exact-head gate is not yet observable.**
   Evidence section "gh pr list --state open" returns only `33`; I confirmed live that PR #33 is unrelated
   (`perf/parallel-python-tests`). So `SIG-001`'s "exact-head `adaptive-trust-ci/verified@06ecf1c875bc` on this successor pull request"
   cannot exist at evidence time (2026-09-16T02:02:32Z) and no local receipt substitutes for it. Recorded as a status fact, not a defect
   of the diff: per `AGENTS.md`, merge authority remains the App-owned check on the exact head SHA.

## Limitations (not findings)

- The review is **diff-content based**. Per the repository contract I did not open `.env`, private keys, credential stores or any
  approval material, and did not read the 10.9 MB artifact bytes beyond their SHA-256. Machine-local values were therefore judged by
  comparison against the previously tracked dossier, not by inspecting the host.
- Deployed Trust CI policy, the holdout bundle, the App signing key and branch protection live outside the pull-request trust domain
  and are not verifiable from this tree. `check_run_id`, `attestation_id`, `signer` and `github_app_id: 4694114` were checked for
  agreement with the evidence file's check-run summary, not re-derived cryptographically.
- The claim "built twice byte-identically" and the installed-unit PIDs inside the new dossier are carried forward verbatim from the
  already-published post-98 dossier; I did not re-observe the runtime host and make no independent claim about it.

## Checks performed and what they proved

**1. No over-claim (FORBID-001) — PASS.** Every added line containing `install|restart|deploy|host(ing)?|cohort|activat|M8|M9|provision|
systemctl|operational_activation` was read (39 added lines). Each is either a negation or a scope statement, e.g.
`PROJECT_STATE.json:65` notes "…establishes no operational landing provider or host, M8 cohort/activation, or real M9 deployment";
`PROJECT_STATE.json:614` `local_candidate.notes` "…no provider installation, host mutation, hosting or deployment occurred";
`PROJECT_STATE.json:681` `repository_delivery.operational_activation: false`; the change-package `release.md` "## Deployment" line
"Documentation only — no service restart, installation, provider activation or host mutation";
`evidence/runtime-observation-post-99.json:78` "the installed units still run `5f6f6ce1…` (primary) and `61a05da2…` (secondary);
nothing was installed, restarted or activated". `active_delivery.current_unreleased_change.next_action` and
`active_delivery.next_action` put M8 cohort and M9 qualification explicitly in the *future* ("then assess…").
`grep '"operational_activation": true'` matches exactly one line in the whole tree, `PROJECT_STATE.json:1432`, inside the pre-existing
`l5_production_preparation` M-stack record; base has the identical line at `8d45b31^:PROJECT_STATE.json:1401` (unchanged, unrelated to
this release). `external_effect` flipped `false→true` (`PROJECT_STATE.json:216`, `:611`) is accurate and scoped by
`external_effect_scope: "github_repository_delivery_and_release_only"` written at `:612` (the identical string already existed at `:411`
for the archived v2.0.16 record, unchanged — so this is the established scope, not a new claim) — the GitHub Release is a real, verifiable
external effect; it does not read as operational activation. Tests only tighten: `tests/test_project_state.py` adds
`assertFalse(state["local_candidate"]["operational_activation"])`.

**2. Record agrees with the remote — PASS, all 14 identifiers matched, none fabricated.** Against evidence sections
"git ls-remote peeled tag", "gh release view v2.0.17", "check runs on A head bbc5cdd9…" and "check-run 104621989321 output summary":
tag `v2.0.17` / tag_object `5c6687ed97e1c365597bf27047016eb07411f28b` (I confirmed `git cat-file -t` = `tag`, i.e. annotated, not a
peeled sha) peeling to `c86b1a19…` = recorded `merge_commit`; `published_at 2026-09-16T01:17:14Z` = `publishedAt`;
`pull_request 99` — independently re-read live: `gh pr view 99` = `state MERGED`, `baseRefName main`, `headRefOid
bbc5cdd9b8ee4dbc6927bf24244a5434f490576d` = recorded `checked_head`, `mergeCommit c86b1a1989ace899a4450bde558fcd8adc00e4e2`,
`mergedAt 2026-09-16T01:14:19Z` = recorded `merged_at` (`PROJECT_STATE.json:42`); App check `adaptive-trust-ci/verified@06ecf1c875bc`
`check_run_id 104621989321` `conclusion success` on that head; `attestation_id b9510589-d40c-4976-aafd-cad6fc141972` (`:56`) and
`signer 0519cf1d47436f2e` (`:57`) = the summary line; GitGuardian `conclusion SUCCESS` with new `check_run_id 104621982710` (`:62`) = evidence.
Tree `5826924586f9d42b02bf9fd5d51985bd323da31e` = `git rev-parse c86b1a1^{tree}` **and** `= git rev-parse bbc5cdd9^{tree}` (so both the
`published_release.tree` and the `local_candidate.artifact_child.tree`/`active_delivery` copies are the same true value, no copy-paste
fudge), and `2283e6a09d3eb2a0aeabce8a872e06746b941176` = `git rev-parse 78082a29^{tree}` = recorded `source_parent_tree`.
Digests: `SHA-256(git cat-file -p HEAD:packages/adaptive-grok-build-pro-v2.0.17.zip)` recomputed here =
`770f1db5725e666be60c1f879d2768feacb15dd53e194a1f1f48632980f74616`, matching the tracked-blob line in the evidence and GitHub's own
asset `digest` for that name; sidecar `54db9f64bb7296ca657410131499ca06358f89b23171e221b04e300acf03f3c0` likewise matches GitHub's asset
digest, the evidence blob digest and `published_release.artifact.sidecar_sha256`. Sizes agree too: GitHub reports 10940676 / 102, tracked
blobs are 10940676 / 102 bytes.
Sidecar layout verified from `od -c` (evidence "sidecar bytes") **and** re-read from the blob: `64 hex` + exactly **two** spaces +
`adaptive-grok-build-pro-v2.0.17.zip` + single `\n`, no CR, 0146₈ = 102 bytes total — byte-for-byte the v2.0.16 sidecar convention
(`od -c` of `packages/adaptive-grok-build-pro-v2.0.16.zip.sha256` shows the same layout, 102 bytes).

**3. Immutability (FORBID-002 / INV-001) — PASS.** A deep key-by-key comparison of `git show 8d45b31^:PROJECT_STATE.json` vs
`git show 8d45b31:PROJECT_STATE.json` reports changed top-level keys only: `active_delivery`, `current_unreleased_change`,
`latest_published_release`, `local_candidate`, `observed_at`, `observed_main_sha`, `prior_published_releases`, `published_release`,
`runtime_observations`. The v2.0.16 record was **prepended to `prior_published_releases`** (3 → 4 entries; tags now
`v2.0.16, v2.0.15, v2.0.14, v2.0.13`) and is equal to the base `published_release` in **every** field except `notes`
(programmatic assert returned True): tag, `published_at 2026-09-13T22:04:08Z`, `pull_request 79`, `checked_head 2b151798…`,
`merge_commit 969c4f65…`, `merged_at`, `tag_object 8486ddb6…`, `tree 2c24c338…`, artifact path + both digests, `trust_ci`
name/conclusion/`check_run_id 103797448701`/`attestation_id 90cb34aa…`/signer/`github_app_id`, `gitguardian` conclusion and its
original note text. The `notes` rewrite to "Historical: superseded as the current published release by v2.0.17." follows the exact
precedent already published on `main` for v2.0.15 (`PROJECT_STATE.json:127`), and carries no identity value. The three older prior
entries are byte-identical (`base priors preserved verbatim: True`). `milestones` equal, `schedule` equal,
`active_delivery.integrated_stack` equal (historical v2.0.13-era M4-M9 heads preserved), frozen PostgreSQL migration range
`001-018` occurs 3× in base and 3× in head, unchanged. Under `packages/` only `packages/README.md` changed
(`git diff --name-only` = that single path; one row, one line: "artifact delivered, tag and GitHub Release pending" →
"published 2026-09-16T01:17:14Z"); all 34 other `packages/` blobs, including both v2.0.17 artifacts, have identical blob ids in
`8d45b31^` and `8d45b31` (`fffe4ec3…` / `35ddd9f8…`), and no binary hunks appear in the diff.

**4. Leaks — PASS.** The added lines were scanned for `BEGIN *PRIVATE KEY`, `BEGIN OPENSSH`, `ssh-rsa`, `password|passwd|secret`,
`token`, `api[_-]?key`, `Bearer `, `AKIA[0-9A-Z]{16}`, `ghp_`, `github_pat_`, `.env`, e-mail-shaped addresses and `/home/<user>`
paths: **zero credential matches**. All hits were commit/tag SHA-256 identifiers, published artifact digests, the
`https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.17` repository URL (already the documented remote on `main`) and
the account name that is the repository owner recorded throughout the pre-existing state file. The new dossier was compared key-by-key
with `engineering/changes/20260916-build-release-deliver-deterministic-v2-0-17-zip-31155d/evidence/runtime-observation-post-98.json`:
**exactly six** differences, all legitimate and none adding a new machine-local value — `previous_dossier` pointer (source trail), the
unit `note` wording, `observed_at` 00:23:18Z → 01:33:14Z (observation timestamp), `source_base` `78082a29…` → `c86b1a19…`,
`artifact_state` provenance wording, and the merged-PR list `98` → `98, 99`. Everything else — `checked_pr_head_sha 4e94f7a9…`,
`grok_config_sha256 450657a9…`, `merged_commit 61a05da2…`, `merged_and_installed_sha 5f6f6ce1…`, the historical `2026-09-14T03:31:08+00:00`
sub-observation and the `status: runtime_deployed_and_live_artifact_acceptance_passed` acceptance record — is copied verbatim from the
already-published dossier, explicitly marked as carried history at `evidence/runtime-observation-post-99.json:37`
("…no reinstall, restart or provider activation happened… their digests must not be restated as new evidence"). No secret, key or
`.env`-derived value exists in either dossier.

**5. Scope — PASS.** The full changed-file list (evidence "diff name-only c86b1a1..HEAD", 25 files, cross-checked against
`git diff --stat`) contains no service/product module, no `scripts/` path and no `trust-ci/` path: 6 root docs
(`README.md`, `START_HERE.md`, `CHANGELOG.md`, `DARK_FACTORY_ROADMAP.md`, `GROK_BUILD_HANDOFF.md`, `mistakes.md`), `PROJECT_STATE.json`,
`packages/README.md`, 3 lockstep test files (`tests/test_structure.py`, `tests/test_project_state.py`,
`tests/test_manifest_package.py`), 2 prior change-package `tasks.md`, and 12 files in this change's own package. Test edits are
literal advances plus *added* assertions (v2.0.16 identity checks migrated to the archived entry, prior count 3 → 4, new
`assertFalse(...operational_activation)`), with no assertion deleted that guarded activation or identity — INV-002 holds.
The v2.0.17 artifact bytes do not appear anywhere in the diff.
