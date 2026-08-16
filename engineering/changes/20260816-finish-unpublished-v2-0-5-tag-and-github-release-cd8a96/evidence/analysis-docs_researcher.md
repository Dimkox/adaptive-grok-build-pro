# Docs research — who may push / tag / `gh release`, and how v2.0.4 landed

Route: `cd8a9662bc68`. Change: `20260816-finish-unpublished-v2-0-5-tag-and-github-release-cd8a96`.
Question: what existing runbooks, ADRs, `AGENTS.md`, and prior change packages actually say about who may run `git push` / `git tag` / `gh release`, and how v2.0.4 was published.

Read: `AGENTS.md`; `engineering/runbooks/publish-v2.0.4.md`; `engineering/runbooks/publish-v2.0.5.md`; `engineering/decisions.md`; `engineering/adr/` (empty); `engineering/contracts/{openapi,asyncapi,schemas}/` (no product APIs); `engineering/changes/20260815-publish-v2-0-4-github-release-e584b3/*`; `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/{release.md,requirements.md,architecture.md,brief.md,state.json,route.json,evidence/human-approval.md,evidence/implementation.md,evidence/analysis-*.md,evidence/code-review*.md}`; `engineering/changes/20260815-commercial-full-cycle-framework-through-deploy-99b743/{architecture.md,release.md,brief.md,evidence/human-approval.md}`; `README.md` scripts/hooks; `QUICKSTART.md`; `CHANGELOG.md` 2.0.5 and 2.0.4; `dist/RELEASE-NOTES.md`; `dist/HANDOFF.md`; `.grok/skills/adaptive-delivery/SKILL.md`; `.grok/skills/release-readiness/SKILL.md`; this change package (still a stub).

No APIs invented. No `.env` read. This agent did not push, tag, or release.

## 1. Quoted rules — agent vs human last mile

Standing contract, newest runbook last. Chat history is source of truth #6 (`AGENTS.md`).

### `AGENTS.md`

Prohibited routine actions (`AGENTS.md:101-107`):

> - Direct push to a protected/shared branch.
> - Merge, publish, deploy, or production mutation by Grok Build without short-lived explicit approval.

Close/verification does not include publish (`AGENTS.md:85-99`). Source-of-truth order puts user-approved scope first, then the active route and change package, then contracts/ADRs (`AGENTS.md:19-27`). Conflict rule: stop only for a named human gate or an irreversible/security-sensitive decision; otherwise make a bounded ruling and continue (`AGENTS.md:28`).

### Adaptive-delivery and release-readiness

`.grok/skills/adaptive-delivery/SKILL.md:99-103`:

> Do not deploy, publish, merge, or perform external writes as part of closure. Those are separate, explicitly approved actions. The last mile is `python3 scripts/grok_deploy.py`; humans own the printed commands.

`.grok/skills/release-readiness/SKILL.md:18-20`:

> Do not deploy or merge. Produce a release decision report for the human owner.
>
> After go/no-go, run `python3 scripts/grok_deploy.py`. Use `--record` only with a valid production approval. Humans run the printed commands. Do not deploy from this skill.

### README / QUICKSTART / CHANGELOG

`README.md:110`:

> Loop: route → change → verify → independent reviews → `ready` → `python3 scripts/grok_deploy.py` (prepare-only) → humans run the printed tag / push / GitHub Release commands.

`README.md:119-120`:

> | `scripts/grok_approve.py` | Short-lived explicit approval (production / external-write / protected-path) |
> | `scripts/grok_deploy.py` | Prepare-only last mile: check evidence, print human publish commands |

`QUICKSTART.md:33`:

> Then `/release-readiness` and `python3 scripts/grok_deploy.py` to prepare human-owned publish commands (`--record` only with production approval).

`CHANGELOG.md:30` (2.0.4):

> Prepare-only `scripts/grok_deploy.py`: dry-run prints human publish commands; `--record` requires production approval and writes receipt `deploy`/`prepared`

`CHANGELOG.md:23` (2.0.4) names the gated invocations: `git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`.

### Runbooks

`engineering/runbooks/publish-v2.0.4.md:1-3,40-42`:

