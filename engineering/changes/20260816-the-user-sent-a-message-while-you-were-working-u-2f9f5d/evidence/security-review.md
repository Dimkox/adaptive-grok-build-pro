# Security review — `2f9f5d5bc202`

**PASS**

Route: `2f9f5d5bc202` (intent=`release`, risk=`high`, `write_agent: null`)  
Change: `20260816-the-user-sent-a-message-while-you-were-working-u-2f9f5d`  
Object reviewed: unpublished commit `7152b75b610bada0ecc7468752900ab1515324f1` vs `origin/main` `22762a77ea4133cc34398f9a70194daa427bd096`  
Reviewer: `security_reviewer` (read-only; in `allowed_agents`)  
Inspected: `/adaptive-delivery` + this change package + analysis + `human-approval.md`, local refs, product tree at HEAD vs GitHub raw of `22762a77`, identity files, policy/gitignore, structure tests, public GitHub HTML for `.github`, `pyproject.toml`, `/actions`, `/releases`, `/commits/main`. `.env` was not read. No push, merge, tag, force-push, or GHA from this agent.

No application-code write on this route. Last mile is not executed here.

---

## Verdict in one screen

`7152b75` is one fast-forward docs/tests commit on top of published 2.0.8 (`22762a77`). It moves the agent logs to root, stubs the old `engineering/` paths, and completes the README stack graph to \(K_{10}\). It does **not** restore GitHub Actions, add `pyproject.toml`, ship secrets, bump `VERSION`, tag, or open a GitHub Release.

Authorized last mile after this report: **HTTPS CLI** `git push origin main` of **exactly** `7152b75`. Not authorized: tag, `gh release create`, force-push, GitHub Actions, `git add -A`, `grok_deploy.py` printer, Bitvise/GUI, PHP install.

| Required confirmation | Result |
| --- | --- |
| No secrets in `7152b75` | **PASS.** Product delta is markdown + `tests/test_structure.py`. Workspace secret-scan on the dirty tree: `0 potential secrets`. No `github_pat_` / `ghp_` / `gho_` / PEM / `AKIA…` values. `.env` unopened and gitignored. |
| No GitHub Actions restore | **PASS.** Local `.github/` absent. No `dependabot.yml`. No `github-actions.yml`. GitHub `main/.github` is 404. `/actions` has only historical v2.0.4 / v2.0.5 failures. |
| No `pyproject.toml` | **PASS.** Absent locally. `requirements.txt` / `setup.py` also absent. GitHub `22762a77/pyproject.toml` is 404. Tests still lock all three missing. |
| Last mile is safe if constrained | **PASS.** Fast-forward of `22762a77..7152b75` over HTTPS + `gh` credential helper. Fresh production token required. Do not tag / release / force-push / stage leftover dirt. |

**Authz** is the named gates from «гони» + «продолжай деплой окружения для разработки», already recorded in `evidence/human-approval.md`, scoped to this push only. **Secrets / PII / tenant isolation** are not in play. **Irreversible** actions (tag, `gh release`, force-push, GHA restore) did not happen and are out of scope.

---

## 1. What `7152b75` is

| Probe | Value |
| --- | --- |
| Local `refs/heads/main` / `HEAD` | `7152b75b610bada0ecc7468752900ab1515324f1` |
| Parent (`.git/logs/HEAD`) | `22762a77ea4133cc34398f9a70194daa427bd096` |
| `refs/remotes/origin/main` | still `22762a77` — **not pushed** |
| GitHub `main` tip | still `22762a77` (`Release v2.0.8`) |
| Local tags | `v2.0.0` … `v2.0.7` — **no** `v2.0.8` / `v2.0.9` |
| GitHub Latest Release | `v2.0.7` @ `02376cc` — **no** `v2.0.8` tag or Release |
| Subject | `Document root agent logs and complete K10 stack graph in README` |
| `VERSION` / `__version__` | still `2.0.8` |
| Origin URL | `https://github.com/Dimkox/adaptive-grok-build-pro.git` |

Product delta vs GitHub raw of `22762a77` (this session has no shell; no live `git show --name-only`):

