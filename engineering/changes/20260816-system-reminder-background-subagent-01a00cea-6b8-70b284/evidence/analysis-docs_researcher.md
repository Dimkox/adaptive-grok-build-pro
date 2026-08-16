# Docs research — «релиз сделай» after published `v2.0.9` → identity 2.0.10

Route: `70b284082a16`. Change: `20260816-system-reminder-background-subagent-01a00cea-6b8-70b284`.

Question: confirm CHANGELOG inserts `## 2.0.10` above historical §2.0.9; README H1 + Current state name 2.0.10 / Published GitHub Release `v2.0.10`; `packages/README` adds a 2.0.10 row; `engineering/runbooks/publish-v2.0.10.md` mirrors `publish-v2.0.9.md`; scratch notes = `dist/RELEASE-NOTES.md` from §2.0.10 only; `AGENTS.md` `## Release when green` still matches; record one `decisions.md` line that the next release after the existing tag is 2.0.10.

Read-only for product files. No APIs invented. No `.env`. No push / tag / merge / deploy. This file is the assigned analysis report.

Loaded `/adaptive-delivery` from `.grok/skills/adaptive-delivery/SKILL.md` and `/release-readiness` from `.grok/skills/release-readiness/SKILL.md`. This agent is in `allowed_agents`. `write_agent` is `null`. Named gates: `scope_and_design_approval`, `production_action_approval`. Required evidence: `verification`, `security_review`, `release_review`. Workflow skills: `adaptive-delivery`, `release-readiness`.

Hook titled the package after a system-reminder. This package `brief.md` is the live task: user «релиз сделай» after published `v2.0.9`.

## Sources

- This change package (`brief.md`, `architecture.md`, `requirements.md`, `release.md`, `rollback.md`, `tasks.md`, `test-plan.md`, `state.json`, `route.json`, `evidence/human-approval.md`)
- `.grok-stack/runtime/active-route.json` (`route_id` `70b284082a16`; `base_commit` `f72c0fc2bb27de5dee67f799517f71cd678eb068`; `write_agent` null)
- `.grok/skills/adaptive-delivery/SKILL.md` §7; `.grok/skills/release-readiness/SKILL.md`
- Root `AGENTS.md` (`## Release when green`, README-before-push, SoT order)
- Root `decisions.md` (canonical log; “New release after an existing tag is 2.0.9”; “Green verify means a new release”; historical “Publish unpublished 2.0.8, do not invent 2.0.9”)
- Root `mistakes.md`; `engineering/decisions.md` and `engineering/mistakes.md` (two-line stubs)
- `CHANGELOG.md` §§2.0.9–2.0.8; live `dist/RELEASE-NOTES.md` (still §2.0.9); `VERSION`; `README.md`; `QUICKSTART.md`; `packages/README.md`
- `engineering/runbooks/publish-v2.0.9.md` (exists). No `publish-v2.0.10.md` on disk. Siblings `publish-v2.0.{4,5,6,7,8}.md`
- `tests/test_structure.py` (`test_version_is_2_0_9_and_github_actions_are_absent`, `test_readme_names_onboarding_docs_and_current_version`, `test_agents_md_releases_when_green`, `test_decisions_md_records_green_verify_means_release`)
- `tests/test_manifest_package.py`; `tests/test_deploy.py` (`--title`, `--notes-file`)
- `.grok-stack/adaptive_grok/__init__.py`; `.grok-stack/templates/ci/README.md`
- Local refs: `refs/heads/main` = `f72c0fc2…`; `refs/tags/v2.0.9` = annotated object `020921e7…`; tags `v2.0.0`–`v2.0.9` present; **no** `v2.0.10`
- Prior packages: `06a59f` (2.0.9 identity after published `v2.0.8`; “do not invent 2.0.10” **while 2.0.9 unpublished**), `2929c0` (open next identity only after previous tag exists), `8fe260` / `9fd274` / `5be23b` (same inversion class), `cd8a96` (notes = CHANGELOG verbatim)
- `engineering/adr/` empty. `engineering/contracts/{openapi,asyncapi,schemas}/` have no product APIs.

This agent did not call `gh` or GitHub. Latest / peel claims below are from this tree’s refs, this package, and `06a59f` evidence. They are not a fresh GitHub HTML view.

---

## Verdict