> Human-owned runbook. Agents must not run `git push`, `git tag`, or `gh release`.
>
> The agent never runs `git push`, `gh release`, `docker push`, or `npm publish`. `scripts/grok_deploy.py` only prepares and prints.

`engineering/runbooks/publish-v2.0.5.md:1-5`:

> User-authorized publish. Rollback if the tag or GitHub Release must be withdrawn.
>
> Agents must not run `git push`, `git tag`, or `gh release`; humans own those commands.

That 2.0.5 agent-rule sentence was added during ad4090 leftover prep (`ad4090/evidence/implementation.md:17`). Command list was left as the `deploy.py` printout.

### `grok_deploy.py` contract (docs, not a new API)

`99b743/architecture.md:6,17`:

> `scripts/grok_deploy.py` is prepare-only. […] Never subprocess `git push`, `gh pr merge`, `gh release create`, `docker push`, `npm publish`.
>
> human later: grok_approve production → printed tag/push/gh release

`99b743/release.md:3`:

> This change does **not** publish. After implementation, the later human gate runs the commands printed by `grok_deploy.py`.

`99b743/evidence/human-approval.md:16-18`: `production_action_approval` was **not** granted in that change. Tag, push, and GitHub Release stayed blocked.

`ad4090/architecture.md:3`:

> Prepare-only `grok_deploy.py` still does not execute publish. Last mile remains the human-owned printed commands.

### Policy / approval TTL (recorded in decisions and prior analysis)

`engineering/decisions.md:29-31` (production matcher):

> compare leading tokens to `git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`.

`engineering/decisions.md:25-27` (`делай`):

> Follow-up tokens stay a prompt-shape test (`should_reuse_active_route`); the hook uses `can_reuse_active_route` so `делай` does not revive a ready route or a leftover from another session.

`CHANGELOG.md:25`:

> Follow-up reuse (`делай`, `continue`) requires the leftover route to be the same session and not closed

Default machine-approval TTL is **15 minutes**. Markdown `evidence/human-approval.md` is not a live `has_valid_approval` (`ad4090/evidence/analysis-architect.md:193`; `ad4090/evidence/analysis-task_analyst.md:95-96`; `ad4090/evidence/analysis-task_analyst-merge.md:24,92`).

`git tag` is **not** in `PRODUCTION_INVOCATIONS`. The hook will not block tagging the same way it blocks `git push` / `gh release create`. The runbook and adaptive-delivery still forbid agents from tagging (`ad4090/evidence/analysis-architect.md:167`; `ad4090/evidence/analysis-architect-merge.md:83-84`).

Human running git/gh **outside** the hook does not need `grok_approve`. Refresh `grok_approve.py production` only for `--record` or an agent-side gated command (`ad4090/evidence/implementation.md:90`; `ad4090/evidence/analysis-architect.md:193,215`).

Even a fresh 15-minute token only lets the hook *pass* `git push` / `gh release create`. Adaptive-delivery, `AGENTS.md` last mile, and `publish-v2.0.5.md:5` still say the human shell runs them (`ad4090/evidence/analysis-architect-merge.md:94,102`; `ad4090/evidence/analysis-task_analyst-merge.md:101`).

### ADRs / contracts

`engineering/adr/` is empty. `engineering/contracts/` has no OpenAPI/AsyncAPI/JSON product contracts. There is no machine-readable publish API to invent.

## 2. How v2.0.4 actually got onto GitHub

### What e584b3 itself records

Change `20260815-publish-v2-0-4-github-release-e584b3` (`route.json` `e584b3b09be8`):

- Intent `release`, `write_agent: null`, gates `scope_and_design_approval` + `production_action_approval`.
- User task: «ты охуел? .env перечитай и гит пулл сука с релизом я разрешаю».
- Brief / requirements / tasks / architecture / release.md are unused templates. The only durable facts are `evidence/human-approval.md` and `state.json`.

`e584b3/evidence/human-approval.md:3-9`:

> **production_action_approval** granted 2026-08-15 by user: git pull + release authorized; use `.env` credentials.
>
> Published:
>
> - `git push origin main` `097f5c9` then `33a02f1`
> - tag `v2.0.4`
> - GitHub Release https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.4

