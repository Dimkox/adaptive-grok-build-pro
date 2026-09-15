# Security review — `b2932dc` v2.0.17 candidate identity sync (R)

**Verdict: PASS** — route `f98796afe7de`, receipt kind `security_review`, primary contract `FORBID-002`
(and secondary `FORBID-001`, `INV-001`).

- Object reviewed: commit `b2932dc6890852a71aeef2d767204bcd9afa4bf3` in worktree
  `/home/pall/grok-projects/adaptive-grok-build-pro-rel217` (branch `feature/v2.0.17-release-sync`,
  parent `7bbf42526f207db0007daafa4cc946cc2d81f465` = upstream `main`).
- Basis: the real diff (`git show b2932dc`, `git diff 7bbf425..HEAD`), a leaf-level JSON comparison of
  `PROJECT_STATE.json` between the two blobs, `git ls-tree`/`git cat-file` object checks, and the
  GitHub API. No claim in this report is taken from the change-package prose.
- **0 Critical, 0 Important, 4 Minor.** Nothing blocks merge on security grounds; two of the minors
  are one-line wording fixes recommended before the pull request opens.

Findings summary:

| # | Severity | Where | Issue |
| --- | --- | --- | --- |
| 1 | Minor | `…/architecture.md:18` | States `work_inventory` and `trust_ci` are "Unchanged"; both subtrees changed |
| 2 | Minor | `README.md:11` | "are delivered by this pull request" now attributes PR #93's adapters to PR #94 / this release-sync PR |
| 3 | Minor | `PROJECT_STATE.json:382` | Archived v2.0.16 candidate is described as "verbatim" but gained one annotation key (`record_scope`) |
| 4 | Minor | `…/route.json:7`, `…/tasks.md:3` | Stale `base 280cbff` citation after the rebase onto `7bbf425` |

---

## 1. Leakage (FORBID-002, credentials/secrets/PII) — PASS, no finding

Method: the 884 added lines were extracted (`git diff 7bbf425..HEAD | grep -n '^+'`) and scanned for
credential vocabulary, e-mail addresses, absolute user paths, environment-variable identifiers,
PEM/armour markers and high-entropy blobs. `.env`, private keys, credential stores and host config
files (`/etc/adaptive-l5/*`) were **not read at all** — that is prohibited by `AGENTS.md`
("Reading `.env`, private keys, credential stores…"), so this is a diff-content review, not a
cross-check against secret files. No repository secret scanner was invoked (the parent owns
`grok_verify --mode pr`, whose secret scan is the authoritative automated gate).

Result — **zero** hits for: key/token/password/cookie/bearer/credential *values*, `BEGIN … PRIVATE
KEY`, e-mail addresses (`[A-Za-z0-9._%+-]@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` → 0 matches), `/home/…`,
`/root/`, local usernames, or any `.env`-shaped assignment. Keyword matches were all prose about the
subject, not values: "reasoning-token usage" (`CHANGELOG.md:9`), "no credential, private key…"
(`requirements.md:22`, `release.md` security line, `change-spec.yaml` FORBID-002), `"evidence": "…no secrets
read…"` (dossier:53) and `"session_id": "manual"` (`route.json:66` — the literal string
`manual`, not a session token).
- Only environment-variable *names* ever mentioned anywhere in the diff: none. No
  `FACTORY_LANDING_*` name and no value appears in the added lines.
- Added file names contain no `.env`/`.pem`/`.key`/`secret`/`credential` entry
  (`git diff --name-only --diff-filter=A | grep -iE '(\.env|\.pem|\.key|secret|credential)'` → none).
- Entropy audit: 38 distinct 40-hex/64-hex tokens appear in added lines. 25 already exist verbatim in
  the base tree `7bbf425`. The 13 novel ones were each resolved: 12 are `git cat-file -t` → `commit`
  objects (the post-publication merge commits and checked heads `01d64e5…`, `280cbff…`, `31725f1…`,
  `45ccb04f…`, `5b03c1f1…`, `6130fbb8…`, `77debe55…`, `7bbf425…`, `9086f2bc…`, `9437efed…`,
  `9c147455…`, `af8419e6…`) and the 13th is the 64-hex `base_fingerprint` in the new package's
  `route.json` — a local routing fingerprint of the *worktree* whose secret material is excluded by
  design; `route.json` is precedent in 104 of the 106 tracked change packages. So **no novel
  high-entropy value is a secret**: every new blob is either a public git object or a local workflow
  digest, and all 64-hex digests in the dossier are byte-copies of already-published values (§2).
