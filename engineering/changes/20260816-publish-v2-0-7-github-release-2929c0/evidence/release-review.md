# Release review — `2929c09b96b5` (re-check)

Reviewer: `release_reviewer` (read-only). Write owner: **none**.
Change: `engineering/changes/20260816-publish-v2-0-7-github-release-2929c0`
Intent: `release` · risk: `high` · profiles: `base`
Supersedes the prior FAIL on this path. Official `python3 scripts/grok_verify.py --mode pr` is now **PASS**.

Assigned re-check: ship still `02376cc`, zip digest still `ec48d317…`, no GHA, do not retag 2.0.6. GO/NO-GO for tag / push / `gh release create --title "Adaptive Grok Build Pro v2.0.7"`.

Fetched: 2026-08-16 (local refs + public GitHub HTML). Did not recompute zip bytes. Did not push, tag, merge, deploy, or call `gh`.

**PASS.** **GO** to last-mile tag / push / `gh release create` of **v2.0.7** on `02376cc` with `--title "Adaptive Grok Build Pro v2.0.7"`.

**NO-GO** to retag `v2.0.6`, rebuild the zip, add GHA, or publish from this agent.

| Check (assigned) | Result |
| --- | --- |
| Ship is still `02376cc` identity 2.0.7 | **PASS** |
| Zip digest still `ec48d317…` | **PASS** |
| No GHA | **PASS** |
| Do not retag 2.0.6 | **PASS** (still frozen) |
| `grok_verify --mode pr` | **PASS** (181 tests OK; ruff / bandit / coverage green) |
| Ready to tag / push / `gh --title Adaptive Grok Build Pro v2.0.7` | **GO** |
| Rollback scoped to `v2.0.7` only | **PASS** |
| Observability plan | **PASS** |

Do not push, merge, deploy, retag, or run `gh release` from this review.

## Verdict