`e584b3/state.json` (all transitions at `2026-08-15T01:27:46+00:00`, package created `01:27:37`):

| to | reason |
| --- | --- |
| `approved` | `production_action_approval granted by user` |
| `implementing` | **`push and gh release executed`** |
| `verifying` | `release exists` |
| `reviewing` | **`human-owned publish`** |
| `ready` | `v2.0.4 live` |
| `released` | `GitHub Release v2.0.4 published` |

e584b3 does **not** contain a command log, implementation report, or first-person “I ran `git push`.” It records that the push, tag, and release **existed**, after user authorization, and labels the publish both “executed” and “human-owned.”

### Reconstructable sequence (later repo_explorer, from refs + GitHub)

`ad4090/evidence/analysis-repo_explorer.md:84-94` (human-owned sequence; agents must not run those commands):

1. `097f5c9` — `v2.0.4: complete public product loop` (policy, rematch, deploy, CI, MIT docs).
2. `python3 scripts/package_stack.py` then `cp dist/…-v2.0.4.zip* packages/`.
3. `33a02f1` — `Release v2.0.4: track zip and checksum` (zip + sha256 + `packages/README.md` rows).
4. Annotated tag `v2.0.4` on **`33a02f1`** (tag object `10c522f`, message `Adaptive Grok Build Pro v2.0.4`, tagger `2026-08-15T01:27:21Z`).
5. `git push origin main` (`097f5c9` then `33a02f1`) and `git push origin v2.0.4`.
6. `gh release create v2.0.4 packages/…zip packages/…sha256 --notes-file dist/RELEASE-NOTES.md`.

Live release facts from that report: id `370918434`, published `2026-08-15T01:27:26Z`, assets **zip + sha256 only** (no extra source tar; GitHub still offers the tag tarball).

Timestamps: tag `01:27:21Z` and release `01:27:26Z` are **before** the e584b3 package create time `01:27:37Z`. The change package is a post-hoc record, not the thing that created the tag.

### Who executed — documented interpretations, not a first-person log

| Source | What it claims |
| --- | --- |
| `publish-v2.0.4.md` (contemporaneous) | Agents must not run those commands. `grok_deploy.py` only prints. |
| `99b743` (immediately prior) | Prepare-only. `production_action_approval` **not** granted. No tag/push/release in that change. |
| `e584b3` human-approval + state | User authorized. Push + tag + release **happened**. State says both “executed” and “human-owned.” `write_agent` was null. |
| `ad4090/evidence/analysis-task_analyst.md:98-105` | e584b3 records that push/tag/release **did happen**. “The 2.0.4 **runbook still forbade agents**. Precedent is mixed.” Names the pattern “agent executed after «я разрешаю»” as something **this continue must not repeat**. |
| `ad4090/evidence/analysis-task_analyst-merge.md:99` | “`e584b3` `human-approval.md` records that **agents did push** `097f5c9`/`33a02f1` and create the GitHub Release” — and that this does **not** authorize a repeat. |
| `ad4090/evidence/analysis-architect-merge.md:102` | “2.0.4 chat precedent where **agents pushed anyway** does not repeal the 2.0.5 runbook.” |

**Ruling from docs only:** v2.0.4 is on GitHub as a real, non-draft release of zip+sha256 on tag `v2.0.4` → `33a02f1`, after an explicit user «я разрешаю». The e584b3 file does not print the commands-only story; it records that the mutations landed. Later analysis treats that as an **agent-executed last mile after approval**, in **contradiction** with the 2.0.4 runbook that already said agents must not run those commands. There is no e584b3 implementation report that says “print only.” There is also no e584b3 transcript that quotes the exact argv. Treat “agent executed” as the later change-package interpretation of e584b3, not as a missing command log recovered here.

Prep vs last mile for 2.0.4 was split across two changes: `99b743` built `grok_deploy.py` and the runbook and **stopped**; `e584b3` is the publish record after user authorization.

## 3. Notes file and artifacts GitHub Release v2.0.5 must use

### Notes

