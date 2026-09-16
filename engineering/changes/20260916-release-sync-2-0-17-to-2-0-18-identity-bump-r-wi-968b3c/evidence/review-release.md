PASS

# Release review — v2.0.18 release sync `R` (route `968b3ce9e148`, wave `…-968b3c`)

Reviewed object: `ee2cb850e05e4ccaa4bb7912340aa6401fbc67c5` on `feature/v2.0.18-release-sync`,
clean tree, diffed against base `d146ca455d615683765b443b747f55aa4dbad436` (PR #106 merge, still
`origin/main`). Contract: `change-spec.yaml` AC-001…AC-004, INV-001/INV-002, FORBID-001/002.
Precedent: `78082a290f8b90cade88685351fbb2ba263689b9` (v2.0.17 R) plus the #102 landing convention.

## Verdict and rationale

**PASS — no Critical finding.** Nothing anywhere claims a published v2.0.18; the four acceptance
criteria and both invariants hold against actual bytes and against live Git/GitHub/systemd state.
Every identity surface agrees on `2.0.18` while the published identity stays `v2.0.17` with
byte-identical immutable facts. The archived v2.0.17 candidate record is verbatim (key order
included). All four landing rows re-derive exactly from Git **and** the checks API. 89 coupled tests
pass, and the pending-state assertions were *inverted*, not weakened (108 → 119 `assertEqual` plus
10 `assertIsNone` in the same method versus the 78082a2 precedent).

Three Important findings must be fixed. Two are one-line edits in `PROJECT_STATE.json` and one is a
single stale sentence in `GROK_BUILD_HANDOFF.md`. None of them contradicts a typed acceptance
criterion, and none touches trust or publication authority, so they do not change the verdict — but
no pull request or App check exists for this branch yet, so fixing them now is free, and finding 1 in
particular should not survive into `main` because it is the *only* SHA pointer to PR #100 in the
durable handoff.

## Findings

### 1. Important (high confidence) — the new v2.0.17 archive records a non-existent commit SHA for PR #100

`PROJECT_STATE.json:537` (`delivered_change_history.v2_0_17_release_preparation.historical_snapshot`,
inside the block `:535` added by this commit):

> `…with the publication successor PR #100 (cfc4a576c3a31015fa79176427f5e73819ea2fbc); tag v2.0.17 …`

The real commit is `cfc4a5741210cc7b28431c56c92b9d549540c65d` — `git rev-parse cfc4a57` and
`gh api pulls/100 → merge_commit_sha` both return it, and the full correct string is already recorded
elsewhere in this same tree (`engineering/changes/20260916-fix-architecture-stream-oversized-tracked-binari-1895e1/route.json:17`).
The recorded value shares only the 7-character prefix `cfc4a57` and then diverges;
`git cat-file -t cfc4a576c3a3…` fails outright. This is the only defect among **28** distinct 40-hex
identifiers this commit adds — the other 27 resolve to objects of the expected type (commits, trees
`2283e6a0…`/`58269245…`, tag `5c6687ed…`).

*Failure scenario.* START_HERE.md:16 states plainly that "the v2.0.17 successor (#100) is not in the
ledger and is referenced only through the release records", so this single string is the sole
machine-readable pointer to the publication-successor commit. A later agent that re-derives the v2.0.17
chain by SHA (`git cat-file`, `git log --ancestry-path cfc4a576c3a3..`, a bisect, or an
evidence-linkage check) gets "object not found" and must either conclude the archive is unreliable or
invent a substitute — exactly the failure mode AC-002's "re-derived from Git, the GitHub API and the
Trust CI job store" wording exists to prevent. Direction: certifies-falsely.
*Fix:* replace with `cfc4a5741210cc7b28431c56c92b9d549540c65d`.

### 2. Important (high confidence) — `active_delivery.pull_request` moved from the precedent's publication-PR pointer to a merged non-publication PR

`PROJECT_STATE.json:802`: `99 → 106`, alongside `branch: feature/v2.0.18-release-sync` (`:801`).