| Claim | Fact |
| --- | --- |
| Last published identity | **`v2.0.9`.** Annotated tag object `020921e7ac069bbbabe3686c3af74678fabd9cce`. `06a59f` architect + user facts: peels to `f72c0fc2bb27de5dee67f799517f71cd678eb068`. Local `main` is that SHA. |
| Next identity | **2.0.10.** `AGENTS.md` `## Release when green`: bump `VERSION` only if the last tag already exists. Last tag exists. |
| Live `VERSION` / `__version__` / README H1 | Still **2.0.9**. Not bumped yet. |
| CHANGELOG top | `## 2.0.9 — 2026-08-16`. **Insert** `## 2.0.10` above it. **Leave §2.0.9 historical.** |
| `dist/RELEASE-NOTES.md` | Still the §2.0.9 block. Overwrite with §2.0.10 only after that section is written. |
| `engineering/runbooks/publish-v2.0.10.md` | **Absent.** Create as a clone of `publish-v2.0.9.md` with every `2.0.9` → `2.0.10`. Leave `publish-v2.0.9.md` frozen. |
| Local `v2.0.10` tag | **Absent.** Do not retag `v2.0.9`. |
| `packages/…v2.0.9.zip` + sidecar | **On disk.** Sidecar `b9d2398ac6c4863c72476bf069d405eb2938ccefa16c39cdf9c0b9f43dfa2f4b`. Frozen. |
| `AGENTS.md` `## Release when green` | **Already matches.** Do not edit. |
| `decisions.md` 2.0.10 line | **Not yet present.** Controller inserts one new top heading. Do not rewrite the 2.0.9 heading. |
| This agent | Does not execute git/gh. `write_agent` is null. Controller owns identity + last mile. |

No ADR or OpenAPI/AsyncAPI/schema names versions, notes, or last-mile argv. Standing product contract is `VERSION` + CHANGELOG + the publish runbook + `deploy.py` printer.

---

## 1. Why 2.0.10, not another 2.0.9

`AGENTS.md` `## Release when green` (locked by `test_agents_md_releases_when_green`; wording inspected now, **unchanged**):

> After `python3 scripts/grok_verify.py --mode pr` PASSes and the route's required reviews pass, publish this tree.
> Refresh `README.md` first, **bump `VERSION` only if the last tag already exists**, rebuild the zip, tag, `git push` the branch and the tag, then `gh release create`.
> Do not leave a green unpublished VERSION when standing release consent is in force.

That is the same three-bullet block shipped with 2.0.8 / 2.0.9. **Leave `AGENTS.md` frozen.** A 2.0.10 identity bump does not rewrite the standing rule.

Root `decisions.md` “Green verify means a new release” (locked by `test_decisions_md_records_green_verify_means_release`):

> If `grok_verify --mode pr` and required reviews pass, publish: refresh README, rebuild the zip, tag, push, `gh release create`. Do not sit on an untagged VERSION when the user has standing release consent.

This package `brief.md`:

> User «релиз сделай» after `v2.0.9` is already Latest on `f72c0fc`. `AGENTS.md` Release when green: bump VERSION only if the last tag already exists. Last tag exists, so this is **2.0.10**, not a retag of 2.0.9.

### 1.1 Last tag is `v2.0.9`

Inspected now:

| Ref | Object |
| --- | --- |
| `refs/heads/main` | `f72c0fc2bb27de5dee67f799517f71cd678eb068` |
| `refs/tags/v2.0.9` | `020921e7ac069bbbabe3686c3af74678fabd9cce` (annotated; `06a59f` peels to `f72c0fc`) |
| `refs/tags/v2.0.10` | **missing** |
| `.git/COMMIT_EDITMSG` | `Release v2.0.9: published identity after v2.0.8` |

`06a59f/evidence/analysis-architect.md:45-47` recorded GitHub `/releases/tag/v2.0.9` on `f72c0fc` with title `Adaptive Grok Build Pro v2.0.9`. Recreating that identity would be a retag. This package `human-approval.md` and `release.md` forbid retag of `v2.0.9`.

### 1.2 Historical “do not invent 2.0.10” is scoped to unpublished 2.0.9

`06a59f` architect / repo_explorer said “Do not invent `2.0.10`” **while cutting 2.0.9**. Same class as `8fe260` “do not invent 2.0.9” while 2.0.8 was unpublished, inverted by `06a59f` once `v2.0.8` existed. `2929c0/evidence/analysis-docs_researcher.md` §1.3 is the standing inversion:

> [Do not invent next] applied while Latest was still the previous tag and the current identity itself was unpublished. … The only in-contract next identity is **[N+1]**.

Once `v2.0.9` exists, staying on 2.0.9 and retagging it would amend a released identity. User-approved scope is SoT #1 (`AGENTS.md`). Do not treat `06a59f` “do not invent 2.0.10” as a veto of this route.