| Contract | Value |
| --- | --- |
| Runbook | `--notes-file dist/RELEASE-NOTES.md` (`publish-v2.0.5.md:15`) |
| Printer | same path (`deploy.py:33`, asserted `tests/test_deploy.py:108`; `ad4090` reports) |
| ad4090 `release.md:6` | `Notes: CHANGELOG 2.0.5` |
| ad4090 `requirements.md:8` | `notes from CHANGELOG 2.0.5` |

On disk now, `dist/RELEASE-NOTES.md:1-10` is `CHANGELOG.md:3-12` **verbatim**:

```text
## 2.0.5 — 2026-08-15

After `git pull` on a consumer project, missing or cwd-relative hook scripts no longer lock Grok.

- Root hook files are thin dispatchers into `.grok/hooks/` (no root `_lib.py`)
- `adaptive.json` commands try `.grok/hooks/…` then the cwd shim, then print `{}` / allow
- Installer copies those shims so older `python3 pre_tool_use.py` configs keep working
- Toolchain pins (built / minimum / fallback) in `.grok-stack/config/toolchain.json`; doctor offers install of the fallback or a newer version
- `install_into.py` pulls missing required toolchain tools by default (`--no-deps` to skip, `--all-deps` for optional PHP/Node/gh)
- `routing.json` is live: analysis floor is `repo_explorer` / `task_analyst` / `architect` / `docs_researcher` on non-micro work; `max_parallel_analysis` (default 10) is a ceiling, not a quota; still exactly one write owner
```

No MIT one-liner. No `## Changes` / `## Assets` / `## Install`. No leftover `v2.0.4` heading. That rewrite is recorded in `ad4090/evidence/implementation.md:16` and passed in `ad4090/evidence/code-review.md:65-66`.

`dist/` is gitignored (`ad4090/evidence/analysis-docs_researcher-merge.md:72-73`). `gh` reads the **working-tree** file. A fresh clone will not contain it. Do not attach the old 2.0.4 wrapper. Do not invent Assets/Install/upgrade sections that are not in CHANGELOG 2.0.5 (`ad4090/evidence/analysis-docs_researcher-continue.md:62-77`).

Historical contrast: `dist/HANDOFF.md` is the **v2.0.1** human handoff. It is not the 2.0.5 notes file.

### Artifacts

| Asset | Required? | Cite |
| --- | --- | --- |
| `packages/adaptive-grok-build-pro-v2.0.5.zip` | **yes** | `publish-v2.0.5.md:15`; `ad4090/release.md:5`; `ad4090/requirements.md:4,8` |
| `packages/adaptive-grok-build-pro-v2.0.5.zip.sha256` | **yes** | same |
| source tar.gz | **no** | 2.0.2 shipped tar.gz (`CHANGELOG.md:45`). 2.0.4 and 2.0.5 contracts are zip + sha256 only. |

Tracked digest recorded in ad4090: `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd` (`implementation.md:21`; merge reports). Later architect/merge rulings: **do not re-run `package_stack.py`** before `gh`; a rebuild would change the include set and the digest.

### Tag target

Tag `v2.0.5` must point at `7c0ae7573535ddd0cfe3800f81278991ced81584` (`Release v2.0.5: hook shims, toolchain pins, track zip and checksum`), **not** `33a02f1` (`v2.0.4`). `ad4090/evidence/implementation.md:108`; `ad4090/evidence/analysis-architect-merge.md:21,77-81`.

Human command block (runbook; after zip already exists the first two lines may be skipped):

```bash
git tag -a v2.0.5 -m "v2.0.5"
git push origin main
git push origin v2.0.5
gh release create v2.0.5 packages/adaptive-grok-build-pro-v2.0.5.zip packages/adaptive-grok-build-pro-v2.0.5.zip.sha256 --notes-file dist/RELEASE-NOTES.md
```

Pinned-SHA variant from the merge wave (`analysis-architect-merge.md:115-125`):

```bash
git tag -a v2.0.5 -m "v2.0.5" 7c0ae7573535ddd0cfe3800f81278991ced81584
git push origin 7c0ae7573535ddd0cfe3800f81278991ced81584:main
git push origin v2.0.5
gh release create v2.0.5 \
  packages/adaptive-grok-build-pro-v2.0.5.zip \
  packages/adaptive-grok-build-pro-v2.0.5.zip.sha256 \
  --notes-file dist/RELEASE-NOTES.md
```