| Gate | Result |
| --- | --- |
| Ship commit | **PASS.** Local `HEAD` / `refs/heads/main` still `02376cc097d7640d56dd308b98efe4e026f4c253` — *Release v2.0.7: leftover 2.0.6 fixes as a published identity*. Parent still `11da31a`. HEAD has not moved since the first review. |
| Identity surfaces | **PASS.** `VERSION` = `2.0.7`; `__version__` = `"2.0.7"`; README H1 = `# Adaptive Grok Build Pro v2.0.7`; CHANGELOG top = `## 2.0.7 — 2026-08-16`; tests pin `2.0.7`. |
| Artifact / provenance | **PASS.** `packages/` and `dist/` sidecars still `ec48d3174248e15e241519546b1414a7698857509cf97ac61e078dbd204de01c  adaptive-grok-build-pro-v2.0.7.zip`. |
| Frozen prior releases | **PASS.** Annotated `v2.0.6` still `8e7c5b67…` → peel `e75f3a1`. GitHub Latest is still **Adaptive Grok Build Pro v2.0.6** on [`e75f3a1`](https://github.com/Dimkox/adaptive-grok-build-pro/commit/e75f3a1b92e247279fbb6210d46715a90cf7895c). No local `v2.0.7` tag. 2.0.6 zip still `55406ff2…`. 2.0.5 zip still `b80e6310…`. |
| No GHA / no packaging markers | **PASS.** `.github/` absent. No `pyproject.toml` / `requirements.txt` / `setup.py`. |
| Quality gate | **PASS.** Receipt 2026-08-16T19:54:06Z, fingerprint `52b580c397764ba4193eecc0d333be9abf3702fb07caca0d84c1cdd62550b2a3`, `status=pass`. ruff pass, bandit pass, python-unittest **181 OK**, coverage 76% (ratchet 74). The earlier fail was the one-off `project_copy` race on `.last-fingerprint.json.*`. |
| Last mile | **GO** for controller/human on SHA-pinned `02376cc` after a live production token. This agent does not execute. |
| Product mutation by this agent | **PASS / empty.** Overwrote only this report. No product edits. No `.env`. No publish. |

## 1. Identity and artifact (unchanged)

`e75f3a1` (published `v2.0.6`) → `11da31a` (leftovers, still 2.0.6) → **`02376cc`** (2.0.7 ship).

`origin/main` / GitHub `main` remain `11da31a` (`raw.githubusercontent.com/.../main/VERSION` was 2.0.6 at first review; Latest page still shows 1 commit since `v2.0.6`). Expected. Last mile pushes `02376cc` to `main`.

`dist/RELEASE-NOTES.md` still starts with `## 2.0.7 — 2026-08-16`. Use it as `--notes-file`. Do **not** run `package_stack` again.

## 2. Verification — prior FAIL cleared

`.grok-stack/runtime/receipts/2929c09b96b5/verification.json`:

| Check | Status |
| --- | --- |
| git-diff-check | pass |
| secret-scan | pass (0 potential secrets) |
| ruff | pass |
| bandit | pass |
| python-unittest | **pass** — Ran 181 tests in 38.980s — OK |
| coverage | pass (76%) |
| overall | **pass** |

`last-fingerprint.json` matches that receipt (`52b580c3…`) before this report write. Writing this file will move the working-tree fingerprint; that is session paperwork, not a new ship. Do not retag. Do not rebuild the zip.

## 3. Rollback — GO as v2.0.7-only withdraw

```bash
gh release delete v2.0.7 --yes
git push origin :refs/tags/v2.0.7
git tag -d v2.0.7
```

Do not touch `v2.0.6` / `v2.0.5`. No force-push. No `git tag -f`.

## 4. Observability — GO for this product shape

Stdlib CLI plus a GitHub Release card. No APM required.

After last mile, confirm:

| Signal | Expected |
| --- | --- |
| `/releases/latest` H1 | `Adaptive Grok Build Pro v2.0.7` |
| Latest badge | on `v2.0.7` only |
| Tag peel | `02376cc097d7640d56dd308b98efe4e026f4c253` |
| Notes first heading | `## 2.0.7 — 2026-08-16` |
| Zip asset | digest `ec48d317…` |
| `v2.0.6` | still exists, peel `e75f3a1`, zip `55406ff2…` |
| `v2.0.5` | still exists, peel `7c0ae75` |

Any miss is a stop, not `-f` / recreate 2.0.6.

## 5. Remaining risk (do not expand scope)

1. **Live production token required** for agent-side `git push` / `gh release create`. Current `approvals.json` rows are leftover-push, expired 19:41:43Z, wrong reason. Mint `python3 scripts/grok_approve.py production --reason "publish v2.0.7 tag and GitHub Release"`. Human terminal may skip the token; argv stay the same.
2. **SHA-pin `02376cc`.** `git push origin 02376cc097d7640d56dd308b98efe4e026f4c253:refs/heads/main` (or `git push origin main` iff `HEAD` is still that SHA). Do not let later paperwork ride the publish.
3. **Skip packager / `cp`.** Zip is already the ship digest.
4. **Working tree is dirty** (this change package, this report). Tag the commit, not the dirty tree. No `git add -A`.
5. **Zip embeds `engineering/changes/**`.** Accepted residual. Do not add excludes.
6. **Cosmetic leftovers.** `packages/README.md` lists 2.0.7 below 2.0.6; CHANGELOG §2.0.7 is shorter than the architect draft. Do not restage.
7. **No GHA / no `pyproject.toml`.** Keep absent.
8. **MCP `create_release`.** Forbidden second publisher.
9. **`security_review` receipt** is a parallel required kind. This PASS is independent.

## 6. GO / NO-GO

| Act | Decision |
| --- | --- |
| Tag / push / `gh release create v2.0.7` on `02376cc` with `--title "Adaptive Grok Build Pro v2.0.7"` and zip `ec48d317…` | **GO** (controller or human; not this agent) |
| Leave `v2.0.6` on `e75f3a1` / zip `55406ff2…` | **GO** |
| Leave `v2.0.5` on `7c0ae75` / zip `b80e6310…` | **GO** |
| Retag / `-f` / delete / edit `v2.0.6` or `v2.0.5` | **NO-GO** |
| Rebuild zip / add GHA / add `pyproject.toml` / MCP create | **NO-GO** |
| This reviewer executing last mile | **NO-GO** |

Last-mile argv (controller/human only):

```bash
git tag -a v2.0.7 02376cc097d7640d56dd308b98efe4e026f4c253 -m "v2.0.7"
git push origin 02376cc097d7640d56dd308b98efe4e026f4c253:refs/heads/main
git push origin v2.0.7
gh release create v2.0.7 \
  packages/adaptive-grok-build-pro-v2.0.7.zip \
  packages/adaptive-grok-build-pro-v2.0.7.zip.sha256 \
  --title "Adaptive Grok Build Pro v2.0.7" \
  --notes-file dist/RELEASE-NOTES.md \
  --verify-tag
```

## What this review is not

- Not this agent publishing.
- Not a second `package_stack`.
- Not a retag of `v2.0.6`.
- Not a security review.
- Did not read `.env`. Did not push, merge, deploy, or call `gh`.

## Stop

**PASS.**

- **GO:** last mile of `v2.0.7` on `02376cc`, zip `ec48d317…`, title `Adaptive Grok Build Pro v2.0.7`.
- **NO-GO:** retag 2.0.6, rebuild zip, GHA, this agent publishing.
- Rollback: delete `v2.0.7` release + tag only.
- Observability: GitHub title + Latest badge + peel `02376cc` + zip `ec48d317…` + surviving 2.0.6 card; local `grok_verify` PASS.
