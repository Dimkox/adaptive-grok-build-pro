PASS

Route-selected `release_reviewer`, read-only. Subject `497de07eee1c65b129a8836b51767aebb9d49c1f` (HEAD tree `c904957fa7d852a521bf6ea4b56b31da1dec90d9`), branch `feature/v2.0.18-artifact-child`, base/diff `git diff fc8d9e6f11bb188ee514784d3b6f614a6da72803..HEAD`, working tree clean at review start (`git status --porcelain` empty). Change `20260916-build-and-deliver-the-deterministic-v2-0-18-zip-f03c54`, stage **A** of the `R → A → tag → SR` chain for `v2.0.18`; precedent `c86b1a1989ace899a4450bde558fcd8adc00e4e2` (v2.0.17 artifact child, PR #99). Reviewer created no file other than this report and wrote no local receipt.

No Critical finding. Two Important currency findings (both prose, both fixable in `SR`, neither touches the delivered bytes, the record's authority claims, or merge eligibility) and six Minor. Go/no-go: **GO for merging A** once the route's `security_review` and `verification` receipts are recorded on the final head fingerprint and the App-owned `adaptive-trust-ci/verified@06ecf1c875bc` is SUCCESS on that exact head.

## Scope and commands run

```
git status --porcelain / git rev-parse HEAD / git rev-parse fc8d9e6^{tree}
git diff --stat fc8d9e6..HEAD ; git diff fc8d9e6..HEAD -- <each file> ; git show --stat c86b1a1 ; git show c86b1a1 -- tests/ packages/README.md
sha256sum packages/adaptive-grok-build-pro-v2.0.18.zip{,.sha256} ; xxd ./{zip,zip.sha256} ; stat -c %s
git cat-file blob HEAD:packages/adaptive-grok-build-pro-v2.0.18.zip | sha256sum   (tracked blob, not the checkout)
git cat-file -s HEAD:packages/adaptive-grok-build-pro-v2.0.18.zip
python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package          -> Ran 89 ... OK
python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package tests.test_change_spec -> Ran 119 tests ... OK
for m in ...; do python3 -m unittest tests.$m; done   -> 19 / 14 / 56 / 30
python3 - <<zipfile/json>>   (INV-001 subtree equality fc8d9e6 vs HEAD; AC-003 null dump; zip integrity 2985 members, testzip None)
Independent dual rebuild: umask 077; two `git clone --no-hardlinks` of /home/pall/grok-projects/adaptive-grok-build-pro
  into /tmp/rr-a18-stage/{1,2} (0700), each `git checkout --detach fc8d9e6…`, each asserted HEAD==fc8d9e6 and
  `git status --porcelain` empty, each `python3 scripts/package_stack.py --output <clone>/…v2.0.18.zip`
Tamper proof of the delivered-form assertion (extracted verbatim into a /tmp root; repo untouched):
  baseline / tamper-zip / missing-zip / tamper-sidecar / one-space-sidecar
gh pr view 107 ; gh api …/commits/f8c5021c…/check-runs ; gh api …/check-runs/104782126773
gh pr list --state open ; git ls-remote origin main refs/heads/feature/v2.0.18* ; git tag --list 'v2.0.1*'
gh release list ; gh release view v2.0.18 ; gh release view v2.0.17 --json assets,targetCommitish,publishedAt
gh issue view 80 --json state ; gh issue view 101 --json state
```

## 1. AC-001 / AC-002 — the pair and its digests — PASS

Digests recomputed two independent ways; nothing was taken from the record.

| Item | Recorded | Recomputed | Result |
| --- | --- | --- | --- |
| `artifact_child.zip_sha256` | `0bc6adc9f4660e1b60be4cb4895e97f2641338b52b6a5e05ac3c7acd85e59b3a` | working-tree file **and** `git cat-file blob HEAD:…zip \| sha256sum` → both `0bc6adc9…` | match |
| zip size | 11 160 330 B (notes/commit msg) | `stat` 11160330, `git cat-file -s` 11160330 | match |
| `artifact_child.sidecar_sha256` | `dd7e2ec5a979d70062f206f381efcb38b92da2f7bfc1129034b459e125a54216` | `sha256sum` of the tracked sidecar | match |
| sidecar format | `<sha>  <name>\n` | `xxd` → `0bc6adc9…9b3a` `2020` `adaptive-grok-build-pro-v2.0.18.zip` `0a`; 102 bytes; embedded digest == recomputed zip digest | exact (two spaces, basename only, LF) |
| sidecar parity with v2.0.17 | precedent byte shape | `git show HEAD:packages/…v2.0.17.zip.sha256 \| xxd` → identical shape | no drift |
| zip integrity | — | `zipfile.testzip()` → `None`, 2985 members, prefix `adaptive-grok-build-pro/`; no `.env`/key/credential member (only `*.env.example`), no prior release ZIP, `v2.0.18.zip` not nested | clean |

**Independent reproduction (not asserted, re-derived).** I ran the dual build myself from the recorded `source_parent` alone:

```
0bc6adc9f4660e1b60be4cb4895e97f2641338b52b6a5e05ac3c7acd85e59b3a  /tmp/rr-a18-stage/1/adaptive-grok-build-pro-v2.0.18.zip
0bc6adc9f4660e1b60be4cb4895e97f2641338b52b6a5e05ac3c7acd85e59b3a  /tmp/rr-a18-stage/2/adaptive-grok-build-pro-v2.0.18.zip
TWO_BUILD_IDENTICAL
MATCHES_TRACKED_BYTES
```

So `INV-002` and `FORBID-002` hold: the archive is reproducible from `fc8d9e6…` alone, from clean non-dirty exact-SHA clones, in `0700` staging. (Side note on the packager: it correctly *refused* my first attempt because this host's default `umask 0002` made the clone dirs group-writable — `PackageError: archive output creation parent grants untrusted rename authority`. That boundary is working, not a defect.)

`source_parent` = `fc8d9e6f11bb188ee514784d3b6f614a6da72803` and `source_parent_tree` = `65d3a996018bf7564866c25b6b869c2493c9e15e`; recomputed `git rev-parse fc8d9e6^{tree}` → `65d3a996018bf7564866c25b6b869c2493c9e15e`. Match. `gh pr view 107` → `headRefOid f8c5021c…`, `mergeCommit.oid fc8d9e6…`, `state MERGED`, `mergedAt 2026-09-16T12:12:11Z`, so the named parent really is the `R` merge, and `git ls-remote origin main` → `fc8d9e6…`, so nothing landed between `R` and `A` (tasks.md:4 premise still true at review time → the tagged tree will be `R` + these two bytes + record/doc/test flips).

`packages/README.md` row is added in the established format and appended last:
`| \`adaptive-grok-build-pro-v2.0.18.zip\` | 2.0.18 (artifact delivered, tag and GitHub Release pending) |` — character-for-character the precedent's v2.0.17 row shape (`git show c86b1a1 -- packages/README.md`), including the "artifact delivered, tag and GitHub Release pending" qualifier rather than a publication claim.

## 2. AC-003 — publication unclaimed — PASS (full null/false set, no drift beyond version identifiers)

Live dump of the tracked `PROJECT_STATE.json`: `published: False`, `published_at: None`, `external_effect: False`, `external_effect_scope: None`, `operational_activation: False`, `checked_head = merge_commit = tree = pull_request = reviewed_product_head = reviewed_product_tree = None`, `artifact_child.commit = artifact_child.tree = None`, and no `tag_object` key exists.

Normalized field-by-field diff against what `c86b1a1` held at its A stage (40-hex → `<SHA>`, 64-hex → `<DIG>`, `2.0.1x`/`v2.0.1x` → `<VER>`/`<VTAG>`, route ids and package slugs masked) — the *only* remaining deltas are:

| Field | Delta vs `c86b1a1` (A of #99) | Judgement |
| --- | --- | --- |
| `status`, `artifact_status` | identical pair `artifact_bytes_delivered` / `pending_tag_and_release` | conformant |
| `published`/`published_at`/`external_effect`/`external_effect_scope`/`operational_activation` | no delta: `false`/`null`/`false`/`null`/`false` | conformant |
| `checked_head`,`merge_commit`,`tree`,`pull_request`,`reviewed_product_head`,`reviewed_product_tree`,`artifact_child.commit`,`artifact_child.tree` | no delta: all `null` | conformant — nothing self-recorded |
| `identity`, `delta_paths`, `source_parent(_tree)`, `zip/sidecar_sha256`, `status`, `predecessor_record`, `change_package`, `branch`, `route_id`, `source_base`, `notes`, `zip_source_note` | values differ only by version/lineage/digest/byte-count; `notes` and `zip_source_note` are the precedent's text with the identifiers replaced | conformant |
| `artifact_child.requirement` | reworded: precedent enumerated "`merge_commit, tree, checked_head` and `pull_request` stay null"; this one says "commit and tree stay null because the child cannot self-record them" | **Minor wording imprecision** (F7): read literally it names only `artifact_child`'s two keys. The sibling `notes` field still states `merge_commit/tree stay null`, and the tests pin all six `local_candidate` self-identities plus `artifact_child.commit/tree` unconditionally, so no field is over-claimed. Fix opportunistically in `SR`. |
| `current_unreleased_change.stage` | identical `artifact_child_delivered_pending_tag` | conformant |
| `current_unreleased_change.artifact_child` | reworded to name the dual-build identity and the SHA instead of pointing at `source_parent` | equivalent, no claim change |
| `current_unreleased_change.next_action`, `active_delivery.next_action` | both advanced to "merge A, then tag, then Release, then SR"; byte-identical to each other (`True`) | **resolves the precedent's F2** |
| `current_unreleased_change.scope[1]` | still "opened local_candidate slot with the artifact pair asserted absent" | historical statement of what `R` did; the precedent A left it identically. Informational only. |
| `local_candidate.status` | `implementing` in `state.json` (precedent stopped at `approved`) | legal transition (`approved → implementing`, `.grok-stack/adaptive_grok/change.py:20`) and more accurate while reviews/PR are open |

## 3. AC-004 — no identity literal moved — PASS

Per-revision comparison `git show fc8d9e6:<p>` vs `git show HEAD:<p>`: `VERSION` (`2.0.18`) and `.grok-stack/adaptive_grok/__init__.py` (`__version__ = "2.0.18"`) are **EQUAL** (whole-file sha256). `README.md:1` `# Adaptive Grok Build Pro v2.0.18` unchanged; `README.md:7` keeps the `Identity: **2.0.18** (candidate, unpublished)` prefix and only the trailing clause changed. `CHANGELOG.md:3` heading `## 2.0.18 — 2026-09-16 (candidate, unpublished)` unchanged (diff hunk `@@ -2,7 +2,7 @@` hits line 5 prose only). `DARK_FACTORY_ROADMAP.md:42` `product version: 2.0.18 candidate (latest published release: v2.0.17; published 2026-09-16T01:17:14Z)` unchanged (ROADMAP diff is one line, `:36`). `tests/test_structure.py` is not in the diff at all (`git diff --stat … -- tests/test_structure.py` empty) and its `:280-287` pins still pass.

## 4. Currency — PASS, all four anchors agree and the external facts re-derive

`observed_main_sha` == `local_candidate.source_base` == `current_unreleased_change.source_base` == `artifact_child.source_parent` == `fc8d9e6f11bb188ee514784d3b6f614a6da72803` == the PR #107 merge == `refs/heads/main`. `runtime_observations.evidence` → `…/f03c54/evidence/runtime-observation-post-107.json`, which exists and whose `source_base` is the same 40-hex; `observed_at`, `runtime_observations.observed_at` and the dossier `observed_at` are all `2026-09-16T12:17:52Z`.

`test_current_epoch_and_app_are_consistent_in_handoff_documents` (`tests/test_project_state.py:671-688`) requires `CURRENT_CHECK`, `str(CURRENT_APP_ID)` and the **full** `observed_main_sha` inside the README "Current state" section and the START_HERE "Current project state" section: `README.md:7,11` and `START_HERE.md:7,9` carry `fc8d9e6f11bb188ee514784d3b6f614a6da72803` plus `adaptive-trust-ci/verified@06ecf1c875bc` / `4694114`; the module is green, so this is test-enforced, not claimed. `DARK_FACTORY_ROADMAP.md:36` `observed source SHA: fc8d9e6… (2026-09-16; PR #107)` matches, and `work_inventory.open_pull_requests` is `[]`, which `gh pr list --state open` confirms.

`trust_ci.last_success` re-derived this session, every field agreeing:

```
$ gh api repos/…/commits/f8c5021c5dabea201cfd273efd55abe3b5893639/check-runs
104782126773  adaptive-trust-ci/verified@06ecf1c875bc  completed  success
$ gh api repos/…/check-runs/104782126773
{"app":4694114,"conclusion":"success","name":"adaptive-trust-ci/verified@06ecf1c875bc","completed":"2026-09-16T12:11:23Z"}
summary: holdout-bundle-integrity: pass · external-holdout: pass · root-unittest: pass
         trust-ci-unittest: pass · compileall: pass · repository-verification: pass
         attestation=46e81300-c8a9-42b2-b899-74dafe1d4e73; signer=0519cf1d47436f2e
```
→ `pull_request 107`, `head_sha f8c5021c…`, `merge_commit fc8d9e6…`, `check_run_id 104782126773`, `attestation_id 46e81300-…`, `conclusion SUCCESS`, `check_url …/runs/104782126773` and the six-command `record_scope` are all exactly what the API returns. This **resolves the precedent's F3**. `last_success` is still a dated observation scoped to "#107 merge authority only"; it is not evidence for merging A.

## 5. Prose — no sentence claims the tag or Release exist; candidate section is correct (one adjacency defect, two same-document contradictions)

`CHANGELOG.md:5` — the rewritten candidate preamble now reads "the artifact child delivered the tracked ZIP+sidecar pair built from the merged release-sync tree. **The tag and GitHub Release do not exist yet**: publication stays a separate step with its own exact delegated authority, and `published` remains false until the successor records it." That is exactly the bytes-in-tree vs publication-pending split, and it *improves* on the precedent, whose A left the older conditional ("reaches a release archive only once the … artifact child is built") false — the precedent's F4. No new CHANGELOG bullet pre-claims the child (the `## 2.0.17` section carries its own `PR #99` row added by that chain's `SR`; `2.0.18`'s row belongs to this chain's `SR`). `README.md:7` and `START_HERE.md:9` state the same split correctly; `packages/README.md:43` still carries the neutralising sentence "Tracked copies live in `packages/`; their presence alone does not claim a tag or GitHub Release." Whole-tree sweeps for `do not exist|asserts their absence|not_built|pending_unpublished_artifact_child|no \`v2.0.18` found **no** sentence anywhere asserting a tag, a Release, `published`, activation or installation.

The two failures are the opposite direction — text that still denies the bytes:

- **F1 (Important)** `GROK_BUILD_HANDOFF.md:303` (next action #1), unchanged, immediately above the line this commit *did* edit: "Product identity `2.0.18` … its ZIP, sidecar, tag and GitHub Release **do not exist**, and each publication step requires its own exact delegated grant." Line 304 now says the child "delivers the ZIP+sidecar pair". Self-contradiction on adjacent lines of the handoff document. Identical class to the precedent's F1 (same document, same partial-edit mechanism, also un-testable: `test_current_epoch…` reads only README and START_HERE sections, never `GROK_BUILD_HANDOFF.md`). Fix in `SR`: "its ZIP and sidecar are tracked bytes delivered by the artifact child; its tag and GitHub Release do not exist yet".
- **F2 (Important)** `START_HERE.md:16`, unchanged, five lines below the corrected `:9`: "`current_unreleased_change` and `local_candidate` describe the `2.0.18` candidate and **assert that its artifact bytes do not exist yet**." Directly false against `artifact_child.status = built_byte_reproducible_twice` and against `START_HERE.md:9` in the same file. This one is inside a document the tests *do* read, but no assertion covers this sentence. Fix in `SR`.

Both under-claim (they deny delivered bytes) rather than over-claim publication, so neither can mislead a tag/Release decision in the unsafe direction; the residual risk is that a zero-context `SR` author re-creates the pair. That is why they are Important, not Critical.

- **F3 (Minor)** route-id drift: authoritative id is `f03c541d184f` (`.grok-stack/runtime/active-route.json:67`, `runtime/routes/f03c541d184f.json`, `runtime/receipts/f03c541d184f/`, and the package's own `route.json:66` + `state.json:30`), but `brief.md:6` and `tasks.md:3` say `f03c541d1848`. The precedent package carried one id everywhere (`31155d4d2a6a` in all four files) — this is drift from precedent in a field the reviewer was asked to watch. Cosmetic (`f03c54` slug matches either way), fix in `SR`.
- **F4 (Minor)** obsolete local-red disclosure, mechanically copied from the precedent: `requirements.md:16`, `test-plan.md:15` and `architecture.md:44` all still assert "the local verifier flags the >10 MB tracked binary it never reads … that is a known local-only red", with a parenthetical "(issues #80/#101 (streaming analysis; the tracked pair now passes the local verifier))" grafted in mid-sentence. Reality now: `gh issue view 80` → **CLOSED**, #101 **MERGED**, the commit message itself states "unlike the v2.0.17 child, the local verifier takes this tree fully because oversized tracked binaries now stream (#101)", and `.grok-stack/runtime/receipts/f03c541d184f/verification.json` is `status: pass` (`mode: pr`, created `2026-09-16T12:36:44Z`) bound to head `497de07` on this clean tree. There is no local red to disclose. Harm is in the safe direction, but the PR body must **not** quote a denial that does not exist and must not use "known red" to justify skipping `grok_verify`. Rewrite the three sentences and drop the graft.
- **F5 (Minor)** `engineering/changes/…968b3c/tasks.md` (the `R` package) still leaves `- [ ] grok_verify --mode pr on the frozen tree, then delivery through a pull request gated on the exact-head App check` unchecked although `R` merged as PR #107 → `fc8d9e6` on check `104782126773` (verified above); `- [ ] After merge: stage A …` is now in flight. The precedent A **ticked the R package's tasks.md in the same commit** (`git show --name-only c86b1a1` lists `…f98796/tasks.md`), so not touching it is drift from precedent. Same class as the precedent's F6.
- **F6 (Minor, pre-existing at base, outside this diff)** `packages/README.md:3` attributes `ZIP SHA-256 71f63a10…` / `sidecar 14e3753a…` to **v2.0.17**, but those are **v2.0.16**'s digests (`prior_published_releases[v2.0.16]`, and `sha256sum packages/…v2.0.16.zip` confirms). Real v2.0.17 is `770f1db5…` / `54db9f64…`, which `published_release.artifact` and the live GitHub release assets both agree on (`gh release view v2.0.17 --json assets` → `"digest":"sha256:770f1db5…"`, `"sha256:54db9f64…"`, `targetCommitish main`, `publishedAt 2026-09-16T01:17:14Z`). Introduced by `cfc4a57` (that chain's `SR`, PR #100); byte-identical at `fc8d9e6` and `HEAD`, so `INV-001` is not violated and this is **not** an A defect — but A edits this file one line below, and a false published-identity claim in the artifact index is worth a one-line `SR` repair.
- **F7 (Minor)** `artifact_child.requirement` imprecision — see the table in §2.
- **F8 (Minor, informational)** `local_candidate.branch` (`feature/v2.0.18-release-sync`), `route_id` (`968b3ce9e148`) and `change_package` (`…968b3c`) deliberately keep the `R` identities while A rides `feature/v2.0.18-artifact-child`, and A's own package appears in `PROJECT_STATE.json` only via `runtime_observations.evidence`. Precedent-identical and test-pinned (`tests/test_project_state.py:379-384`), so this is the intended lineage retention, not staleness. `route.json` again classifies the release/packaging task as `domains: [frontend, api]`, `write_agent: null`; only `required_evidence: [verification, security_review, release_review]` and `review_agents` are load-bearing and both match. No gate is bypassed; a missing `code_review` receipt for this wave is not an omission.

## 6. Tag / Release readiness — independently confirmed unclaimed

```
$ git tag --list 'v2.0.1*' | sort -V | tail -4   -> v2.0.14 v2.0.15 v2.0.16 v2.0.17   (no v2.0.18)
$ gh release list --limit 4                      -> v2.0.17 (Latest) … v2.0.14        (no v2.0.18)
$ gh release view v2.0.18                        -> release not found
$ gh pr list --state open                        -> []
$ git ls-remote origin main refs/heads/feature/v2.0.18*
  f8c5021c…  refs/heads/feature/v2.0.18-release-sync   (R's pre-merge head)
  fc8d9e6f…  refs/heads/main
  (no artifact-child branch pushed; no A pull request exists)
```
No tag object, no Release, no asset, no A PR. Nothing in this wave pre-fills a publication identity: `tag_object` is absent from `local_candidate`, and §2 confirms every self-identity is null. The binding to mirror: v2.0.17's tag targets `c86b1a1` = the protected merge of A's head `bbc5cdd9`, with `SR` = `cfc4a57` (`published_release.artifact` = the same `770f1db5…` bytes that remain tracked today — so the tag/`SR` step must **upload these exact bytes**, not rebuild them).

## 7. Lockstep and test strength — nothing weakened

Four coupled modules: `test_structure` 19 + `test_project_state` 14 + `test_manifest_package` 56 + `test_change_spec` 30 = **119 tests OK** (`Ran 119 tests in 9.153s / OK`; the trailing `/tmp/…/publish/project.zip` + digest lines are scratch output printed by another test, not a failure). The three modules the package names still give `Ran 89 tests … OK`, reproducing `tasks.md:9`.

The two changed test modules were diffed line-by-line against `c86b1a1`'s. Structurally the same shape, and in one place stronger:

| Assertion | Precedent `c86b1a1` | This wave | Verdict |
| --- | --- | --- | --- |
| digest equality | `assertEqual(zip_sha256, "<literal>")`, `assertEqual(sidecar_sha256, "<literal>")` | same two lines, digests replaced | same |
| self-record nulls | `for key in (reviewed_product_head, reviewed_product_tree, checked_head, merge_commit, tree): assertIsNone` + `for key in (commit, tree): assertIsNone` | identical, both loops present and unconditional | same |
| `source_parent` naming | `if artifact_status == "pending_unpublished_artifact_child": assertIsNone(…)` / `else: assertEqual(source_parent, "<lit>")` + tree literal | unreachable `if` arm deleted; now unconditional `assertEqual(source_parent, OBSERVED_MAIN_SHA)` + `assertEqual(source_parent_tree, "65d3a996…")` | **stronger** (the value is pinned, and pinned to the currency constant, so a moved base fails) |
| status pair | `artifact_bytes_delivered` / `pending_tag_and_release` | same | same |
| `zip_source_note` | not asserted | `assertTrue(local["artifact_child"]["zip_source_note"])` added | stronger |
| delivered arm in `test_manifest_package` | one `artifact_status` literal flipped → selects the existence+digest+sidecar-text branch | identical single-line flip (`:1426`) | same |
| `published`/`external_effect`/`operational_activation` false, `published_at`/`external_effect_scope` null | asserted | asserted (`test_project_state.py:387-393`) | same, unchanged context |

`grep -rn "not_built\|pending_release\|pending_unpublished_artifact_child\|d146ca4\|7bbf425" tests/*.py` returns exactly **one** hit — the still-needed pre-delivery arm guard at `tests/test_manifest_package.py:1435` — so no invalidated literal survives anywhere in the suite (the precedent's second guard in `test_project_state.py` was correctly deleted rather than left dangling). A separate sweep for the stale day pin `2026-09-15T` finds only the historical `closed_at` of PR #15 inside a pinned `work_inventory` literal (`tests/test_project_state.py:826`), which is correct to leave. The day-scoped `observed_at` regex needed no move (`12:17:52Z` is still `^2026-09-16T…`) — correct, not an omission; note it will fail on the next calendar day if the chain slips past midnight.

**Would the delivered assertion actually fail on bad bytes?** Proved, not reasoned — I extracted the assertion block verbatim and ran it against a `/tmp` copy under four mutations (repo untouched):

```
baseline           -> PASS
tamper-zip         -> FAILS: zip digest 2d711642… != recorded
missing-zip        -> FAILS: existence (count != 2)
tamper-sidecar     -> FAILS: sidecar text
one-space-sidecar  -> FAILS: sidecar text   (precedent did not probe this case)
```
Because the sidecar text is compared against the **recomputed** digest plus the derived member name with exactly two spaces, the candidate sidecar's bytes are fully pinned transitively; the recorded `sidecar_sha256` is additionally pinned to a test literal and I verified it equals the tracked blob. No drift channel.

`INV-001` verified mechanically, not by eye: comparing the parsed JSON of `PROJECT_STATE.json` at `fc8d9e6` vs `HEAD`, the only top-level keys that differ are `observed_at`, `observed_main_sha`, `current_unreleased_change`, `local_candidate`, `active_delivery`, `l5_production_preparation`, `runtime_observations` and `trust_ci.last_success`. `published_release`, `prior_published_releases`, `milestones`, `work_inventory`, `operational_qualification`, `delivered_non_milestone_work`, `governance` and **every** `delivered_change_history` subkey (including `post_v2_0_17_landing` and the verbatim archived v2.0.17 `published_local_candidate`) are equal. `delta_paths` lists exactly the two `packages/` files and `git ls-tree --name-only fc8d9e6 packages/ | grep -c '2\.0\.18'` → `0`, so A is the sole owner of the pair; read as the artifact delta (precedent semantics), not the commit's full path list.

## 8. Rollback credibility (records + bytes, `forward_fix ≤ 2`) — credible

`git revert` of A's merge removes two tracked files and flips `local_candidate`/currency/`trust_ci.last_success`/the two test modules back as a unit — the reverted tests pin the pre-delivery form (`assertIsNone(zip_sha256)`, `artifact_status == pending_unpublished_artifact_child`, non-existence `== ()`), so the revert lands green rather than half-reverted. Verified there is nothing else to unwind:

- `git diff --name-only fc8d9e6..HEAD` filtered to non-`engineering|packages|tests|the six top docs` → **empty**: no `scripts/`, no `.grok-stack/adaptive_grok/` code, no packaging logic, no migrations, no `governance/`, no architecture model change. The only `/opt` string in the whole diff is the read-only `control_repository` path inside the observation dossier.
- The dossier's own `observation_provenance.method` is `systemctl show -p MainPID -p Id -p ActiveState -p UnitFileState … read-only, unprivileged`, with `unchanged_since_previous.primary_main_pid=698333` / `secondary_main_pid=3597736` identical to the post-106 dossier, i.e. no reinstall, restart or activation. `external_effect: false`, `operational_activation: false`, `source_defaults.live_enabled: false`, `limits` state no new provider call. `rollback.md` names PostgreSQL 001-018 untouched, and `frozen.postgresql_migrations` is unchanged.
- No published byte is touched: `packages/…v2.0.17.zip` still hashes `770f1db5…` and `published_release` is byte-equal to base, so a revert cannot damage a released artifact.
- `rollback.md` verification is executable and correct (`git ls-files packages/ | grep -c 2.0.18` → 0 after revert, `git tag --list 'v2.0.1*'` ends at `v2.0.17`, which I confirmed live). Its "fix forward rather than move or delete `v2.0.18`" clause is right, and `change-spec.yaml` `rollback.maximum_steps: 2` covers revert + re-deliver.

## 9. Doctrine conformance

Tag and GitHub Release are **not** created and no local record claims authority for them: `next_action` (both copies), `tag_and_release`, `artifact_child.requirement` and `notes` all state that each publication step needs its own exact delegated grant bound to the merged commit, and `release.md:7` repeats the HEAD/tree/TTL binding and the "no grant reuse after a tree change" rule. `AGENTS.md`'s "no GitHub Actions" is unaffected (`.github/workflows/` still absent), and `PROJECT_STATE.json`/`START_HERE.md:16` keep the chain-commit convention (`R`/`A` commits are recorded through `current_unreleased_change`/`local_candidate`, not as landing rows) — the 2.0.18 CHANGELOG section correctly lists only #101/#102/#105/#106.

One sequencing note the parent should carry, because it is the only place this wave departs from precedent process: the precedent A committed its `review-security.md` / `review-response.md` / `review-release.md` **inside** `c86b1a1` and ticked `tasks.md:10`; this A is being reviewed before any report exists in the package, so any of these reports (including this one) is a tracked write that re-fingerprints the tree and voids the existing `verification` receipt. Do not let that push a rewrite of the bytes: the digest pair, `packages/README.md` row and `delta_paths` must stay byte-identical. Recommended order — land the report files as a second commit on the A branch (or amend before the first push), then run `grok_verify --mode pr` on that final head and record `verification` + `security_review` + `release_review` against **that** fingerprint, then open/merge the PR and tag the exact merged commit.

## SR checklist (what this commit correctly leaves undone)

`SR` must set and must **not** be pre-filled here: `local_candidate.published=true`, `published_at`, `merge_commit` (A's protected merge), `tree`, `checked_head` (A head), `pull_request` (A's number), `reviewed_product_head`/`reviewed_product_tree`, `external_effect=true` + `external_effect_scope`, `artifact_child.commit`/`artifact_child.tree`, the annotated tag object SHA and its target, the Release/asset identities re-derived with `gh release view v2.0.18 --json tagName,assets,digests,publishedAt,targetCommitish`, `trust_ci.last_success` advanced to A's exact-head run, `current_unreleased_change` closure, both `next_action` fields, `active_delivery`, the verbatim `local_candidate` archive into `delivered_change_history`, the `2.0.18` CHANGELOG row and `packages/README.md` v2.0.18 row → published, plus `operational_activation` **still false**. Fix F1-F6 there (F6 is a one-line published-digest correction; F7 optionally). `SR` must also tick both packages' task rows and re-check `gh pr list --state open`.

## Limits

- Read-only review: no merge, no publish, no tag, no push, no install, no restart, no external write, no local receipt written, no credential store, `.env`, key or approval material read (and none needed — the packager's exclusion is what makes the archive publishable).
- `grok_verify --mode pr` was **not** re-run by me; the `verification` receipt (`status: pass`, `mode: pr`, created `2026-09-16T12:36:44Z`, bound to head `497de07` on a then-clean tree) is reported as existing evidence and will be voided by writing this file. Re-run on the final head.
- `security_review` was not performed here; `FORBID-002` secret-exclusion is my own membership scan of the archive plus the reproduction, not a substitute for that receipt.
- `attestation_id` and the six-command list were verified from the check run's `output.summary` text; I did not (and cannot) re-verify the App's signing key, deployed policy, holdout bundle or PostgreSQL state — those live outside the PR trust domain.
- The dual-build reproduction used the local `adaptive-grok-build-pro` object store as the clone origin. That is the same content GitHub serves for `fc8d9e6` (its commit and tree ids match the remote main tip), but it is not a network-fetched clone.
- `predecessors`, `post_v2_0_17_landing`, the runbook and `l5_production_preparation` internals were checked for equality against the base and spot-checked against Git; they are `R`'s responsibility, not this wave's.
- Findings F1-F6 are documentation/record currency. None of them changes the archive, its digests, the record's null/false set, or the App-owned check's role as the only merge authority.
