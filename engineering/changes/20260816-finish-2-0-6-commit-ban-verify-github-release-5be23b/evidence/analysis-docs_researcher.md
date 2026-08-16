# Docs research — GitHub Release ≠ Actions; last mile; «go ahead» + prior release demand

Route: `5be23b16d59f`. Change: `20260816-finish-2-0-6-commit-ban-verify-github-release-5be23b`.
Question: confirm GitHub Release is not GitHub Actions; last mile is still `grok_deploy` commands; user «go ahead» plus prior release demand authorizes publish. Quote `publish-v2.0.6.md`.

Read-only. No application-code edits. No `.env`. No push / merge / deploy. No APIs invented.

Adaptive-delivery loaded from `.grok/skills/adaptive-delivery/SKILL.md`. This agent is in `allowed_agents`. `write_agent` is `general_implementer`. `human_gates` is empty. Required evidence on this route: `verification`, `code_review`, `test_review`.

## Sources

- This change package (`brief.md`, `architecture.md`, `requirements.md`, `release.md`, `rollback.md`, `tasks.md`, `test-plan.md`, `state.json`, `route.json`, `evidence/human-approval.md`)
- `.grok-stack/runtime/active-route.json` (`task`: `<user_query>go ahed</user_query>`)
- `engineering/runbooks/publish-v2.0.6.md` (quoted in full below)
- `engineering/runbooks/publish-v2.0.4.md`, `publish-v2.0.5.md`
- `.grok/skills/adaptive-delivery/SKILL.md` §7; `.grok/skills/release-readiness/SKILL.md`; `.grok/skills/feature-workflow/SKILL.md`
- `AGENTS.md` source-of-truth order and prohibited routine actions
- `engineering/decisions.md` 2026-08-16 Never GitHub Actions; 2026-08-14 production-invocation prefixes
- `README.md`, `QUICKSTART.md`, `CHANGELOG.md` §2.0.6 / §2.0.4, `dist/RELEASE-NOTES.md`, `packages/README.md`, `VERSION`
- `.grok-stack/templates/ci/README.md` (current: never GitHub Actions)
- `scripts/grok_deploy.py`, `.grok-stack/adaptive_grok/deploy.py` `_human_commands`, `.grok-stack/adaptive_grok/policy.py` `PRODUCTION_INVOCATIONS`
- `scripts/grok_approve.py` default TTL 15 minutes
- `.grok-stack/runtime/approvals.json` (not `.env`)
- `tests/test_deploy.py` last-mile printer + no-workflow tests
- `.grok-stack/config/toolchain.json` tool `gh` (`name`: GitHub CLI, `profile`: release)
- Prior packages: `864726` (prior «делай всё полностью вместе с релизом»), `9fd274` (GHA ban + rebuild; last mile already authorized), `39b13f` (user GHA ban wording), `ec0388`, `cd8a96`
- `engineering/adr/` empty. `engineering/contracts/{openapi,asyncapi,schemas}/` have no product APIs.

---

## 1. Quote: `engineering/runbooks/publish-v2.0.6.md` (entire file)

```1:36:engineering/runbooks/publish-v2.0.6.md
# Publish v2.0.6

Print-only last mile. Assemble the zip first; humans own tag / push / GitHub Release.

Last mile is the GitHub CLI (`gh release create`), not GitHub Actions. Do not add `.github/workflows/`.

Agents must not run `git push`, `git tag`, or `gh release`; humans own those commands.

## Checks

```bash
python3 scripts/grok_status.py
python3 scripts/grok_verify.py --mode pr
python3 scripts/grok_deploy.py
```

Only when a human is ready to publish: `python3 scripts/grok_approve.py production --reason "publish v2.0.6"`

## Commands

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.6.zip* packages/
git tag -a v2.0.6 -m "v2.0.6"
git push origin main
git push origin v2.0.6
gh release create v2.0.6 packages/adaptive-grok-build-pro-v2.0.6.zip packages/adaptive-grok-build-pro-v2.0.6.zip.sha256 --notes-file dist/RELEASE-NOTES.md
```

## Rollback