| Path | Origin `22762a77` | Local `7152b75` tree |
| --- | --- | --- |
| `decisions.md` | **404** | NEW canonical log (prior `engineering/` body + move / K10 entries) |
| `mistakes.md` | absent on origin (same class) | NEW canonical log |
| `engineering/decisions.md` | full log | 3-line stub (“Moved” / “Do not append here”) |
| `engineering/mistakes.md` | full log | 3-line stub |
| `AGENTS.md` first bullets | `engineering/decisions.md` / `engineering/mistakes.md` | `decisions.md` / `mistakes.md` |
| `README.md` mermaid | K7, 21 `---` edges | K10, 45 `---` edges + copy-list names |
| `tests/test_structure.py` | no K10 / root-log tests | `test_readme_names_root_self_learning_logs`, `test_readme_stack_graph_is_complete` |

Not in the product identity set: `VERSION`, `CHANGELOG.md` §2.0.8, zips, packager, `install_into.py`, `.github/**`, `pyproject.toml`.

`changed_files` on the stale `2f9f5d` verification receipt is the union of `22762a77...HEAD` **and** unstaged **and** untracked leftover packages (`04ae05`, `0f3d94`, `2a31f5`, this package, ad4090 merge files, …). That list is **not** the commit namelist. Pushing `7152b75` does not send uncommitted files. `git add -A` is forbidden.

---

## 2. Required confirmations

### 2.1 Secrets

Workspace text scan (not `.env`):

- No `github_pat_` / `ghp_` / `gho_` / `BEGIN … PRIVATE KEY` / `AKIA…` values
- No `token|secret|password|api_key = "…"` matches of the `secret-scan` generic regex except test fixtures (`tests/test_verification_doctor.py` fake `'abcde'*5`) and historical review prose
- `tests/test_manifest_package.py` still has the unquoted `GIT_FINE_GRAIN_TOKEN=should-not-pack` fixture (pre-existing; not a live token)
- Stale `2f9f5d` `grok_verify --mode pr` `secret-scan`: **0 potential secrets**

`.gitignore` and `policy.py` `DEFAULT_SECRET_READ` still cover `.env`, `.env.*`, `*.pem` / `*.key` / `*.p12` / `*.pfx`, `id_rsa`, `id_ed25519`, `credentials*`, `secrets/**`. Runtime (`approvals.json`) is gitignored via `.grok-stack/runtime/*`.

`7152b75` product files (`decisions.md`, `mistakes.md`, README mermaid, `AGENTS.md` path rewrite, structure tests) contain no credentials. Local `.env` exists on the operator machine (parent listing only). **Not opened.**

### 2.2 No GitHub Actions restore

| Probe | Result |
| --- | --- |
| Local `.github/` | absent |
| `.github/dependabot.yml` | absent |
| `.grok-stack/templates/ci/github-actions.yml` | absent; CI README still bans Actions |
| Repo `*.yml` / `*.yaml` with `runs-on:` | none in product tree |
| `test_version_is_2_0_8_and_github_actions_are_absent` | still locks VERSION + no workflows / Dependabot / CI template |
| GitHub `main/.github` | **404** |
| `/actions` | **5 historical failures**, all `.github/workflows/adaptive-grok.yml` on **v2.0.4 / v2.0.5** (`097f5c9`, `33a02f1`, `7c0ae75`). **No v2.0.6 / v2.0.7 / v2.0.8 / `7152b75` run.** |

`decisions.md` (now at root) still records “Never GitHub Actions.” This commit does not add a workflow.

GitHub CLI last mile (`git push` via `gh auth git-credential`) is not Actions. `gh release create` is also not Actions and is **out of scope**.

### 2.3 No `pyproject.toml`

| Probe | Result |
| --- | --- |
| Root `pyproject.toml` | does not exist |
| `requirements.txt` / `setup.py` | do not exist |
| `test_product_tree_has_no_packaging_markers` | still locks all three absent |
| GitHub `22762a77/pyproject.toml` | **404** |
| `ruff.toml` / `bandit.yaml` | still the verify config (unchanged) |

Adding a packaging marker would flip `detect_repo` and can skip `python-unittest`. This commit does not do that.

### 2.4 Last mile is not unsafe — if it stays the authorized command

Safe last mile (controller / human, after green verify + both reviews + **fresh** production token):

```
GIT_TERMINAL_PROMPT=0 git -c credential.helper='!gh auth git-credential' push origin main
```

Preconditions that keep it safe:

| Check | Why |
| --- | --- |
| `HEAD` == `7152b75` | only this commit |
| `origin/main` still `22762a77` (re-fetch first) | fast-forward only |
| `22762a77` is ancestor of `HEAD` | linear; no rewrite |
| branch is `main` | no other remote |
| index empty; no `git add -A` | leftover packages stay local |
| no `git tag` / `gh release create` | identity stays unpublished 2.0.8 docs follow-up |
| no `--force` / `-f` | `DESTRUCTIVE_COMMANDS` + rollback = forward-fix |
| no `grok_deploy.py` | printer also emits `package_stack` / `git tag -a v2.0.8` / `gh release create` |
| no Bitvise / `xdg-open` / `gh browse` / `gh auth login` / SSH | origin is HTTPS; 2a31f5 already ruled GUI a false alarm |
| mint new `grok_approve.py production` | row `4dfff07da9e0` expired `2026-08-16T22:20:19+00:00` |

`git push` is a `PRODUCTION_INVOCATIONS` pair. Policy will block agent Bash without a live token. Do **not** reuse the expired row.

If `origin/main` has moved: **stop**. Do not force-push.

---

## 3. Authz, secrets, PII, tenant isolation, irreversible actions

### Authz

Named gates `scope_and_design_approval` and `production_action_approval` are recorded in `evidence/human-approval.md` from «гони» then «продолжай деплой окружения для разработки», scoped to: `git push origin main` of `7152b75` via git/gh CLI.

Not authorized (same file + architect ruling): tag, `gh release create`, force-push, GitHub Actions, Bitvise GUI, sudo install of optional PHP.

`write_agent` is null. This reviewer does not push.

### Secrets

No new credential path. No token in the product delta. Packager / gitignore / secret-read policy unchanged. Local `.env` unopened. Runtime approvals not in git.

### PII

No customer data, no email harvest, no coverage/SaaS upload. Public MIT product tree. Git author email `bpall@mail.ru` already lives on every published commit (including `22762a77`). `.git/config` `user.name` has a leftover CR (`"Dimkox\r"`) — pre-existing clone quirk, not in `7152b75`.

### Tenant isolation

CLI installed into consumer git trees. No multi-tenant data plane. Pushing docs/tests to the public product repo does not read or write another customer’s tree.

### Irreversible actions

None executed by this reviewer.

| Forbidden | Observed |
| --- | --- |
| `git tag` / `git tag -f` / `v2.0.8` / `v2.0.9` | tags still stop at `v2.0.7`; GitHub `v2.0.8` Release 404 |
| `git push` / force-push | `origin/main` and GitHub `main` still `22762a77` |
| `gh release create` / delete / edit | Latest still `v2.0.7` @ `02376cc` |
| Restore `.github/workflows` / Dependabot | still absent locally and on GitHub |
| Add `pyproject.toml` | still absent |
| Read `.env` | not read |
| Stage leftover dirt / second commit | not done here |

Rollback if the later push lands: do **not** force-push. Forward-fix on a new route.

---

## Findings

No blocking findings.

| ID | Severity | Item | Disposition |
| --- | --- | --- | --- |
| S1 | Residual (process) | Expired production row `4dfff07da9e0` (expired 22:20Z) still on disk | Wrong window. Do not reuse. Mint a fresh 15-minute token immediately before push. |
| S2 | Residual (process) | Working tree is dirty with leftover change packages | `git push` of `7152b75` does not send them. `git add -A` / a second commit would. |
| S3 | Residual (accepted) | No live `git show --name-only 7152b75` (no shell on this release route) | Parent log + GitHub raw of `22762a77` + a13da8 implementation/code-review. Same bar as prior reviews. |
| S4 | Residual (accepted) | Stale `2f9f5d` verification receipt (`3e2275c…`, stale after later evidence writes) | Expected. Controller re-verifies after the last `*.md` write. Secret-scan on that pass was already 0. |
| S5 | Historical, not this commit | Five failed Actions runs on v2.0.4 / v2.0.5 | Workflows banned since `e75f3a1`. This commit does not restore them. |
| S6 | Observational | GitHub Latest is still `v2.0.7` while `main` is already 2.0.8 `22762a77` | Out of scope. Do not close that gap on this route. |

---

## Recommendation

**PASS.** Treat `7152b75` as an authorized unpublished docs/tests fast-forward of 2.0.8: no GHA, no `pyproject.toml`, no packed/committed secrets.

Last mile after independent `release_review` + fresh `grok_verify --mode pr` + fresh production approval:

```
GIT_TERMINAL_PROMPT=0 git -c credential.helper='!gh auth git-credential' push origin main
```

Do not tag. Do not `gh release create`. Do not force-push. Do not add GitHub Actions. Do not add `pyproject.toml`. Do not read `.env`. Do not publish from this review.
