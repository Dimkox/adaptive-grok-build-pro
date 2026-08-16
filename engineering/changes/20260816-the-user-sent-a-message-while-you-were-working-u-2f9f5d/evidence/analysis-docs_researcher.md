# Docs research — last mile is git/gh CLI, not Actions; «гони»+«продолжай» authorizes push of 7152b75, not a new GitHub Release

Route: `2f9f5d5bc202`. Change: `20260816-the-user-sent-a-message-while-you-were-working-u-2f9f5d`.

Question: standing last mile is git push / gh CLI, not GitHub Actions. User «гони» then «продолжай деплой окружения для разработки» authorizes push of unpublished `7152b75`, not a new GitHub Release. Confirm.

Read-only. No APIs invented. No `.env`. No push / merge / deploy.

Loaded `/adaptive-delivery` from `.grok/skills/adaptive-delivery/SKILL.md`. This agent is in `allowed_agents`. `write_agent` is `null`. `workflow_skills` are `adaptive-delivery` + `release-readiness`. `human_gates` are `scope_and_design_approval` and `production_action_approval`. Required evidence: `verification`, `security_review`, `release_review`.

---

## Verdict

| Claim | Standing fact? | Ruling |
| --- | --- | --- |
| Standing last mile is **git push / gh CLI**, not GitHub Actions | **Yes.** Runbooks open with “Last mile is GitHub CLI, not GitHub Actions.” Printer is `python3 scripts/grok_deploy.py`. Quality gate is local `grok_verify --mode pr`. | **Confirm.** |
| User «гони» authorizes **push**, not tag / zip / Release | **Yes.** 04ae05 `brief.md` / `release.md` / `state.json`. | **Confirm.** |
| «продолжай деплой окружения для разработки» continues that unfinished last mile | **Yes.** This package + predecessor 2a31f5 / a13da8. It is “continue the unpublished `origin/main` push,” not a new SKU. | **Confirm.** |
| Authorized object is unpublished `7152b75`, not a new GitHub Release | **Yes.** `7152b75` is one local commit ahead of `origin/main` (`22762a7` / “Release v2.0.8”). `VERSION` stays `2.0.8`. No tag. No `gh release create`. | **Confirm.** |

`engineering/adr/` is empty. `engineering/contracts/{openapi,asyncapi,schemas}/` have no product APIs. There is no ADR or contract that names GitHub Actions as a publish path, or that turns this follow-up into a Release.

Do not invent a deploy API. Do not treat `grok_deploy.py`’s full printer (tag + `gh release create v2.0.8`) as this change’s command list.

---

## Sources

Standing (authority):

- `.grok/skills/adaptive-delivery/SKILL.md` §7
- `.grok/skills/release-readiness/SKILL.md`
- `AGENTS.md` source-of-truth order + prohibited routine actions
- `README.md` Scripts loop + Requirements (`gh` = “for GitHub Release”)
- `QUICKSTART.md` steps 6–7
- `decisions.md` 2026-08-16 Never GitHub Actions; 2026-08-14 Match production side-effects as argv prefixes
- `CHANGELOG.md` §§2.0.8, 2.0.7, 2.0.6, 2.0.4
- `VERSION` = `2.0.8`
- `engineering/runbooks/publish-v2.0.{4,5,6,7,8}.md`
- `.grok-stack/templates/ci/README.md`
- `scripts/grok_deploy.py` (print-only)
- `.grok-stack/adaptive_grok/deploy.py` `_human_commands`
- `packages/README.md`

Predecessor change packages (user-approved scope for this last mile):

- `20260816-user-query-гони-user-query-04ae05` (user «гони»)
- `20260816-the-user-sent-a-message-while-you-were-working-u-a13da8` (K10 README + unfinished «гони» push)
- `20260816-the-user-sent-a-message-while-you-were-working-u-2a31f5` (CLI-only; push `7152b75`; no Release)
- `20260816-user-query-пересобирай-себя-под-следущей-версией-37141f` (2.0.8 identity; GitHub Release out of scope)
- This package: `brief.md`, `architecture.md`, `requirements.md`, `release.md`, `tasks.md`, `evidence/human-approval.md`

---

## 1. Standing last mile is git push / gh CLI, not GitHub Actions — confirmed

### 1.1 Controller and printer

`.grok/skills/adaptive-delivery/SKILL.md` §7:

> Do not deploy, publish, merge, or perform external writes as part of closure. Those are separate, explicitly approved actions. The last mile is `python3 scripts/grok_deploy.py`; humans own the printed commands.

