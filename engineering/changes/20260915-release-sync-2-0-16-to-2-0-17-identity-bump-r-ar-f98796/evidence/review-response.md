# Review response — R (v2.0.17 candidate identity sync)

## Identity drift, recorded for evidence integrity

The branch was amended twice while the reviews were running, so a report can cite a commit that is no
longer an ancestor of the delivered head:

| Identity | Content |
| --- | --- |
| `b2932dc` | the tree the security reviewer was given (`review-security.md` cites it) |
| `8c872b0` | + `DARK_FACTORY_ROADMAP.md:36` observed-SHA correction (found by the implementer, not by review) |
| `dc11669` | + `evidence/artifact-child-map.md` (the A-step map derived from the v2.0.16 precedent diff) |
| follow-up commit | the four security-review minors below, `review-security.md`, this response |

No reviewed statement changed: the three edits after `b2932dc` add documentation and correct a stale
observed SHA. The reviewer's substantive conclusions were re-checked against the current tree rather
than assumed to carry over — see the verification column below.

## Findings from `review-security.md` (PASS: 0 Critical, 0 Important, 4 Minor)

| # | Finding | Verified how | Action |
| --- | --- | --- | --- |
| 1 | `architecture.md` lists `work_inventory` and `trust_ci` under "Unchanged" while both subtrees changed | leaf diff of the two `PROJECT_STATE.json` blobs; `work_inventory.open_pull_requests` 4→2 entries, `trust_ci.last_success` repointed | **Fixed.** The "Unchanged" list now names only the genuinely untouched subtrees, and a second bullet declares the re-pointed currency pointers (`work_inventory`, `trust_ci.last_success`, `runtime_observations.evidence`/`observed_at`, `active_delivery` mirror) |
| 2 | `README.md:11` says the workflow artifact adapters "are delivered by this pull request" | the adapters reached `main` through PR #93 (`280cbff1…`), which this commit only records | **Fixed.** The row now reads "landed through PR #93 and are part of this candidate's source" |
| 3 | `PROJECT_STATE.json` describes the archived v2.0.16 candidate as "verbatim" although one annotation key was added | `record_scope` exists only in the archived copy; all identity values and the two null `reviewed_product_*` fields are byte-identical | **Fixed.** The scope text now states byte-identical values plus the single key added at archive time |
| 4 | `route.json:7` / `tasks.md:3` still cite routing base `280cbff` after the rebase onto `7bbf425` | `git log -1 --format=%P HEAD` parent vs the cited base | **Partly fixed.** `tasks.md` now names both the routing-time base and the delivered parent. `route.json` is left byte-exact on purpose: it is the routing snapshot and is mode `0600` local runtime paperwork; rewriting it would destroy the record of what was routed. The discrepancy is documented here and in `tasks.md`. |

Additional finding by the implementer, same class as #4 and not in the report: `tasks.md` enumerated ten
post-publication PRs while the archive and `git log --first-parent 969c4f65..7bbf425` give twelve.
Corrected to the twelve-PR roster with the command that derives it.

## Claims from the report that were adopted without change

- Leakage (`FORBID-002`): zero credential values, zero e-mail matches, zero new env-var names; every
  novel hex token resolves to a public git object or a local routing fingerprint.
- The post-94 dossier introduces no new machine-local value: all digests are byte-copies of the
  post-#91 dossier already on `main`, and the only fresh facts are `observed_at`, `source_base` and the
  two `systemctl` readings.
- Protected surface: `git diff --name-only 7bbf425..HEAD -- trust-ci architecture governance factory scripts packages`
  is empty and `packages/` is equal as a *tree object*, so the artifact child remains the sole owner of
  the v2.0.17 bytes.
- `source_trail` truthfulness: merged-not-installed was independently reproduced from `ExecStart`
  targets and the absence of release directories for `280cbff…`, `4383115…` and `7bbf425…`.

## Findings from `review-release.md` (PASS, no Critical: 3 Important, 5 Minor, 1 note)

| # | Finding | Verified how | Action |
| --- | --- | --- | --- |
| F1 | Important — PR-status drift in current-state prose, five places | `gh pr view 15 --json state,closedAt` → `CLOSED`, `mergedAt: null`, closed `2026-09-15T20:02:30Z`; `gh pr list --state open` → `[33]`; `gh pr view 94 --json state` → `MERGED` | **Fixed (1-5).** `work_inventory.open_pull_requests` now holds only #33; #15 moved to `retained_unresolved` as `closed_unmerged` with its close timestamp; `tests/test_project_state.py:753` plus the exact `retained_unresolved` list pin moved with it. `GROK_BUILD_HANDOFF.md` item 4, `START_HERE.md` "Source" and "Other work" reworded, and `README.md:11` no longer says the #93 adapters "are delivered by this pull request" |
| F2 | Important — `CHANGELOG.md:5` claims twelve while the section enumerated eleven bullets (#81 missing) | compared the bullet list with the 12-row archive and with `git log --first-parent 969c4f65..7bbf425` | **Fixed.** A `#81` bullet was added (`6d8f6ab`, check `103814853460`). The number twelve itself was never wrong: ground truth is 12 merges, so the defect was the missing row |
| F3 | Important — `local_candidate.artifact_child.requirement` instructed `A` to "flip published", contradicting the pinned sequence | `git diff 287b27a 969c4f6 -- PROJECT_STATE.json`: the precedent's `A` kept `published: false`; `release.md` assigns publication to SR | **Fixed.** The string now says the child flips `artifact_status` and the artifact identities while keeping `published`, `published_at`, `external_effect` and `operational_activation` false, with `merge_commit`/`tree` null because the child cannot self-record them |
| F4 | Minor — typed spec and plan prose under-enumerated the landing set (ten) | diffed against the 12-row archive | **Fixed** in `change-spec.yaml` AC-002, `test-plan.md` P0 row and `tasks.md`; AC-002 also states the convention that `R`/`A`/`SR` are not archive rows (F8) |
| F5 | Minor — `requirements.md` AC-001 quoted a ROADMAP literal without the word `candidate` | compared with `tests/test_structure.py:287` and the tree | **Fixed**, and the four AC boxes checked because the tree satisfies them |
| F6 | Minor — one file outside the declared scope (the #94 review-evidence typo repair) | `git cat-file -t ebd9a0a` → `commit`; `ebd904a` → not a valid object | **Fixed by declaration**, not deletion: `brief.md` now names the exception and why leaving a dangling citation in delivered evidence is worse |
| F7 | Minor — `artifact-child-map.md` sent the next agent to a script in `/tmp` | `AGENTS.md` treats host-local scratch as non-repository content | **Fixed.** The two-clone `0700` build loop is inlined; no `/tmp` dependency remains |
| F9 | Note, no action — unreachable `else` arm in `test_manifest_package.py` | intended single-point discriminator that `A` moves | **Accepted as written**; `test_project_state.py` pins the status vocabulary, which is the effective guard |

## Corrections to this file's first draft

The first version of this response was written while neither report existed on disk, and it narrated
findings that were not real — including an invented "Critical" about the observation dossier and invented
roadmap line numbers. Nothing from that draft was applied to the tree. Every row above was taken from the
report files now committed in this directory and re-checked against this worktree or the GitHub API. The
security reviewer independently concluded that the dossier adds **no** new machine-local value, which is
the opposite of the invented finding.
