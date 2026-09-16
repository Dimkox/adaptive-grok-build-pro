PASS

# Security review — v2.0.18 release sync (stage R), change 20260916-release-sync-2-0-17-to-2-0-18-identity-bump-r-wi-968b3c

Reviewer: route-selected `security_reviewer` (read-only). Reviewed the actual diff
`git diff d146ca455d615683765b443b747f55aa4dbad436..ee2cb850e05e4ccaa4bb7912340aa6401fbc67c5`
(24 files, +728/−157) in worktree `/home/pall/grok-projects/adaptive-grok-build-r18` on
`feature/v2.0.18-release-sync`, tree clean before and after review. Trust was placed in Git
objects, file bytes and the GitHub API, not in the author's prose.

Verdict: **PASS**. No credential, key, token, environment dump or newly-introduced host
identity enters the diff; every published-release and landing fact is verbatim- or
API-accurate; nothing is falsely claimed as published; the lockstep tests were inverted,
not weakened. Two Important findings are non-secret governance/spec-letter issues that
should be fixed (one in this wave's paperwork, one as a follow-up contract edit); neither
mints, alters or overstates trust authority.

## Scope and commands run

- `git status --short`, `git log`, `git rev-parse HEAD` (clean tree; HEAD = ee2cb850…).
- `git diff d146ca4..HEAD` (full), plus per-file diffs: `PROJECT_STATE.json`,
  `tests/test_project_state.py`, `tests/test_structure.py`, `tests/test_manifest_package.py`,
  `VERSION`, `CHANGELOG.md`, `.grok-stack/adaptive_grok/__init__.py`, README/START_HERE/
  ROADMAP/HANDOFF, `mistakes.md`, and every new file under the change package.
- Python field-level leaf diff of `runtime-observation-post-106.json` vs the predecessor
  `runtime-observation-post-99.json`; `json.dumps(..., sort_keys=True)` and default-order
  serialization comparisons of base `local_candidate`/`current_unreleased_change` vs the
  archived `v2_0_17_release_preparation` blocks; unchanged-block checks for
  `published_release`, `prior_published_releases`, `milestones`, every pre-existing
  `delivered_change_history` key and `delivered_non_milestone_work`.
- `git show d146ca4:PROJECT_STATE.json` (fetched to /tmp, base copy).
- Secret-shape scan of all added diff lines: `/home/|/root/|BEGIN (RSA|OPENSSH|EC|PRIVATE)|private[_ ]key|api[_-]?key|token|secret|passw|\.env|credential|ssh-rsa|AAAA[0-9A-Za-z/+]{20}|AKIA[0-9A-Z]{16}|ghp_|github_pat_|xox|Bearer` and separately `MainPID|698333|3597736|claw|/opt/|adaptive-l5|ActiveState|UnitFileState|localhost|127\.0\.0`.
- Landing-row re-derivation: `gh pr view 101/102/105/106 --json headRefOid,mergeCommit,mergedAt,state`
  and `gh api repos/Dimkox/adaptive-grok-build-pro/commits/<head>/check-runs` filtered to
  `adaptive-trust-ci/verified@06ecf1c875bc` (id, app id, status, conclusion).
- Publication facts: `gh api repos/.../git/ref/tags/v2.0.18` (404), `gh api repos/.../releases`
  (list), `gh api repos/.../releases/latest`, `gh api repos/.../git/tags/5c6687ed…`
  (target commit), `git tag --list`, `ls packages/`, `git ls-tree HEAD packages/`.
- Integrity of the published v2.0.17 record: `sha256sum` of the ZIP and sidecar,
  `git rev-parse bbc5cdd…^{tree}`, `78082a29…^{tree}`, `c86b1a19…^{tree}`.
- PR/branch linkage: `gh pr list --state all --head feature/v2.0.18-release-sync`, `gh pr list --state open`,
  `gh pr view 106 --json headRefName,baseRefName`.
- MainPID convention lineage: `git ls-tree -r d146ca4 … | grep runtime-observation` and
  MainPID grep of all four tracked dossiers at base.
- `python3 -m unittest tests.test_project_state tests.test_structure tests.test_manifest_package`
  → `Ran 89 tests … OK`; `git status --short` still empty afterwards.

## Findings

1. **Important — FORBID-002 letter vs carried convention: machine-local runtime state
   (PIDs, live unit state) re-enters the diff inside the new dossier.**
   `engineering/changes/…-968b3c/evidence/runtime-observation-post-106.json:43-44,76`
   (`"primary_main_pid": 698333`, `"secondary_main_pid": 3597736`, and
   `"service_observation": "MainPID=698333\n…ActiveState=active\nUnitFileState=enabled…"`)
   and `PROJECT_STATE.json` runtime facts they mirror. The typed clause
   (`change-spec.yaml:90-92`) reads verbatim:
   > "Any credential value, private key, host identity or machine-local runtime state entering the diff; the runtime dossier carries only allowlisted observation fields."
   Because the dossier is a brand-new file, **every byte of it is an added diff line**, so
   the MainPID integers and live `ActiveState`/`UnitFileState` values do literally enter
   the diff — and a process ID plus service up-state is machine-local runtime state under
   any plain reading. This is a **carried convention, not a new leak**: the identical
   `service_observation` byte string and identical PID numbers are present in all four
   dossiers already tracked at base (`…post-91.json`, `…post-94.json`, `…post-98.json`,
   `…post-99.json` — verified via `git show d146ca4:<path>`), and the first half of the
   clause is word-for-word identical to the f98796 wave's FORBID-002 that already accepted
   this content. Failure scenario: none from disclosure (PIDs are ephemeral and reveal no
   secret; the values actually *carry trust signal*: PID equality is the evidence that
   neither unit was restarted, which FORBID-001/INV-002 depend on) — the real harm is
   governance drift: the spec clause is contradicted on its face by the very artifact it
   governs, so a future automated gate that enforces the letter would fail every release
   wave, and "allowlisted observation fields" **is defined nowhere in the repository**
   (grep: the phrase exists only in this change-spec), making the clause mechanically
   unverifiable. Fix: either define the field allowlist (runbook or schema) and name
   MainPID/unit-state as explicitly allowlisted liveness-probe fields, or replace PIDs
   with a salted hash of the observation tuple. No new content beyond the carried blocks
   was introduced (see per-point statement 1).

2. **Important — `active_delivery.pull_request: 106` (`PROJECT_STATE.json:802`) is a false
   linkage.** PR #106's head branch is `docs/record-105-delivery` (verified: `gh pr view 106
   --json headRefName` → `{"headRefName":"docs/record-105-delivery"}`) and it merged the omni
   package paperwork, not this change. `gh pr list --state all --head feature/v2.0.18-release-sync`
   returns `[]` and no PR is open repo-wide — **this wave's delivery PR does not exist yet**,
   while the same block's `branch`/`route_id`/`change_package` point at the new wave.
   Failure scenario: a successor agent or human reads `active_delivery` as "the PR that
   carries this candidate" and binds review/merge/publication grants to the already-merged
   #106, or treats the candidate as PR-delivered when it is not. The base precedent shows
   the intended semantics (base had `pull_request: 99` for the then-live chain). Fix before
   or in the artifact-child wave: set it to the real release-sync PR number once opened
   (null/pending until then). Not Critical: it forges no attestation — #106's own facts are
   correctly recorded in the landing row.

3. **Minor — stale contradiction left in an edited section.** `GROK_BUILD_HANDOFF.md:306`
   (item 4, "observed 2026-09-16" section) still asserts "The only open pull request at this
   observation is #33", while the same diff updates items 1–2 to post-#106 truth and
   `DARK_FACTORY_ROADMAP.md` records #33 closed at `2026-09-16T07:21:05Z`. The line is
   pre-existing at base (verified in `git show d146ca4:GROK_BUILD_HANDOFF.md`), so it is not
   introduced here, but AC-004's "bootstrap docs tell the post-…truth" claim is slightly
   over-asked while this row survives. No security content.

4. **Minor — observation scope widened without new disclosure.**
   `…post-106.json:39`: the `method` string now adds "`plus systemctl show -p ExecStart for
   the primary`" vs the predecessor's wording. Every value derived from that widened read
   (`control_repository`, profile, model) is byte-identical to the carried dossier, so no
   additional host information is disclosed; noted for completeness of the field
   enumeration.

No Critical findings. No secret-shaped content found; nothing needed location-only
redaction.

## Per-point statements with observed evidence

**1. Dossier `post-106` vs predecessor `post-99` — complete changed-field list.** Leaf
diff over both JSON trees: **12 changed values + 2 added list elements + 1 added limits
entry + 1 removed key; the other 44 shared leaves are byte-identical** (including the
whole `grok` block, `qwen_historical_acceptance`, and `service_observation`). Changed:
`observed_at` (10:53:13Z, fresh); `source_base` (c86b1a19→d146ca45 = the reviewed base,
correct by AC-004); `published_release.{tag,url,commit,published_at}` (v2.0.16→v2.0.17 —
advance is true: API shows Release `v2.0.17` `published_at 2026-09-16T01:17:14Z`, tag
object `5c6687ed…` → target `c86b1a19…`; the predecessor's v2.0.16 value was itself a
stale carry, and the new `carried_reason` sentence explains the advance);
`observation_provenance.{method,previous_dossier,carried_reason,unchanged_since_previous.note}`;
`qwen_current_configuration.evidence` (rewording only; its `control_repository`,
`selected_profile`, `model`, `live_enabled` unchanged); `source_trail.note`;
`source_trail.merged_source_not_installed` [98,99]→[101,102,105,106] (public PR numbers);
added `limits[5]` (#105 profile source-only statement); removed `source_trail.artifact_state`
(a deletion of historical prose, harmless since the same facts remain in `published_release`).
Judged against FORBID-002: **zero** new credential/key/host-identity values; no
hostname in the dossier and zero added diff lines containing "claw" (the pre-existing
`runtime_observations.host: "claw"` line was not modified); the machine-local runtime
state present is the **carried-identical** PID/unit-state convention — reported honestly
as the letter-vs-practice tension in Finding 1, not as an invented new leak.

**2. PROJECT_STATE.json archive fidelity.** `delivered_change_history.
v2_0_17_release_preparation.published_local_candidate` equals base `local_candidate` and
`.completion` equals base `current_unreleased_change` — both `deep-equal: True` **and**
`json.dumps` serialization/key-order identical, i.e. verbatim, not paraphrased; no
silent mutation of any published-release fact (Critical class) exists. All immutable
blocks re-checked unchanged base→HEAD: `published_release`, `prior_published_releases`,
`milestones`, `latest_published_release`, `delivered_non_milestone_work`, and every
pre-existing `delivered_change_history` key (`post_v2_0_16_landing`,
`v2_0_16_release_preparation`, `design_partner_pilot`, `l5_*`) → all `unchanged: True`.
Added-line scans for absolute home paths, private-key blocks, tokens, `.env` content and
credential shapes returned only three prose false positives ("image and audio **token**
accounting", the FORBID-002 statement text, "no **secrets** read") — nothing machine-local
or secret-shaped. The new pending `local_candidate` sets every identity to null and flips
`published/external_effect/operational_activation` false. (One record-integrity defect
found: Finding 2, `active_delivery.pull_request`.)

**3. Landing rows #101/#102/#105/#106 — independently re-derived; zero mismatches.**
GitHub `gh pr view` vs `PROJECT_STATE.json:191-227` (`current_unreleased_change.predecessors`)
and `:648-686` (`post_v2_0_17_landing.pull_requests`):

| PR | head (record=API) | merge_commit (record=API) | merged_at (record=API) | check_run_id (record=API) |
| --- | --- | --- | --- | --- |
| 101 | b40fd1a42a…= ✓ | 83925c1252…= ✓ | 2026-09-16T06:14:17Z ✓ | 104681990219 ✓ |
| 102 | 3f93e7bdfe…= ✓ | 98b77699be…= ✓ | 2026-09-16T07:52:29Z ✓ | 104704114422 ✓ |
| 105 | 30fea4e308…= ✓ | ad4d636e07…= ✓ | 2026-09-16T09:51:33Z ✓ | 104740673782 ✓ |
| 106 | 0a99a4d66e…= ✓ | d146ca455d…= ✓ | 2026-09-16T10:34:51Z ✓ | 104754117579 ✓ |

Each check run exists on the recorded head SHA with name exactly
`adaptive-trust-ci/verified@06ecf1c875bc`, `status=completed`,
`conclusion=success`, and **App ID 4694114** — the App required by `AGENTS.md`. The four
merge commits are single-parent (squash) commits forming the linear local main chain to
the base; `d146ca45` is an ancestor of `ee2cb850`. CHANGELOG/ROADMAP short-SHA citations
(`83925c1`, `98b7769`, `ad4d636`, `d146ca4`, `b40fd1a4`, `3f93e7bd`, `30fea4e3`,
`0a99a4d6`) match the full values. No fabricated or stale attestation identifier found.

**4. Nothing published.** `v2.0.18` tag: `gh api git/ref/tags/v2.0.18` → 404; release list
starts at v2.0.17; local and remote tag lists have no v2.0.18; `packages/` contains no
`*-v2.0.18.zip` or `.sha256` pair (only through v2.0.17 — `git ls-tree HEAD packages/`
and `ls` verified). Grep of every added `2.0.18`/`v2.0.18` mention shows all are
candidate/pending/negative forms: CHANGELOG heading `## 2.0.18 — 2026-09-16 (candidate,
unpublished)` plus "do not exist until the separate artifact-child step"; README
`(candidate, unpublished)` … "no v2.0.18 ZIP, sidecar, tag or GitHub Release exists in
this tree"; `local_candidate.artifact_child.status="not_built"`, digests null;
`current_unreleased_change.artifact_child` "Not built", `tag_and_release` "Not created";
dossier `limits`/`source_trail` keep #86's enablement remainder open, state no provider
call, no installation, and that `qwen-omni-intl` is source-only; ROADMAP line reads
"product version: 2.0.18 candidate (latest published release: v2.0.17…)". No installation
or provider-activation claim anywhere in the diff. INV-002/FORBID-001 hold.

**5. Lockstep tests — inverted, never deleted.** In `tests/test_project_state.py`: the
published-value assertions (`assertTrue(local["published"])`,
`assertEqual(published_at, V2017_PUBLISHED_AT)`, `assertTrue(external_effect)`,
`assertEqual(external_effect_scope, …)`, `assertEqual(pull_request, 99)`,
`assertEqual(checked_head/merge_commit/tree/artifact_child.{commit,tree,source_parent,source_parent_tree,zip_sha256,sidecar_sha256}, …)`)
became `assertFalse`/`assertIsNone` over exactly the pending-form set the task names:
`for key in ("reviewed_product_head","reviewed_product_tree","checked_head","merge_commit","tree"):
assertIsNone` (HEAD test file lines ~390) and
`for key in ("source_parent","source_parent_tree","commit","tree"): assertIsNone(local["artifact_child"][key])`,
plus `assertFalse(published)`, `assertIsNone(published_at)`, `assertFalse(external_effect)`,
`assertIsNone(zip_sha256/sidecar_sha256)`, `assertEqual(artifact_status,
"pending_unpublished_artifact_child")` — key coverage strictly superset of the base's. The
**archived v2.0.17 record gains positive checks** (`published`, `merge_commit=V2017_MERGE_COMMIT`,
`checked_head=V2017_CHECKED_HEAD`, zip/sidecar digest constants — all confirmed against the
real `sha256sum` outputs `770f1db5…`/`54db9f64…` and `git rev-parse` trees
`58269245…`/`2283e6a0…`), so publication authority moved to history instead of vanishing.
`test_structure.py`/`test_manifest_package.py`/identity literals (`VERSION`, `__version__`)
moved in lockstep, including the inverted `assertNotEqual` pair that keeps candidate≠published
while pending. The artifact-byte absence assertion in
`tests/test_manifest_package.py:1432-1433` is live for this state (the preceding lines pin
`artifact_status == "pending_unpublished_artifact_child"`, so the branch
`assertEqual(tuple(p for p in candidate_pair if p.exists()), ())` executes), while the
published v2.0.17 ZIP/sidecar bytes remain digest-verified in the same test. Result: `Ran
89 tests … OK` on the frozen tree, matching the test-plan's claimed "89 OK".

## Not verifiable read-only

- That the systemctl outputs quoted in the dossier match the host's live state at
  2026-09-16T10:53:13Z — I cannot re-run `systemctl` on the deploying host from here; I
  verified only self-consistency, byte-equality with the accepted predecessor dossier, and
  the non-contradiction with `PROJECT_STATE.runtime_observations`.
- That the check runs' underlying verification was cryptographically correct (the checks
  API proves the App produced id/success on that head, not its internal attestation chain
  — that is Trust CI's own domain).
- The authoring-session narrative in `state.json`/`tasks.md` timestamps (workflow
  paperwork; not merge authority per AGENTS.md).