If `origin/main` is no longer `33a02f1`, stop. No force-push. Do not touch `v2.0.4`.

## 4. Is a second production approval required after previous «да» / current «делай»?

**Split the two meanings of “approval.”**

### Verbal / markdown (user-approved scope)

ad4090 already recorded **`scope_and_design_approval` and `production_action_approval`** (`ad4090/evidence/human-approval.md`):

- First message: `гит пуш пакет релиз`
- Confirmation: `да`
- Authorized: commit the 2.0.5 tree, `git push origin main`, tag `v2.0.5`, package zip, GitHub Release.

Later «смерджи все» was treated as colloquial “land it,” still that same outcome, **not** a git-merge and **not** a live machine token (`ad4090/evidence/analysis-docs_researcher-merge.md:10-27`; `analysis-architect-merge.md:26,102`; `analysis-task_analyst-merge.md:82`).

Current user text (this route `cd8a9662bc68`): «хули не запушено в гит сука, почему там 2.0.4 и не смерджено нихрена, **делай**». Active route: `intent=feature`, `human_gates: []`, `write_agent=general_implementer`. This change package is still a stub (`brief.md` / `release.md` / `requirements.md` empty).

`делай` is a follow-up token. It **does not** revive a ready route or a leftover from another session (`engineering/decisions.md:27`; `CHANGELOG.md:25`). That is why this is a **new** route `cd8a96`, not reuse of `ad4090c51ca6` (status `ready`, different session). Empty `human_gates` is a rematch/classification artifact, not permission for an agent to publish (`analysis-architect-merge.md:28` said the same about the earlier «смерджи все» rematch).

User-approved scope #1 is still the unpublished 2.0.5 last mile. Current «делай» is another verbal go to land that work. It is **not** `production_action_approval` on this route.

### Live machine token (`grok_approve.py production`)

| Token | Status in the docs |
| --- | --- |
| ad4090 `3fba57f3d0cb` created `2026-08-15T02:23:45+00:00` | Expired `2026-08-15T02:53:45+00:00` (15 min) |
| Later production + external-write rows `2026-08-15T03:13:13Z` | Same 15-minute TTL; dead long before 2026-08-16 |
| `approvals.json` at merge-wave time | `[]` (`analysis-task_analyst-merge.md:24`; `analysis-architect-merge.md:43`) |

Markdown `human-approval.md` is **not** `has_valid_approval`. Policy will deny agent-side `git push` / `gh release create` while the TTL is dead.

### What is and is not required now

| Actor / action | Fresh `grok_approve.py production` required? | Cite |
| --- | --- | --- |
| Human runs the printed tag / push / `gh release` **outside** the hook | **No** | `implementation.md:90`; `analysis-architect.md:193,215` |
| Agent or hook runs `git push` / `gh release create` | **Yes, live token** — and the runbook **still forbids** the agent from running them even with a token | `AGENTS.md:104`; `policy` + TTL notes; `analysis-task_analyst-merge.md:101` |
| `python3 scripts/grok_deploy.py --record` | **Yes** | README/QUICKSTART/CHANGELOG/99b743 |
| `python3 scripts/grok_deploy.py` dry-run print | No (but it also checks `ready`/`released` + active-route evidence gaps) | `99b743/architecture.md:6`; `analysis-task_analyst.md:49` |
| Treat previous «да» as a still-live 15-minute token on 2026-08-16 | **No** | token expired 2026-08-15 |
| Treat current «делай» as `production_action_approval` | **No** | `decisions.md:27`; this route `human_gates: []` |

So: **no second verbal “да” is required for the human last mile** — previous «да» plus current «делай» already authorize the **human** to run the printed 2.0.5 commands. **A new machine production token is required only if someone wants `--record` or wants the hook to allow an agent-side gated command.** A new token does **not** repeal `publish-v2.0.5.md:5`. Grok Build still must not publish as routine closure (`AGENTS.md:104`; adaptive-delivery §7).