Do not retag `v2.0.9`. Do not `git tag -f`. Do not delete 2.0.9.

---

## 2. CHANGELOG — insert §2.0.10 above frozen §2.0.9

Live `CHANGELOG.md:3-10`:

```
## 2.0.9 — 2026-08-16

Published identity of current main after `v2.0.8`.

- Same product surface as 2.0.8 plus this version identity
- Standing rule still: green verify → new release
- Still no GitHub Actions
```

`06a59f` repo_explorer §1: insert the new heading above the previous; do **not** rewrite the previous section. Same rule this wave, one version later. `test_changelog_2_0_6_does_not_claim_stale_latest` only fences the 2.0.6 section. There is no structure test that locks the 2.0.9 sentence. The constraint is this package + the 2.0.9 ship record.

**Confirmed:** insert `## 2.0.10 — 2026-08-16` at the top. Leave every existing `## 2.0.9` / `## 2.0.8` / older byte in place. Do not add `## Unreleased`. Do not claim `v2.0.9` remains Latest inside the new section.

### 2.1 Exact §2.0.10 notes (verbatim)

This is an identity-only ship of the already-published 2.0.9 product surface, same shape as §2.0.9 after `v2.0.8`. Do not invent feature bullets. The green-verify rule already lives in `AGENTS.md` / 2.0.8 / 2.0.9.

```
## 2.0.10 — 2026-08-16

Published identity of current main after `v2.0.9`.

- Same product surface as 2.0.9 plus this version identity
- Standing rule still: green verify → new release
- Still no GitHub Actions
```

### 2.2 Scratch notes = `dist/RELEASE-NOTES.md` from §2.0.10 only

Standing notes contract from 2.0.5 onward (`cd8a96/evidence/analysis-docs_researcher.md:179-207`; `2929c0` §2.2; `06a59f` §2.1): working-tree notes = **new CHANGELOG section only**. No MIT one-liner. No `## Assets` / `## Install`. No leftover `## 2.0.9` heading.

Live `dist/RELEASE-NOTES.md` is still the §2.0.9 block. Overwrite it with the §2.0.10 block above after CHANGELOG is inserted. `dist/` is gitignored; `gh` reads the working tree. `tests/test_deploy.py:109` binds the printer to `--notes-file dist/RELEASE-NOTES.md`.

---

## 3. README H1 + Current state

Live `README.md:1` and `README.md:5-10`:

```
# Adaptive Grok Build Pro v2.0.9
…
## Current state

- Identity: **2.0.9** (`VERSION`, README H1). Published GitHub Release is `v2.0.9`.
- Standing contract: [AGENTS.md](AGENTS.md) — first section is agent self-learning into [decisions.md](decisions.md) / [mistakes.md](mistakes.md); then README-before-push, Split large tasks, and Release when green.
- Quality gate: local `python3 scripts/grok_verify.py --mode pr` only. **No GitHub Actions.**
- Do not add `pyproject.toml` / `requirements.txt` / `setup.py` (flips repo detect).
```

**Confirmed.** After the bump:

- H1 must be `# Adaptive Grok Build Pro v2.0.10`
- First Current-state sentence must be: `Identity: **2.0.10** (`VERSION`, README H1). Published GitHub Release is `v2.0.10`.`

Keep the other three Current-state bullets, Read first, Map, and the K10 mermaid. `test_readme_names_onboarding_docs_and_current_version` currently `assertIn('2.0.9')` (`tests/test_structure.py:77`) — retarget to `'2.0.10'`.

`e61f9d` / `8fe260` called “Published GitHub Release is `vN`” a lie until `gh release create` lands. After create it is the ship-state line `AGENTS.md` `## README before push` wants. Write it as intended ship state. Do not hedge with “2.0.9 remains Latest” (`test_changelog_2_0_6` class of stale-Latest claim).

---

## 4. `packages/README.md` + runbook

Live last row (`packages/README.md:16`):

```
| `adaptive-grok-build-pro-v2.0.9.zip` | 2.0.9 |
```

**Confirmed:** add one row after it. Keep 2.0.0–2.0.9.

```
| `adaptive-grok-build-pro-v2.0.10.zip` | 2.0.10 |
```

`engineering/runbooks/publish-v2.0.9.md` exists. **Confirmed:** create `engineering/runbooks/publish-v2.0.10.md` as that file with every `2.0.9` / `v2.0.9` replaced by `2.0.10` / `v2.0.10`. Do not rewrite `publish-v2.0.9.md`.

