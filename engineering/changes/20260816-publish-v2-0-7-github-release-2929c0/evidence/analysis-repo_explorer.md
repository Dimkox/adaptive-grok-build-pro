# Analysis — repo_explorer

Change: `20260816-publish-v2-0-7-github-release-2929c0`  
Route: `2929c09b96b5` · write owner: none · intent: release v2.0.7

Read-only. Local refs + public GitHub HTML. REST API rate-limited. No product edits, tag, push, or `gh release`.

Confirmed: `HEAD` = `origin/main` = `11da31a`; identity still **2.0.6**; GitHub Latest is **v2.0.6** on `e75f3a1`; leftover `11da31a` is on main but unpublished as a release. Next identity is **2.0.7**. No `v2.0.7` tag. No GitHub Actions.

| Check | Fact |
| --- | --- |
| `HEAD` / `refs/heads/main` / `origin/main` | `11da31a3f3e60a0463233cb96c576da8517ddabd` — *Fix 2.0.6 leftovers: installer configs, deploy title, stale notes* |
| GitHub `main` | same tip `11da31a` (`/commits/main`) |
| `VERSION` / `__version__` / README H1 | **2.0.6** local and `raw.githubusercontent.com/.../main/VERSION` |
| GitHub Latest | **Adaptive Grok Build Pro v2.0.6** on [`e75f3a1`](https://github.com/Dimkox/adaptive-grok-build-pro/commit/e75f3a1b92e247279fbb6210d46715a90cf7895c) (16 Aug 18:29). `/releases/latest` = `/releases/tag/v2.0.6` |
| Unpublished leftover | `v2.0.6...main` = **1 commit / 24 files** = `11da31a`. Already on origin; **not** a GitHub Release |
| Next identity | **2.0.7** (patch after published 2.0.6). No `## 2.0.7`, no 2.0.7 zip, no packages/README row |
| Tag `v2.0.7` | **absent** locally (tags stop at annotated `v2.0.6`) and on GitHub (`/tags` top is v2.0.6; `/releases/tag/v2.0.7` 404) |
| Prior tags | `v2.0.6` → `e75f3a1`; `v2.0.5` → `7c0ae75`. Do not retag |
| GHA | **none**. `.github/` missing; no `dependabot.yml`; no `templates/ci/github-actions.yml`; CI README bans Actions |

Do not retag 2.0.6. Do not add GHA. Identity + zip still to be created; last mile is tag `v2.0.7` on the 2.0.7 commit then `gh release create --title`.