The field is a historical pointer to **the pull request that delivered the latest publication**, not to
the in-flight branch's PR, and not to whichever PR produced `source_base`. Traced across history:

| commit | `active_delivery.pull_request` | `active_delivery.branch` |
| --- | --- | --- |
| `78082a2` (v2.0.17 R) | `79` | `feature/v2.0.17-release-sync` |
| `c86b1a1` (v2.0.17 A) | `79` | `feature/v2.0.17-release-sync` |
| `d146ca4` (this base) | `99` | `feature/v2.0.17-release-sync` |
| `ee2cb85` (HEAD) | `106` | `feature/v2.0.18-release-sync` |

PR #79's own head branch is `feature/v2.0.16-artifact-child` (verified via API) — i.e. the precedent
deliberately carries a *different* branch's PR number. The v2.0.17 R wave left it untouched at `79`; only
the SR wave (#100) advanced it, to `99`, once v2.0.17 was actually published. PR #106 is none of those:
it is the already-merged omni package-closure PR from `docs/record-105-delivery`, it is recorded in this
same commit as landing row #106 (`PROJECT_STATE.json:643` block), and **no pull request exists yet for
`feature/v2.0.18-release-sync`** (`gh pr list --state all --head feature/v2.0.18-release-sync` → `[]`).
`ee2cb85` is the only commit in history that ever wrote `106` here.

*Failure scenario.* `PROJECT_STATE.json` is the declared zero-context handoff. A routed agent reading
`branch: feature/v2.0.18-release-sync` + `pull_request: 106` can conclude the release-sync delivery is
already merged, and either proceed to stage A against an unmerged branch or treat PR #106's consumed
App check (`104754117579`, bound to head `0a99a4d6…`) as this commit's merge authority — which
`AGENTS.md` forbids (a new head requires a fresh exact-SHA check). Direction: certifies-falsely.
*Fix:* restore `99` (precedent-consistent) or set `null` until this wave's PR actually exists. Note the
field is test-uncovered: `tests/test_project_state.py:445-446` mirrors only
`route_id`/`branch`/`change_package`/`next_action` into `active_delivery`, so nothing would have caught this.

### 3. Important (high confidence) — `GROK_BUILD_HANDOFF.md` still asserts an open pull request that does not exist

`GROK_BUILD_HANDOFF.md:306` (bullet 4): "The only open pull request at this observation is #33".
GitHub says PR #33 `state=closed`, `merged=null`, `closed_at=2026-09-16T07:21:05Z`, and the repository
currently has **zero** open pull requests. The same tree says the opposite twice: `START_HERE.md:14`
("No pull request is open at this observation") and `DARK_FACTORY_ROADMAP.md:98` (#33 closed, "ending
the last open pull request").

Pre-existing at the base, so not introduced here — but this wave rewrote bullets 1–2 directly above it
under the same `## Next actions (observed 2026-09-16)` header (`:301`) and advanced `observed_main_sha`,
leaving a handoff surface dated 2026-09-16 that contradicts the two files it sits next to. AC-004's
intent ("bootstrap docs tell the post-#101/#102/#105/#106 truth") covers it; it is a one-sentence edit.
*Fix:* state that no pull request is open and that #101/#102/#105/#106 are the merges since publication.

### 4. Suggestion (high confidence) — `current_unreleased_change` was re-serialized in alphabetical key order, diverging from the field-for-field precedent

`PROJECT_STATE.json:176-237` now runs `artifact_child, branch, change_id, change_package, explanation,
external_effect, frozen, identity, next_action, …` (alphabetical), while the 78082a2 precedent and the
`delivered_change_history.v2_0_17_release_preparation.completion` block lower in the same file
(`PROJECT_STATE.json:556`, the verbatim archive of the record being reordered) keeps the semantic order
`change_id, route_id, branch, change_package,
identity, status, stage, source_base, target_version, scope, predecessors, …`. The result is that the
same logical record exists twice in one file in two different field orders.

Measured, not assumed: restoring the precedent order shrinks this file's diff from **+240/−79** to
**+232/−71**, so the reorder costs ~16 lines of avoidable churn. This is *not* mass re-dump damage —
the file has no indent drift and no escaping churn (both sides round-trip exactly through
`json.dumps(obj, indent=2, ensure_ascii=False)`), top-level key order is preserved,
`delivered_change_history`'s new blocks are placed in the established chronological position, and a
whole-tree walk finds **exactly one** pure key reorder in the entire file (this one). INV-001 is not
violated: no historical value changed. `decisions.md` order-preservation convention argues for fixing it
while the block is being rewritten anyway.

### 5. Nice to have — the fresh dossier drops `source_trail.artifact_state`

`post-106` carries no `source_trail.artifact_state` where `post-99` had one asserting "publication is
repository delivery only; nothing installed, restarted or activated". Content is preserved across
`limits[]` and `source_trail.note`, no test references the field (`grep -rn "source_trail\|artifact_state" tests/`
→ no hits), and dropping a *publication* statement from a pending-artifact dossier is arguably more
honest. Noted only so the omission is a decision rather than an accident.

### 6. Observation (not a defect) — the wave's own local preflight is still open

`tasks.md` leaves `grok_verify --mode pr` unchecked, `state.json` status is `implementing`, and
`route.json` records `write_agent: null`. Consistent with an unshipped R commit, and route records are
workflow evidence rather than merge authority; flagged only because this review is on tree bytes and
does not substitute for that gate or for the exact-head App check.

## Requirement-by-requirement result

| Check | Result | Evidence |
| --- | --- | --- |
| AC-001 identity coherence | **PASS** | `VERSION`=2.0.18; `.grok-stack/adaptive_grok/__init__.py:3` `2.0.18`; `README.md:1` H1 + `:7` `Identity: **2.0.18** (candidate, unpublished)`; `CHANGELOG.md:3` `## 2.0.18 — 2026-09-16 (candidate, unpublished)`; `START_HERE.md:7,9`; `GROK_BUILD_HANDOFF.md:303-304`; `DARK_FACTORY_ROADMAP.md:42` `product version: 2.0.18 candidate (latest published release: v2.0.17; published 2026-09-16T01:17:14Z)` + PR inventory `:98`; `PROJECT_STATE.json:7` `product_version: 2.0.18` with `:8` `latest_published_release: v2.0.17` and `published_release.tag: v2.0.17` unchanged |
| No v2.0.18 publication claim (FORBID-001) | **PASS** | All 4 `v2.0.18` mentions in live docs are candidate/absent/negative framings; the only bare `v2.0.18` strings are the README H1 and the two asserted-absent delta paths (`PROJECT_STATE.json:762-763`) |
| AC-002 landing rows {101,102,105,106} | **PASS** | Row set at `:643` is exactly `{101,102,105,106}`; the complete merged-since-publication set from GitHub is `{100,101,102,105,106}` and #100 is correctly excluded as the previous chain's SR step by the documented #102 exception. Every head, `merge_commit`, `merged_at` matches `git log origin/main` + `gh api pulls/N`; all four `check_run_id`s return `adaptive-trust-ci/verified@06ecf1c875bc` `conclusion=success`. `record_scope` wording matches the `post_v2_0_16_landing` template |
| AC-003 pending candidate + verbatim archive | **PASS** | `local_candidate`: identities null, `published:false`, `external_effect:false`, `status:pending_release`, `artifact_status:pending_unpublished_artifact_child`, delta pair names only the v2.0.18 pair. `published_local_candidate` (`:602`) is **order-sensitively** identical to `git show d146ca4:PROJECT_STATE.json → local_candidate` (`json.dumps` string equality, not just deep equality); `completion` likewise equals the previous `current_unreleased_change` verbatim. Pair absent on disk (`ls packages/ \| grep -c v2.0.18` → 0) and asserted absent by `tests/test_manifest_package.py:1435-1436` |
| AC-004 bootstrap truth + dossier | **PASS** (with finding 3) | Observation SHA `d146ca45…` present in README "Current state" and START_HERE "Current project state" sections, still required by `test_current_epoch_and_app_are_consistent_in_handoff_documents` (`tests/test_project_state.py:670-677`, section-scoped via `_section`, still asserting `assertNotIn` the superseded epoch). #86 open, #87 closed, #104 open, no PR #103/#104/#107 — all doc claims match GitHub |
| INV-001 historical values frozen | **PASS** | Leaf walk of both JSON trees: 68 value changes, all confined to `observed_at`/`observed_main_sha`/`product_version`, `current_unreleased_change`, `local_candidate`, `active_delivery`, `runtime_observations.{observed_at,evidence}`. `published_release`, `prior_published_releases`, `milestones`, `trust_ci`, `delivered_milestones_on_main`, `implemented_milestones`, `work_inventory`, `l5_production_preparation`, `operational_qualification`, `fresh_clone`, `intentionally_untracked`, `schedule`, released artifact digests: **value-equal and order-equal** |
| INV-002 nothing published | **PASS** | No local or remote `v2.0.18` tag (`git ls-remote --tags origin` ends at `v2.0.17` → `c86b1a19…`); `gh release view v2.0.18` → "release not found"; latest release still v2.0.17 at `2026-09-16T01:17:14Z`; no `packages/` bytes added; diff is 8 modified + 12 added, all additions inside the change package |
| FORBID-002 no secrets/host state | **PASS** | Secret-pattern scan of every added line returned only the phrases "token accounting" and "no secrets read". No new machine-local field entered the dossier: the `MainPID`s and `control_repository` are *unchanged* from post-99 (they do not appear in the dossier diff), `service_observation` is test-required, and the dossier names no hostname |
| Tests | **PASS** | `Ran 89 tests in 9.242s — OK` |
| mistakes.md / decisions.md | **PASS** | `decisions.md` untouched. `mistakes.md` gains only an 11-line appended entry (`:1140-1149`) that recurs the real 2026-09-13 rule at `mistakes.md:878-884` (`pkill -f` matching its own command line) and strengthens it to exact-PID polling; no other governance row changed |

## Commands run (read-only) and observed output

```
git status --porcelain=v1 --branch        ## feature/v2.0.18-release-sync...origin/main [ahead 1]  (no dirty files)
git rev-parse HEAD                        ee2cb850e05e4ccaa4bb7912340aa6401fbc67c5
git diff --stat d146ca4..HEAD             24 files changed, 728 insertions(+), 157 deletions(-)
git diff --numstat d146ca4..HEAD -- PROJECT_STATE.json   239  78  PROJECT_STATE.json
git rev-parse origin/main                 d146ca455d615683765b443b747f55aa4dbad436 (unchanged by this wave)

# leaf-level JSON walk, d146ca4 -> HEAD
value changes: 68 | added paths: 2 (v2_0_17_release_preparation, post_v2_0_17_landing)
removed paths: 1 (local_candidate.artifact_child.zip_source_note -> moved into the archive verbatim)
key-order-only restructures: 1 (.current_unreleased_change)
formatting: both sides round-trip exactly as json.dumps(indent=2, ensure_ascii=False)+"\n"
churn with precedent key order restored: +232 -71 (vs committed +240 -79)

# ordering / verbatim checks
archived published_local_candidate == d146ca4:local_candidate            order-sensitive True
archived completion                == d146ca4:current_unreleased_change  order-sensitive True
delivered_change_history: new keys appended in established position; relative order of old keys preserved True

# GitHub re-derivation (AC-002)
gh api pulls/101  2026-09-16T06:14:17Z 83925c12… b40fd1a4… head ref fix/architecture-stream-large-binaries
gh api pulls/102  2026-09-16T07:52:29Z 98b77699… 3f93e7bd… docs/release-chain-convention-and-inspected-causes
gh api pulls/105  2026-09-16T09:51:33Z ad4d636e… 30fea4e3… fix/qwen-omni-intl-and-probe-class
gh api pulls/106  2026-09-16T10:34:51Z d146ca45… 0a99a4d6… docs/record-105-delivery
gh api commits/<head>/check-runs → id 104681990219 / 104704114422 / 104740673782 / 104754117579,
                                   all name adaptive-trust-ci/verified@06ecf1c875bc conclusion=success
gh api "pulls?state=closed" | merged_at > 2026-09-16T01:17:14  → {100,101,102,105,106} exactly
gh pr list --state all --head feature/v2.0.18-release-sync     → []      (no PR exists for this branch)
gh api pulls/79   branch=feature/v2.0.16-artifact-child        (precedent: pointer ≠ active branch)
gh api issues/86  open | issues/87 closed(state=PR) | issues/104 open | pulls/103,104,107 → 404
gh api pulls/33   state=closed merged=null closed_at=2026-09-16T07:21:05Z
gh pr list --state open                                         → (empty: no open PRs)

# INV-002 / FORBID-001 reality
git tag -l 'v2.0.1[6-9]'        v2.0.16 v2.0.17          (no v2.0.18)
git ls-remote --tags origin     … newest v2.0.17 → 5c6687ed tag object → c86b1a19
gh release view v2.0.18         release not found
gh release view (latest)        v2.0.17 publishedAt 2026-09-16T01:17:14Z
ls packages/ | grep -c v2.0.18  0
git grep -no "cfc4a57[0-9a-f]*" PROJECT_STATE.json:537 cfc4a576c3a31015fa79176427f5e73819ea2fbc
git rev-parse cfc4a57           cfc4a5741210cc7b28431c56c92b9d549540c65d
git cat-file -t cfc4a576c3a31015fa79176427f5e73819ea2fbc
                              fatal: git cat-file: could not get object info
# all 28 added 40-hex ids: 27 resolve with the expected type; 1 BAD (the above)

# tests + live corroboration of the fresh dossier
python3 -m unittest tests.test_project_state tests.test_structure tests.test_manifest_package
                              Ran 89 tests in 9.242s — OK
git show 78082a2:tests/test_project_state.py  assertion forms for the pending slot: identical set,
                              HEAD adds artifact_child.identity=="A" and truthy requirement
                              (assertEqual 108→119, assertIsNone 8→8, assertFalse 6→6) — inverted, not removed
hostname                      claw
systemctl show -p MainPID -p Id -p ActiveState -p UnitFileState adaptive-l5{,-grok}.service
                              MainPID=698333 active enabled / MainPID=3597736 active enabled
                              → matches dossier observation_provenance.unchanged_since_previous exactly
systemctl show -p ExecStart -n 1 adaptive-l5.service
                              /opt/adaptive-l5/releases/5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a/…
                              → matches qwen_current_configuration (control_repository + profile)
```

## What I could not verify

- **That the dossier observation was actually executed at `2026-09-16T10:53:13Z`.** I re-ran the same
  read-only `systemctl` probes at review time and every field matches (identical MainPIDs, active,
  enabled, unchanged `ExecStart` release path), which proves the *content* is true and that neither unit
  restarted since — but a capture timestamp is not independently provable from the tree.
- **`python3 scripts/grok_verify.py --mode pr`.** Deliberately not run: it writes fingerprint-bound
  local receipts and runtime state, which my read-only constraint forbids. `tasks.md` leaves it
  unchecked, so the wave's own preflight remains outstanding and this PASS does not substitute for it.
- **Merge eligibility.** No exact-head `adaptive-trust-ci/verified@06ecf1c875bc` check can exist for
  `ee2cb85` until a pull request is opened; nothing here is, or may be treated as, merge authority.
- **The mistakes.md narrative's session history** (that two live gates were destroyed and a third run's
  empty log was misread). Not reconstructible from tree bytes; I verified only that the cited
  2026-09-13 predecessor entry exists (`mistakes.md:878-884`) and that the new row's technical claims are
  self-consistent with it.
- **`route.json` `base_fingerprint`** — not recomputed; it is workflow evidence, not merge authority.