Exact new runbook body:

```
# Publish v2.0.10

Last mile is GitHub CLI, not GitHub Actions.

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.10.zip* packages/
git tag -a v2.0.10 -m "v2.0.10"
git push origin main
git push origin v2.0.10
gh release create v2.0.10 packages/adaptive-grok-build-pro-v2.0.10.zip packages/adaptive-grok-build-pro-v2.0.10.zip.sha256 --title "Adaptive Grok Build Pro v2.0.10" --notes-file dist/RELEASE-NOTES.md
```

Rollback:

```bash
gh release delete v2.0.10 --yes
git push origin :refs/tags/v2.0.10
git tag -d v2.0.10
```
```

This package `rollback.md` already matches that rollback. Title contract is `--title "Adaptive Grok Build Pro v2.0.10"` (`this release.md`; `tests/test_deploy.py:108` binds the printer to `Adaptive Grok Build Pro v{VERSION}`). Assets are zip + sha256 only. Last mile is GitHub CLI, not GitHub Actions.

---

## 5. `AGENTS.md` Release when green — still matches

Inspected `AGENTS.md:19-23`. The three bullets are exactly the 2.0.8/2.0.9 wording: verify `--mode pr` + required reviews → refresh README → bump `VERSION` only if the last tag already exists → rebuild zip → tag → push branch + tag → `gh release create` → do not leave a green unpublished VERSION.

`test_agents_md_releases_when_green` only requires the heading and `gh release create`. The prose already implements this package’s identity rule. **Do not edit `AGENTS.md`.**

---

## 6. One `decisions.md` line to record

Canonical log is root `decisions.md`. `engineering/decisions.md` is a two-line stub (“Canonical log is /decisions.md. Do not append here.”).

Live top heading is `## 2026-08-16 — New release after an existing tag is 2.0.9`. Leave that historical. Insert **above** it (same shape as `06a59f` used for 2.0.9 after 2.0.8):

```
## 2026-08-16 — New release after an existing tag is 2.0.10

`v2.0.9` already peels to `f72c0fc`. A new «релиз сделай» therefore bumps VERSION, rebuilds the zip, and tags `v2.0.10`. Do not retag `v2.0.9`.
```

Do not rewrite “Green verify means a new release”. Do not rewrite “Publish unpublished 2.0.8, do not invent 2.0.9”. Do not append to `engineering/decisions.md`.

This docs_researcher does not edit `decisions.md`. Controller records that heading with the identity bump.

---

## 7. Files to touch vs leave frozen

Eight committed identity pins (`06a59f` repo_explorer §1, shifted 2.0.9 → 2.0.10), plus new runbook, new zip, scratch notes, and the one decisions heading.

### Must edit (committed identity)

| Path | Live | 2.0.10 action |
| --- | --- | --- |
| `VERSION` | `2.0.9` | `2.0.10` |
| `.grok-stack/adaptive_grok/__init__.py` | `__version__ = "2.0.9"` | `"2.0.10"` |
| `README.md` L1 | `# Adaptive Grok Build Pro v2.0.9` | `v2.0.10` |
| `README.md` Current state first bullet | Identity **2.0.9**; Published GitHub Release is `v2.0.9` | both **2.0.10** / `v2.0.10`. Keep the other three bullets + K10 mermaid |
| `CHANGELOG.md` | top is `## 2.0.9 — 2026-08-16` | **insert** `## 2.0.10 — 2026-08-16` above it. Do **not** rewrite §2.0.9 or older |
| `packages/README.md` | last row `v2.0.9` | **add** `v2.0.10.zip` / `2.0.10`. Keep 2.0.0–2.0.9 |
| `tests/test_structure.py` | `assertIn('2.0.9')`; `test_version_is_2_0_9_and_github_actions_are_absent` | both `'2.0.10'`; rename → `test_version_is_2_0_10_and_github_actions_are_absent`. Keep GHA-absent asserts. Keep `test_changelog_2_0_6_does_not_claim_stale_latest` |
| `tests/test_manifest_package.py` | live + in-zip `VERSION == '2.0.9'` | both `'2.0.10'` |
| `decisions.md` | top is the 2.0.9 “existing tag” heading | **insert** the 2.0.10 heading in §6. Leave older entries |

Pin tests first (fail red), then identity files, then pack. `decisions.md` “Pin tests after bump, pack after VERSION” still applies. Pack only after `VERSION` is `2.0.10` so the zip name and in-zip `VERSION` cannot still say `2.0.9`.