- Not a finding, recorded for completeness: the commit *metadata* author `Dimkox <bpall@mail.ru>` is
  the repository's long-standing configured identity on every prior commit, is not a diff line, and is
  the author identity of the public remote. `Caroline` (a project label, `CHANGELOG.md:14`,
  `PROJECT_STATE.json:292`) and `Dimkox` (public repo owner in URLs) are pre-existing vocabulary.

## 2. Machine-local state: the new observation dossier — PASS, no finding, no fields to remove

Target: `engineering/changes/20260915-release-sync-2-0-16-to-2-0-17-identity-bump-r-ar-f98796/evidence/runtime-observation-post-94.json`
(85 lines). It does embed host-adjacent facts: raw `systemctl show` output with `MainPID=698333` /
`MainPID=3597736` (`:75`), the two derived PID fields (`:42-43`), unit names
`adaptive-l5.service` / `adaptive-l5-grok.service` / `adaptive-l5-pr82-e2e-…service` (`:66`), the
socket path `/run/adaptive-l5-grok/control.sock` (`:9`), the control checkout
`/opt/adaptive-l5/releases/5f6f6ce1…/repository` (`:54`) and config/artefact SHA-256s (`:7`, `:14-15`,
`:60-61`).

Decision and evidence that committing it matches this repository's established practice:

1. **The precedent dossier is already on `main` and is byte-equivalent in every machine-local value.**
   `engineering/changes/20260915-update-third-party-workflow-components-superpowe-1b0c02/evidence/runtime-observation-post-91.json`
   became tracked at base `7bbf425` (merged as `280cbff`, PR #93). A key-by-key comparison of the two
   dossiers (script over both blobs) shows: keys only in the new file = the
   `observation_provenance.*` and `source_trail.*` blocks; keys only in the old file = none; differing
   shared leaf values = **only** `/observed_at` and `/source_base`. The PIDs, both unit names, the
   socket path, `grok_config_sha256`, `control_repository`, `attestation_id`, `check_run_id`,
   `job_id`s and all digests are identical copies. Therefore the new dossier introduces **zero new
   machine-local facts** beyond a timestamp and a git SHA — a field-removal request would delete
   nothing that is not already public in `main`.
2. **The same field classes are already tracked in the runbook layer**:
   `engineering/runbooks/l5-runtime-observation-2026-09-15.md:11-14` names the host ("Role on Claw"),
   both units, both installed SHAs and the `/opt/adaptive-l5/releases/5f6f6ce1…/repository` path;
   `engineering/runbooks/l5-provider-failover.md:12` and `factory/runtime/landing-failover.example.json:21`
   carry `/run/adaptive-l5-grok/control.sock`; `PROJECT_STATE.json` already carried
   `runtime_observations.host = "claw"` and the same `control_repository` at base (`7bbf425:PROJECT_STATE.json:1317`).
   A third precedent dossier `engineering/changes/20260915-documentation-align-readme-roadmap-and-bootstrap-d7264b/evidence/observed-state.json`
   carries `MainPID` and `grok_config_sha256` too.
3. **AGENTS.md scope check.** The contract excludes "Secrets, PEM/private keys, credentials, PostgreSQL
   runtime state, runtime approvals/receipts and host-local deployment scratch". None of those
   categories is present: there is no secret material, no PostgreSQL runtime state, no receipt
   (`.grok-stack/runtime/*` is gitignored with only `.gitkeep` tracked — `git ls-files
   .grok-stack/runtime` → 1 file, added in the initial commit, untouched here), and no deployment
   scratch. Dated *observations* are affirmatively Git content: `README.md`, `START_HERE.md`, the
   roadmap and `PROJECT_STATE.runtime_observations.evidence` all route a reader to a tracked dated
   observation, and this commit's job includes re-pointing that field. Not committing the dossier would
   leave `runtime_observations.evidence:2` (`PROJECT_STATE.json`) dangling at the stale post-#91 path.

What is *not* in the file, checked explicitly: no `/etc/adaptive-l5/grok-provider.conf` or
`grok-host.json` content or name, no unit drop-in, no environment value, no account/tenant identifier,
no absolute developer path, no hostname field (the string `claw` does not appear in the dossier).

## 3. Truthfulness of security-meaningful claims (FORBID-001) — PASS, one wording Minor

- `local_candidate` (`PROJECT_STATE.json:546-582`) is a correctly *pending* slot:
  `version 2.0.17`, `status pending_release`, `published false`, `published_at null`,
  `external_effect false`, `external_effect_scope null`, `operational_activation false`,
  `artifact_status pending_unpublished_artifact_child`, `pull_request null`, `review_status pending`,
  `source_base 7bbf425…`, `artifact_child.status not_built` with `zip_sha256`/`sidecar_sha256`/
  `commit`/`tree`/`source_parent`/`source_parent_tree` all null, and
  `checked_head`/`merge_commit`/`tree`/`reviewed_product_head`/`reviewed_product_tree` all null.
  Pinned by `tests/test_project_state.py:356-386` (loop at `:375` fails if a pending slot names any
  identity) and `:368-370` (`external_effect`, `external_effect_scope`, `operational_activation`).
- No publication/tag/install/activation claim exists anywhere. All 40 tree-wide `2.0.17` mentions were
  enumerated and every one is qualified (`candidate`, `unpublished`, `pending`, `not built`, `absent`,
  `requires its own … grant`). The strongest remaining ambiguity, accepted: `README.md:1` H1
  `# Adaptive Grok Build Pro v2.0.17` and `CHANGELOG.md:3` `## 2.0.17 — 2026-09-15 (candidate,
  unpublished)` use release-shaped conventions, but `README.md:7` and `CHANGELOG.md:5,18` immediately
  state no ZIP/sidecar/tag/GitHub Release exists, and `test_structure.py:280-285` pins both strings, so
  the qualifier cannot silently rot. `test_project_state.py:691-700` now asserts
  `"v" + product_version != published_release.tag` — the structural anti-FORBID-001 pin.
- Artifact absence is real, not asserted: `packages/` has no `v2.0.17` entry
  (`ls packages/ | grep -c 2.0.17` → 0) and `tests/test_manifest_package.py:1436` asserts the named
  pair does not exist while `artifact_status == 'pending_unpublished_artifact_child'`; the `else`
  branch (`:1438-1447`) independently requires both files plus a recomputed sidecar match, so flipping
  the status without delivering bytes cannot pass.
- No provider "went live" claim: `operational_qualification` keys stay false
  (`tests/test_project_state.py:689-691`), `runtime_observations.source_defaults.live_enabled = false`,
  and the dossier `limits[0-4]` + `carried_reason` state no reinstall, no restart, no provider
  activation, no factory publication (`live_url: null` in both acceptance records).
- **Minor #2** (`README.md:11`): the sentence still reads "the workflow artifact adapters (…) are
  delivered by this pull request" while this commit repointed the same table cell to
  "`main` observed at `7bbf425…` (PR #94)". A fresh reader attaches the adapters (third-party component
  compilers, `workflow_sources` pins) to PR #94 or to the release-sync PR, which deliver no such code —
  they landed through PR #93 as `280cbff1…`. The clause is pre-existing at base (where it pointed at
  `b6fe340`/PR #91 and was already wrong) and is unpinned by any test
  (`grep -rn "delivered by this pull request" tests/` → no match); a forward-fix to "delivered by PR #93"
  closes it.
- **Minor #1** (`architecture.md:18`): "Unchanged: `published_release`, `prior_published_releases`,
  `milestones`, `work_inventory`, `trust_ci`, packaging scripts, `packages/` bytes, PostgreSQL
  migrations 001-018" — the data-level diff shows `work_inventory` and `trust_ci` **did** change.
  Both changes are legitimate current-state updates that `INV-001` does not freeze, and nothing
  protected was touched (§4/§5), but the sentence is false in the one document a reviewer uses to
  decide what not to diff. Drop those two names from the list.
- **Minor (folded into #4)**: `requirements.md:7` AC-001 quotes the roadmap line as
  `product version: 2.0.17 (latest published release: …)` whereas the tree says
  `2.0.17 candidate (…)`. Cosmetic AC paraphrase; the authoritative pin is `test_structure.py:286-289`.

## 4. Immutability — PASS, no finding

Proved by blob comparison, not eyeballing: `git show 7bbf425:PROJECT_STATE.json > /tmp/a.json`,
`git show HEAD:PROJECT_STATE.json > /tmp/b.json`, then a recursive leaf walker (and a second script
keying list entries by identity rather than index). 81 leaf diffs, no type/coercion surprises, no
removed keys except within the mutable candidate slot, no added top-level keys.

Byte-unchanged (verified by `json.dumps(..., sort_keys=True)` equality): `published_release`,
`prior_published_releases`, `milestones`, `latest_published_release`, `operational_qualification`,
`schema_version`, and the frozen PostgreSQL migration range in every location
(`/current_unreleased_change/frozen/postgresql_migrations`,
`/delivered_change_history/design_partner_pilot/record/frozen/postgresql_migrations`,
`/active_delivery/integrated_stack/migrations` → all preserved; migrations 001-018 untouched, matching
`rollback.md`).

Changed subtrees, classified:

| Subtree | Kind | Note |
| --- | --- | --- |
| `product_version`, `observed_at`, `observed_main_sha` | rewrite | intended identity/currency move |
| `active_delivery` | rewrite (4 leaves: `branch`, `change_package`, `next_action`, `route_id`) | mutable pointer; `integrated_stack` incl. migrations untouched |
| `current_unreleased_change` | rewrite + appends (`scope[0-2]`, `predecessors[0-1]`, `identity`, `change_id`, `route_id`, `target_version`, `explanation`) | `frozen` untouched; `source_base` → `7bbf425…` |
| `l5_production_preparation` | rewrite (1 leaf `actual_main_observation`) | |
| `local_candidate` | **slot takeover**: every v2.0.16 identity repointed/nulled, `zip_source_note` key removed, `predecessor_record` pointer added | This is the candidate slot, not a historical record; its prior content is archived (row below), so no published fact is lost |
| `delivered_change_history.post_v2_0_16_landing` | **append** (new key) | 12 rows, see §6 |
| `delivered_change_history.v2_0_16_release_preparation` | **append only** (`added=['published_local_candidate']`, `changed=[]`, `removed=[]`) | no pre-existing leaf rewritten |
| `delivered_change_history.{design_partner_pilot,l5_offline_v2_0_14,l5_source_preparation}` | **unchanged** | |
| `runtime_observations` | rewrite (2 leaves: `evidence` path → post-94 dossier, `observed_at`) | `host`, both `services.*.installed_sha`, both `acceptance` blocks, digests untouched |
| `trust_ci` | rewrite of `last_success` only (6 leaves: PR 91→94, head, merge, check_run_id, attestation_id, check_url, `record_scope`) | semantically a "latest" pointer, not a history append |
| `work_inventory.open_pull_requests` | 4 entries → 2, keyed comparison: PR #15 and PR #33 records **byte-identical**; #13 and #64 removed and present in the landing append | removal is correct (they merged); no surviving record was edited |
| `work_inventory.retained_unresolved[1].purpose` | **rewrite** of a pre-existing entry's prose | not covered by `INV-001` (it is live continuation guidance, not a released fact); change is truth-promoting — it names PR #93's merge `280cbff1…` and replaces the stale "delete after that PR merges" with the retention rule |

**Minor #3** — precision, not a violation: `PROJECT_STATE.json:382` gives the archived v2.0.16
candidate a `record_scope` key that the live slot did not have (old value `null`/absent). Every
identity value, digest and the two null `reviewed_product_*` fields are byte-identical, so the commit
message's "moved verbatim" holds for all facts; strictly, one annotation field was *added* (and the
added text itself says it was archived verbatim from `local_candidate`). Suggest "verbatim plus an
archival annotation" if the wording is revisited.

Also noted, no action: the same commit edits one line in an unrelated delivered package,
`engineering/changes/20260915-fix-verify-reject-same-inode-cas-tampering-by-co-665347/evidence/review-code.md:9`,
changing a broken citation `git diff --stat f10741b ebd904a` → `ebd9a0a`. Verified:
`git cat-file -t ebd9a0a` → `commit`, `git cat-file -t ebd904a` → *fatal: not a valid object name*.
That is a truthfulness repair of a nonexistent SHA reference, it adds no claim, and it is the only
modified (non-added) file outside `PROJECT_STATE.json`.

## 5. Protected surface and artifact ownership — PASS, no finding

`git diff --name-only 7bbf425..HEAD -- trust-ci architecture governance factory scripts packages` →
**empty** (0 files). `packages/` gained no bytes and is not merely equal in content but equal as a
tree object: `git rev-parse 7bbf425:packages HEAD:packages` →
`86fa35d0268350e22b7d0d89ef6592322c69f4d7` for both, and `git ls-tree -r packages` digests match
(`2e4c12c81d73c0c323470e43b8ed51e8` both sides). The 24 changed paths are exactly: the 8 identity
files (`VERSION`, `.grok-stack/adaptive_grok/__init__.py`, `README.md`, `CHANGELOG.md`,
`DARK_FACTORY_ROADMAP.md`, `START_HERE.md`, `GROK_BUILD_HANDOFF.md`, `PROJECT_STATE.json`), the 3
coupled test modules, the 1 typo repair of §4, and the 12 files of this change package. No
`.github/workflows/` addition, no production code, no migration, no packaging script change — the
artifact child remains the sole owner of the two `packages/` files.

## 6. Dossier `carried_forward` / `source_trail` vs git (and host) truth — PASS, no finding

- `source_trail.merged_source_not_installed = [93, 13, 94]` and the note "merged source on main at this
  base, none installed into either running unit" are **both** verified, which is stronger than the
  brief assumed for installed state:
  - Merged: `gh pr view --json state,mergedAt,mergeCommit,headRefOid` → 93 = MERGED
    `280cbff1…`/`9086f2bc…`/`2026-09-15T20:03:41Z`; 13 = MERGED `43831155…`/`6130fbb8…`/`21:03:37Z`;
    94 = MERGED `7bbf4252…`/`9437efed…`/`22:58:12Z`. `git log --first-parent
    969c4f65..7bbf425` lists exactly the 12 merge commits the landing archive names, in that order.
  - Not installed: read-only `systemctl show -p ExecStart --value` on this host (hostname `claw`)
    resolves primary → `/opt/adaptive-l5/releases/5f6f6ce1ecb0…/venv/bin/adaptive-landing-server` and
    secondary → `/opt/adaptive-l5/releases/61a05da2bd0c…/venv/bin/adaptive-landing-server`, i.e. exactly
    the recorded installed SHAs; `ls -d /opt/adaptive-l5/releases/*/` shows only `5f6f6ce1…`,
    `61a05da2…` and `969c4f65…` — no release directory for `280cbff…`, `4383115…` or `7bbf425…`.
    `git merge-base --is-ancestor` confirms both installed SHAs precede PR #93. No unit drop-in, config
    file or environment file was read.
- `observation_provenance.unchanged_since_previous` ("Identical MainPID and enabled state in both
  dossiers; neither unit was restarted") is reproducible right now: re-running the dossier's own stated
  method (`systemctl show -p MainPID -p Id -p ActiveState -p UnitFileState`, unprivileged) returned
  `MainPID=698333 … adaptive-l5.service active enabled` and `MainPID=3597736 …
  adaptive-l5-grok.service active enabled` — byte-equal to the dossier's `service_observation:75` and to
  the base post-91 dossier.
- `carried_forward = [published_release, qwen_historical_acceptance, grok]` is consistent with the file
  contents: those three blocks are byte-copies of the post-91 dossier (§2.1), so they are correctly
  *not* presented as fresh evidence, and the dossier's own fresh facts are limited to
  `observed_at`, `source_base` and the two systemctl readings. The embedded `published_release` block
  (tag `v2.0.16`, `969c4f65…`, `2026-09-13T22:04:08Z`) matches `PROJECT_STATE.published_release`, which
  this commit left untouched.
- Landing-record cross-checks: spot-verified `check_run_id` 104591923631 (#94) and 104536573008 (#93)
  via `gh api …/check-runs/<id>` → both
  `adaptive-trust-ci/verified@06ecf1c875bc`, `completed`, `success`, on head SHAs equal to the recorded
  checked heads. `merged_at` values are GitHub merge timestamps and differ from local git committer
  dates by ≤1 s on 7 of 12 rows (e.g. #94 `22:58:11+03:00`=22:58:11Z vs recorded 22:58:12Z); that is
  API-vs-committer-clock, not a false record.
- **Minor #4**: `route.json:7` records `base_commit 280cbff1…` and `tasks.md:3` says "base `280cbff`",
  while the commit's actual parent and `local_candidate.source_base` are `7bbf425…`. That is the
  pre-rebase routing snapshot (`tasks.md:6` records the rebase), so no security statement is wrong —
  but a durable route copy that names a base three commits behind the delivered parent reads as a
  provenance gap to the next agent. Either annotate it as the routing-time base or cite `7bbf425`.

## 7. Residual risk / out-of-scope for this receipt

- Whether the *deployed* Trust CI policy, holdout bundle, images, PostgreSQL state, App keys and branch
  protection match what the docs assert is outside the pull-request trust domain and was not
  (and cannot be) reviewed here; `AGENTS.md` keeps it independent of this commit.
- The App-owned exact-head check for this commit's own head does not exist yet; per
  `release.md`/`tasks.md`, `R` may merge only on
  `adaptive-trust-ci/verified@06ecf1c875bc` SUCCESS for this exact SHA, and tag push / GitHub Release
  publication still require their own exact delegated grants. This receipt is local evidence and never
  merge authority.
- This review did not run the test suite or `scripts/grok_verify.py --mode pr` (owned by the parent);
  the `FORBID-002`/`FORBID-001` conclusions above are diff-, object- and API-derived.