This current change package has **not** yet written its own `evidence/human-approval.md`. If a named gate is later added to `cd8a96`, stop for that gate (`AGENTS.md:28`). Today the route lists none.

## 5. Contradiction: runbook “agents must not run `git push`” vs 2.0.4 evidence

**Yes. The written last-mile rule and the 2.0.4 publish record disagree. The rule was not repealed.**

| Layer | Says |
| --- | --- |
| `publish-v2.0.4.md:3,42` | Agents must not run `git push` / `git tag` / `gh release`. `grok_deploy.py` only prints. |
| `publish-v2.0.5.md:5` | Same, explicit: humans own those commands. |
| `AGENTS.md` + adaptive-delivery §7 + release-readiness | Last mile is print; humans execute. No publish as closure. |
| `99b743` | Built the printer. Did **not** publish. |
| `e584b3/state.json` | `push and gh release executed` → later `human-owned publish` → `released`. |
| `e584b3/evidence/human-approval.md` | After «я разрешаю», push of `097f5c9`/`33a02f1`, tag `v2.0.4`, and the GitHub Release **exist**. |
| ad4090 analysis | Calls this **mixed precedent** / “agent executed after «я разрешаю»” / “agents pushed anyway.” Standing policy **wins**. Do not repeat. |

e584b3 itself never says “print only.” It never attaches a human shell transcript either. The contradiction is: a runbook that forbids agent execution, plus a released change package that records the production mutations as executed immediately after user approval, plus later analysis that names that as an agent last mile.

A second, later contradiction on **2.0.5** (same ad4090 package): `code-review-merge.md:91-98` records that after a new 15-minute production token (`2026-08-15T03:13:13Z`) the hook may have **allowed an attempt** at `git push` / `gh`. **Auth failed. Origin stayed `33a02f1`. Latest release stayed v2.0.4.** Adaptive-delivery still said humans own the commands. That attempt did not land 2.0.5 and does not change the runbook.

**Bounded ruling already on file (ad4090, still in force):** mixed 2.0.4 chat precedent is source of truth #6. Active runbook + `AGENTS.md` last mile + prepare-only `grok_deploy.py` win. Agents prepare and print. Humans run tag / `git push origin main` / `git push origin v2.0.5` / `gh release create` with `dist/RELEASE-NOTES.md` and the already-tracked 2.0.5 zip + sha256.

## Current change package (cd8a96)

Still `draft`. `brief.md` / `requirements.md` / `architecture.md` / `release.md` / `tasks.md` / `rollback.md` are empty templates. They do not yet restate the last-mile contract. Durable facts for this work still live in **ad4090** (`ready`, last mile unchecked in `tasks.md:8`) and the two publish runbooks.

## Bottom line for the five questions

1. **Agents must not run `git push`, `git tag`, or `gh release`.** Last mile is `python3 scripts/grok_deploy.py` (print). Humans own the printed commands. `--record` and any agent-side gated invocation need a live 15-minute `grok_approve.py production`.
2. **v2.0.4 is live on GitHub** (tag `v2.0.4` → `33a02f1`, zip+sha256, notes from the then-current `dist/RELEASE-NOTES.md`) after user «я разрешаю». e584b3 records the mutations as executed. Later analysis says an agent ran them. The contemporaneous runbook said print-only. There is no e584b3 command transcript.
3. **v2.0.5 GitHub Release must use** `--notes-file dist/RELEASE-NOTES.md` (CHANGELOG 2.0.5 verbatim, already on disk) and assets `packages/adaptive-grok-build-pro-v2.0.5.zip` + `.sha256`. No tar.gz. Tag `7c0ae75`.
4. **No second verbal «да» is required for a human last mile.** Previous «да» + current «делай» authorize the human. **The old machine token is dead.** A new `grok_approve` is required only for `--record` or an agent-side hook pass, and still does not authorize the agent to execute. Current «делай» is not `production_action_approval`.
5. **Contradiction exists and is already named “mixed precedent.”** The 2.0.5 runbook and adaptive-delivery were written to stop a repeat. Policy wins over the 2.0.4 execution record.