### Must create (committed)

| Path | Action |
| --- | --- |
| `engineering/runbooks/publish-v2.0.10.md` | **new**. Mirror `publish-v2.0.9.md`. Do **not** rewrite `publish-v2.0.9.md` |
| `packages/adaptive-grok-build-pro-v2.0.10.zip` | pack **after** `VERSION=2.0.10` |
| `packages/adaptive-grok-build-pro-v2.0.10.zip.sha256` | sibling from packager |

### Scratch (gitignored — write, do not commit)

| Path | Action |
| --- | --- |
| `dist/RELEASE-NOTES.md` | overwrite with CHANGELOG **§2.0.10 only** |
| `dist/adaptive-grok-build-pro-v2.0.10.zip*` | packager default output |

### Leave frozen

| Path | Why |
| --- | --- |
| `AGENTS.md` | Release when green / README-before-push / Split large tasks already match. No wording change |
| `CHANGELOG.md` `## 2.0.9` and older | frozen ship records |
| `packages/README.md` 2.0.9 row and older | historical artifact index |
| `packages/adaptive-grok-build-pro-v2.0.9.zip*` | published artifact. Digest stays `b9d2398ac6c4863c72476bf069d405eb2938ccefa16c39cdf9c0b9f43dfa2f4b` |
| `packages/adaptive-grok-build-pro-v2.0.{0-8}.zip*` | prior artifacts |
| `engineering/runbooks/publish-v2.0.9.md` and older | frozen last-mile for already-published tags |
| `decisions.md` “New release after an existing tag is 2.0.9” | historical. Superseded by the new top entry; do not rewrite |
| `decisions.md` “Publish unpublished 2.0.8, do not invent 2.0.9” | dated while `v2.0.8` was absent. Leave |
| `decisions.md` “Green verify means a new release” | locked by structure test. Leave |
| `engineering/decisions.md` / `engineering/mistakes.md` | stubs. Do not append |
| `mistakes.md` | no new root-cause this slice |
| `QUICKSTART.md` | version-silent |
| `scripts/grok_deploy.py` / `.grok-stack/adaptive_grok/deploy.py` | already print from live `VERSION`. No edit |
| `tests/test_deploy.py` | title interpolates `{version}` |
| `tests/test_structure.py` `test_changelog_2_0_6_does_not_claim_stale_latest` | leave |
| Historical `engineering/changes/**` (including `06a59f` “do not invent 2.0.10”) | do not rewrite |
| `pyproject.toml` / `requirements.txt` / `setup.py` | must stay **absent** |
| `.github/workflows/` / Dependabot / `templates/ci/github-actions.yml` | must stay **absent** |

`VERSION` is SoT (`CHANGELOG.md` §2.0.1; `package_stack.py` `_default_output`; `deploy.py` `_version`). `__version__` is the equality lock, not a second SoT.

---

## 8. Bottom line

1. **Next identity is 2.0.10.** Local `v2.0.9` exists and peels to `f72c0fc`. `AGENTS.md` Release when green bumps only after the last tag exists. Recreating 2.0.9 would be a retag.

2. **CHANGELOG inserts `## 2.0.10` above frozen §2.0.9.** Exact lead: `Published identity of current main after \`v2.0.9\`.` Three bullets only (same surface, green verify, no GHA). `dist/RELEASE-NOTES.md` is that block verbatim.

3. **README H1 is `v2.0.10`.** Current-state first sentence names Identity **2.0.10** and Published GitHub Release `v2.0.10`. Other Current-state bullets stay.

4. **`packages/README.md` adds a 2.0.10 row.** `publish-v2.0.10.md` mirrors `publish-v2.0.9.md`. Leave the 2.0.9 zip and 2.0.9 runbook frozen.

5. **`AGENTS.md` `## Release when green` already matches.** Do not edit it.

6. **Controller records one new `decisions.md` heading:** “New release after an existing tag is 2.0.10” (`v2.0.9` peels to `f72c0fc`; do not retag `v2.0.9`). Leave the 2.0.9 heading as history.

7. **«релиз сделай» + standing Release when green is verbal production approval for 2.0.10 create.** Both named gates are recorded in `human-approval.md`. It is not a live 15-minute `grok_approve` token. `write_agent` is null. This agent does not execute git/gh.

8. **Old “do not invent 2.0.10” is historical.** It applied while cutting unpublished 2.0.9. User SoT and the standing bump-if-tag-exists rule invert it the same way `06a59f` inverted the 2.0.8 hold.