`.grok/skills/release-readiness/SKILL.md`:

> After go/no-go, run `python3 scripts/grok_deploy.py`. Use `--record` only with a valid production approval. Humans run the printed commands. Do not deploy from this skill.

`scripts/grok_deploy.py`: “Prepare human-owned publish commands. Never executes tag, push, or release.” On success it prints strings. It does not `subprocess` them.

### 1.2 Printed verbs (the CLI last mile)

`.grok-stack/adaptive_grok/deploy.py` `_human_commands` (full product-publish list):

```
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v{version}.zip* packages/
git tag -a v{version} -m "v{version}"
git push origin {branch}
git push origin v{version}
gh release create v{version} packages/{zip} packages/{zip}.sha256 --title "Adaptive Grok Build Pro v{version}" --notes-file dist/RELEASE-NOTES.md
```

`README.md` Scripts: loop ends at prepare-only `grok_deploy.py`, then “humans run the printed tag / push / GitHub Release commands.”

`QUICKSTART.md` step 6: `python3 scripts/grok_deploy.py` “to prepare human-owned publish commands.”

`README.md` Requirements: GitHub CLI (`gh`) is “for GitHub Release.” Predecessor 2a31f5 also uses `gh` as the HTTPS credential helper (`credential.helper='!gh auth git-credential'`). Both uses are **gh CLI**. Neither is GitHub Actions.

### 1.3 Runbooks say the split in one sentence

| File | Opening |
| --- | --- |
| `publish-v2.0.8.md` | “Last mile is GitHub CLI, not GitHub Actions.” Then `git push origin main`, `git push origin v2.0.8`, `gh release create …` |
| `publish-v2.0.7.md` | Same pattern. |
| `publish-v2.0.6.md` | “Last mile is the GitHub CLI (`gh release create`), not GitHub Actions. Do not add `.github/workflows/`.” Agents must not run `git push` / `git tag` / `gh release`. |
| `publish-v2.0.5.md` | Agents must not run those three; humans own them. |
| `publish-v2.0.4.md` | “The agent never runs `git push`, `gh release`, `docker push`, or `npm publish`. `scripts/grok_deploy.py` only prepares and prints.” |

### 1.4 Never GitHub Actions (live rule)

`decisions.md` 2026-08-16 — Never GitHub Actions:

> Local `make verify` / `python3 scripts/grok_verify.py --mode pr` is the only quality gate. Do not add `.github/workflows/`, Dependabot, `--with-ci` copies, or another CI SaaS. `install_into --with-ci` is `SystemExit` / forbidden.

`.grok-stack/templates/ci/README.md`: “This product never uses GitHub Actions.”

`CHANGELOG.md` 2.0.8 / 2.0.7: “Still no GitHub Actions.” 2.0.6: local `grok_verify --mode pr` is the only gate; `--with-ci` is forbidden.

GitHub **Release** (`gh release create`) is not GitHub **Actions**. Standing docs already split those. This change is not creating a Release.

Policy (`decisions.md` 2026-08-14) gates the real argv prefixes `git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`. Those are CLI invocations, not workflow files.

`AGENTS.md` prohibits unapproved merge / publish / deploy. It does not name Actions as a last-mile path.

---

## 2. «гони» then «продолжай деплой…» authorizes push of unpublished 7152b75, not a new GitHub Release — confirmed

### 2.1 What «гони» already granted

`20260816-user-query-гони-user-query-04ae05`:

- `brief.md`: “User «гони» is the production go for **push**.” Out of scope: VERSION bump, zip rebuild, tag, GitHub Release, GitHub Actions.
- `release.md`: “Push only. No tag. No GitHub Release. VERSION stays 2.0.8.”
- `state.json`: transitioned to `approved` with reason “user гони authorizes push of the ready ba1615 tree.” Status remains `approved`, not pushed.
- 04ae05 `evidence/analysis-docs_researcher.md`: no standing doc, ADR, or contract requires a bump or GitHub Release for that push.

a13da8 folded the unfinished «гони» push after the README K10:

- `release.md`: “Push only. VERSION 2.0.8. No tag. No GitHub Release.”
- `tasks.md` item 5 still open: “Push origin/main. (controller; no tag, no VERSION bump)”
- `evidence/analysis-task_analyst.md` §2.5: “This is last-mile **push**, not publish. User «гони» … is the production go for **`git push origin main` only**.”
- `evidence/implementation.md`: write owner committed locally; “`origin/main` still lacks the root logs and the K10 README until the controller pushes.”