```bash
gh release delete v2.0.6 --yes
git push origin :refs/tags/v2.0.6
git tag -d v2.0.6
```
```

Facts locked by that file, not inferences:

| Line | Claim |
| --- | --- |
| 3 | Last mile is print-only; humans own tag / push / **GitHub Release** |
| 5 | Last mile is **GitHub CLI** `gh release create`, **not GitHub Actions**. Do not add `.github/workflows/` |
| 7 | Agents must not run `git push`, `git tag`, or `gh release` |
| 13–15 | Checks include `python3 scripts/grok_deploy.py` |
| 17 | Live machine token: `grok_approve.py production --reason "publish v2.0.6"` when a human is ready |
| 22–27 | Printed commands: packager → `cp` → annotated tag → push `main` → push tag → `gh release create` of zip + sha256 + `dist/RELEASE-NOTES.md` |
| 32–35 | Rollback is `gh release delete` + delete tag. That is the Release API, not a workflow |

No line in this runbook names `gh workflow run`, `workflow_dispatch`, Dependabot, or a hosted runner.

---

## 2. Confirmed: GitHub Release ≠ GitHub Actions

Independent in-repo sources. No document equates the two.

| Thing | What the tree calls it | What it does | Last-mile? |
| --- | --- | --- | --- |
| **Local verify** | `make verify` / `python3 scripts/grok_verify.py --mode pr` | Only quality gate | No. Required before close. |
| **GitHub Actions** | Hosted CI; `.github/workflows/*.yml`; old `--with-ci` copy | **Banned.** `decisions.md` 2026-08-16: do not add `.github/workflows/`, Dependabot, `--with-ci` copies, or another CI SaaS | No. Never published. |
| **GitHub Release** | `gh release create v<VERSION> …` via GitHub CLI | Advertises `packages/` zip + sha256 as Latest | **Yes.** Different CLI, different policy gate. |

Standing splits:

- `publish-v2.0.6.md:5`: “Last mile is the GitHub CLI (`gh release create`), **not GitHub Actions**.”
- This package `brief.md:9`: “Tag/push/`gh release` (already authorized; **not GitHub Actions**).”
- This package `evidence/human-approval.md:3`: “Never GitHub Actions.”
- `9fd274/evidence/human-approval.md:7`: “Publish — prior: «делай всё полностью вместе с релизом». **GitHub Release is not GitHub Actions.**”
- `CHANGELOG.md:10` (2.0.6, also `dist/RELEASE-NOTES.md:8`): “**No GitHub Actions** / Dependabot; local `python3 scripts/grok_verify.py --mode pr` is the only gate.”
- `CHANGELOG.md:33,41` (2.0.4 history, do not rewrite): `gh release create` is a **production CLI invocation**; “This-repo GitHub Actions: verify plus a conditional package job **(no publish)**.”
- `README.md:60`: GitHub CLI (`gh`) is “**for GitHub Release**.”
- `README.md:110`: humans run printed tag / push / **GitHub Release** commands.
- `.grok-stack/templates/ci/README.md:3`: “This product **never uses GitHub Actions**.”
- `tests/test_deploy.py:203-215`: CI README must say never GitHub Actions **and** must **not** contain `gh release` / `git push` / `docker push`.
- `tests/test_deploy.py:103-108`: `grok_deploy` dry-run **must** print `gh release create`.
- `policy.py:48-54` `PRODUCTION_INVOCATIONS` includes `('gh', 'release', 'create')` next to `git push`. There is no `github-actions` / `workflow` / `act` prefix.
- `toolchain.json` tool `gh`: name **GitHub CLI**, profile **release**. Not a runner.

Banning GitHub Actions therefore does **not** ban `gh release create v2.0.6`, `gh release delete v2.0.6 --yes` (this package `rollback.md`), the `gh` pin, or `--all-deps` installing `gh`.

Banning GitHub Actions **does** ban `.github/workflows/**`, Dependabot, installer `--with-ci` copy, and adding another CI vendor. Those are already out of scope on this package (`brief.md:13-15`).

---

## 3. Confirmed: last mile is still `grok_deploy` commands

The last mile is the **printed** six-line sequence from `python3 scripts/grok_deploy.py`. The script does not execute tag / push / release.

```15:15:scripts/grok_deploy.py
parser = argparse.ArgumentParser(description='Prepare human-owned publish commands. Never executes tag, push, or release.')
```

```24:34:.grok-stack/adaptive_grok/deploy.py
def _human_commands(root: Path, version: str) -> list[str]:
    …
        'python3 scripts/package_stack.py',
        f'cp dist/{zip_name}* packages/',
        f'git tag -a v{version} -m "v{version}"',
        f'git push origin {branch}',
        f'git push origin v{version}',
        f'gh release create v{version} packages/{zip_name} packages/{zip_name}.sha256 --notes-file dist/RELEASE-NOTES.md',
```

Same six lines as `publish-v2.0.6.md:21-27`. Checks in that runbook are `grok_status` → `grok_verify --mode pr` → **`python3 scripts/grok_deploy.py`**.

Controller / docs say the same:

| Source | Quote |
| --- | --- |
| Adaptive-delivery §7 (`SKILL.md:103`) | “The last mile is `python3 scripts/grok_deploy.py`; humans own the printed commands.” |
| Release-readiness (`SKILL.md:20`) | “After go/no-go, run `python3 scripts/grok_deploy.py`. … Humans run the printed commands. Do not deploy from this skill.” |
| `README.md:110,120` | Loop ends at prepare-only `grok_deploy.py`; humans run printed tag / push / GitHub Release. |
| `QUICKSTART.md:33` | `python3 scripts/grok_deploy.py` prepares human-owned publish commands (`--record` only with production approval). |
| `CHANGELOG.md:5` | “2.0.5 remains the previous published GitHub Latest **until a human last mile**.” |
| `test_deploy.py:185-191` | `deploy.py` / `grok_deploy.py` must not import or call `subprocess` / `os.system`. |

Dry-run print needs the change `ready` or `released` plus empty evidence gaps (`deploy.py:10,55-63`). This package `state.json` is still **`draft`**. `grok_deploy.py --record` additionally needs a live production approval (`deploy.py:74-75`).

This change’s own sequence (`brief.md`, `architecture.md`, `tasks.md`) is: **commit** the already-on-disk GHA ban + rebuilt zip → `grok_verify --mode pr` → reviews → last mile on the **new** SHA. The packager/`cp` lines may already be done on disk (`9fd274/evidence/implementation.md`); the printer still names them. Tag target is **not** `549f29d` (`architecture.md:3`).

---

## 4. Confirmed: «go ahead» + prior release demand authorizes publish

User-approved scope is source of truth #1 (`AGENTS.md`). This route has **no** named `human_gates`. The verbal chain is recorded in this package and the two predecessors.

### 4.1 What the user said

| Utterance | Where recorded | Meaning on file |
| --- | --- | --- |
| «делай всё полностью вместе с релизом» | `864726/brief.md:3`; `864726/evidence/human-approval.md:5`; `864726/route.json` task | Names the **release**. Demands the full last mile, not another assemble. |
| «НИКОГДА НЕ ИСПОЛЬЗУЕМ ЕБАНЫЕ GITHUB ACTOIONS» | `39b13f/brief.md:12`; `9fd274/evidence/human-approval.md:3` | Bans **GitHub Actions**, not GitHub Release. |
| «и по новым правилам сам себя пересобери и проверь на версии 2.0.6» | `9fd274/evidence/human-approval.md:5` | Rebuild + local verify under the ban; stay on 2.0.6. |
| «go ahed» / «go ahead» | Active route `task`; this `brief.md:3`; this `evidence/human-approval.md:5` | Proceed: commit the banned tree as 2.0.6, verify, publish Latest. |

This package writes the conjunction explicitly:

`brief.md:3`:

> GHA already removed on disk. User «go ahead»: commit that tree as 2.0.6, verify locally, publish Latest.

`brief.md:9`:

> Tag/push/`gh release` (**already authorized**; not GitHub Actions)

`evidence/human-approval.md`:

> - Never GitHub Actions.
> - Rebuild/verify 2.0.6.
> - Publish: «делай всё полностью вместе с релизом» then «go ahead».

`9fd274/brief.md:15` already said the same last mile was “already authorized.” `9fd274/state.json` transitioned `approved` with reason “user rule never GHA plus prior publish authorization.”

`864726/evidence/analysis-docs_researcher.md:134-148` already classified «делай всё полностью вместе с релизом» (while Latest was still v2.0.5) as verbal `production_action_approval` for GitHub Latest v2.0.6. This «go ahead» is the follow-through after the GHA ban + rebuild, not a new product scope.

### 4.2 What that authorization covers

Authorized outcome (this package + 9fd274, **superseding** 864726’s tag-of-`549f29d`):

- Stay `VERSION` **2.0.6**. Do not open 2.0.7.
- Commit the on-disk GHA ban + rebuilt zip (`9fd274` left that tree uncommitted; this change owns the commit).
- Local `python3 scripts/grok_verify.py --mode pr`.
- Last mile: annotated `v2.0.6` on the **post-ban commit** (not `549f29d`), `git push origin main`, `git push origin v2.0.6`, `gh release create` of `packages/adaptive-grok-build-pro-v2.0.6.zip` + `.sha256` + `dist/RELEASE-NOTES.md`.
- GitHub Latest becomes `v2.0.6`. `v2.0.5` stays viewable (`test-plan.md:3-4`; this `rollback.md:9`).
- Do not restore GHA. Do not add another CI vendor. Do not force-push. Do not print secrets.

Current rebuilt digest on disk (`packages/adaptive-grok-build-pro-v2.0.6.zip.sha256`; `9fd274/evidence/implementation.md:50`):

```
55406ff22f81ae05fc70eb9a5710b5c055c76a18f2ddbe60687c03b3e0b95c4d  adaptive-grok-build-pro-v2.0.6.zip
```

`864726/requirements.md` digest `b34af685…` and tag target `549f29d` are **stale**. That package is still `draft` and assumed a tree that still shipped GitHub Actions. This change `architecture.md:3`: “last mile on the **new** SHA (not 549f29d).”

### 4.3 What it is not

| Claim | Status |
| --- | --- |
| Verbal / markdown authorization of the **GitHub Release** outcome | **Yes.** SoT #1. This package records it. |
| Authorization to use **GitHub Actions** | **No.** Opposite. Never GHA. |
| Live `has_valid_approval` machine token | **No.** `approvals.json` only has expired 2.0.5 rows (`3c0ab95c9f72` / `5fd6bdb8db43`, expired `2026-08-16T16:24:55+00:00`). Default TTL is 15 minutes (`grok_approve.py:18`). |
| Repeal of `publish-v2.0.6.md:5,7` | **No.** Runbook still says humans own the argv; last mile is still `gh release create`, not Actions. |
| License for this agent to push / tag / release | **No.** docs_researcher is read-only. |
| Transfer of the cd8a96 2.0.5 execute-exception | **No.** `ec0388` already said that exception does not transfer. 2.0.6 needed its own named release demand — that demand is now on file (`864726` + this «go ahead»). |

`AGENTS.md:104`: merge / publish / deploy by Grok Build is banned **without short-lived explicit approval**. Publish **with** a short-lived token is not that ban. If the write owner **executes** `git push` / `gh release create` (the cd8a96 shape) they still run `python3 scripts/grok_approve.py production --reason "publish v2.0.6"` first, as the runbook Checks section already says. A human running the printed commands outside the hook does not need that token.

This agent does not authorize or perform the gated argv.

---

## 5. ADRs and contracts

- `engineering/adr/` is empty. No ADR names Actions as required or equates them with Releases.
- `engineering/contracts/{openapi,asyncapi,schemas}/` have no product APIs. No HTTP/event/data contract requires a workflow or a GitHub Release field.
- `feature-workflow`: a new service / framework / major dependency needs an ADR. Committing the already-implemented GHA ban and running the existing last-mile printer is not a new service.

---

## 6. Facts for the write owner

1. **GitHub Release ≠ GitHub Actions.** Last mile is `gh release create` (GitHub CLI). Do not add `.github/workflows/`. Do not invent `workflow_dispatch` publish.
2. **Last mile is still `python3 scripts/grok_deploy.py`.** It prints the six commands in `publish-v2.0.6.md`. It does not execute them. Dry-run needs this change `ready` + verification/code_review/test_review receipts.
3. **«go ahead» + prior «делай всё полностью вместе с релизом» authorizes the publish outcome** (Latest v2.0.6 after commit + local verify). It does not authorize Actions. It is not a live 15-minute token.
4. Tag the **post-ban commit**, not `549f29d`. Attach digest `55406ff2…`, not `b34af685…`. Leave `v2.0.5` up.
5. Stay `VERSION` 2.0.6. Rebuild only if the commit tree differs from the zip already rebuilt in `9fd274`.
6. Rollback is `gh release delete v2.0.6` + delete that tag only. No force-push.

This report is analysis only.