37141f (2.0.8 identity) already said GitHub Release / tag were out of scope unless a later controller ran printed `grok_deploy` commands. That prompt said git push, not `gh release create`. This follow-up is the same shape, without a new identity.

### 2.2 What 7152b75 is (unpublished, not a new SKU)

2a31f5 `evidence/analysis-repo_explorer.md` recorded the refs:

| Ref | SHA | Subject |
| --- | --- | --- |
| `HEAD` / `refs/heads/main` | `7152b75b610bada0ecc7468752900ab1515324f1` | Document root agent logs and complete K10 stack graph in README |
| `refs/remotes/origin/main` | `22762a77ea4133cc34398f9a70194daa427bd096` | Release v2.0.8 |

This route’s `base_commit` is still `22762a77ea4133cc34398f9a70194daa427bd096`. `VERSION` is still `2.0.8`. `7152b75` is one local commit ahead of origin: the ba1615 root logs + a13da8 K10 README. It is **not** a 2.0.9 ship and not a retag of 2.0.8.

2a31f5 `release.md`: “Push `7152b75` only. CLI. No tag. No GitHub Release.”

That predecessor stayed `approved` and did not land the push (Bitvise GUI false alarm; user now says Codex-on-Windows).

### 2.3 What «продолжай деплой окружения для разработки» grants on this route

Active-route task (verbatim user follow-up):

> ложная тревога, это кодекс под виндой хуйню творил, продолжай деплой окружения для разработки

“Продолжай” is continue the unfinished last mile. “Деплой окружения для разработки” is the outstanding `git push origin main` of that unpublished tree so `origin/main` matches local development HEAD. It is **not** “cut a new GitHub Release.”

This package already records that reading:

- `brief.md`: “User «гони» then «продолжай деплой окружения для разработки» is `scope_and_design_approval` and `production_action_approval` **for this push only**.” Outcome: `origin/main` == `7152b75`. No tag, no GitHub Release, no VERSION bump.
- `release.md`: “Push `7152b75` to `origin/main`. VERSION stays 2.0.8. No tag. No GitHub Release.”
- `requirements.md`: no Bitvise/GUI; no tag; no `gh release create`.
- `architecture.md` last mile: verify → security/release reviews → `grok_approve production` → `GIT_TERMINAL_PROMPT=0 git -c credential.helper='!gh auth git-credential' push origin main`.
- `evidence/human-approval.md`: authorized `git push origin main` of `7152b75` via git/gh CLI. **Not** authorized: tag, `gh release create`, force-push, GitHub Actions, Bitvise GUI, sudo install of optional PHP.
- `rollback.md`: do not force-push; forward-fix if already on origin.

The route is `intent=release` / `risk=high` only because the prompt contained «деплой». That classifier does not expand scope to `gh release create`. `write_agent` is `null`: no product write, last mile only.

### 2.4 Do not run the full product-publish printer

`grok_deploy.py` `_human_commands` still prints `git tag -a v2.0.8` and `gh release create v2.0.8 …` because `VERSION` is `2.0.8`. Standing runbook `publish-v2.0.8.md` is that **versioned publish** list.

This change’s authorized last mile is the **narrower** 04ae05 / a13da8 / 2a31f5 list: `git push origin main` of `7152b75` only. Running the full printer would tag and open a GitHub Release, which every package in this chain forbids.

Policy still requires a **fresh** live `grok_approve.py production` token before agent Bash `git push` (`AGENTS.md` prohibited routine actions; 04ae05 architecture: “Do not reuse the 2.0.8 push token.” 2a31f5 recorded the prior production row as expired).

---

## 3. Fact for the controller

1. **Confirm** standing last mile tooling: `git` + `gh` CLI. Never GitHub Actions. Never add `.github/workflows/`.
2. **Confirm** this authorization: «гони» + «продолжай деплой окружения для разработки» = push unpublished `7152b75` to `origin/main`.
3. **Do not** bump `VERSION`, rebuild the zip, tag, or `gh release create`.
4. **Do not** treat `grok_deploy.py`’s full 2.0.8 printer as the command list for this route.
5. After green `grok_verify --mode pr` and independent `security_review` + `release_review`, mint a fresh production approval, then:

```
GIT_TERMINAL_PROMPT=0 git -c credential.helper='!gh auth git-credential' push origin main
```

No contract or ADR to update. Empty `engineering/adr/` and empty contract trees stay empty.
