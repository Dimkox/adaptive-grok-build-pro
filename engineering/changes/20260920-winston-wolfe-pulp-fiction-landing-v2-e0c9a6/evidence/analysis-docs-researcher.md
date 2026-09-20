# docs_researcher — optional generated SEO landing constraints

Change: `20260920-winston-wolfe-pulp-fiction-landing-v2-e0c9a6`  
Route: `e0c9a65c0d53`  
Scope: recover documented requirements for adding an **optional generated landing side project**. No APIs invented. Read-only except this report.

**Fact:** there is **no Winston Wolfe / Pulp Fiction landing in this tree**. `side-projects/` contains only `seo-landing-showcase/`. There is **no** `side-projects/seo-landings/` directory yet. README map lists the skill and the showcase only.

---

## 1. Output directory (required)

Source: `.agents/skills/seo-landing/SKILL.md` §1.

- Default: create every generated project under `side-projects/seo-landings/<project-slug>/`.
- **Never** write generated landing files to the workspace root.
- Another dedicated directory is allowed **only** when the user explicitly names it.
- Multi-file project; every local resource referenced by HTML must exist as a real file.

Required tree (skill):

```
side-projects/seo-landings/<project-slug>/
  index.html
  styles.css          # only if below-the-fold CSS is deferred
  script.js           # only if the page uses JS; single file, defer
  images/
  favicon.png
  ASSETS.md
  robots.txt
  sitemap.xml
  SERVER-SETUP.md
```

`references/tech-spec.md` OUTPUT contract matches that file set. Referenced-but-missing files are a generation failure.

Showcase vs generated landing:

| Path | Role |
| --- | --- |
| `.agents/skills/seo-landing/` | Reusable skill (PR #19) |
| `side-projects/seo-landing-showcase/` | Non-indexable Russian **capability** showcase; not a customer landing |
| `side-projects/seo-landings/<slug>/` | Canonical **generated** landing output (not present in repo today) |

Do not overwrite the showcase. Prior L5 analysis (`engineering/changes/20260904-l5-multimodal-landing-dogfood-9f67ef/evidence/analysis-repo-explorer.md`) says keep the showcase as a fixture and put generated output on the `seo-landings/<slug>/` path.

`architecture/system.yaml` `NODE-SEO-SHOWCASE-LAB` currently lists only `.agents/skills/seo-landing` and `side-projects/seo-landing-showcase`. It does **not** list `side-projects/seo-landings/`.

---

## 2. Indexing without a domain (required)

Skill (`SKILL.md` §0a): Domain / final URL is **required** for canonical, `og:url`, absolute paths, JSON-LD `@id`. If domain or keywords are missing — **ask first, do not invent them**.

Tech-spec §3 default production SEO (when a real origin exists): `index, follow`, absolute canonical, OG URL, sitemap `<loc>` matching canonical, `robots.txt` with fully qualified `Sitemap:`.

**Without a production origin**, repository practice is the **showcase indexing boundary**, not invented `https://site.com/` URLs:

- `side-projects/seo-landing-showcase/README.md`: page has `noindex, nofollow` and **no** canonical or `og:url` because production origin is not set. Enabling indexing requires a **separate** change with a real canonical URL and re-check of absolute links.
- `docs/superpowers/specs/2026-09-01-seo-landing-codex-side-project-design.md` “Showcase Indexing Boundary”: no hostname → `noindex, nofollow`; no canonical, OG URL, sitemap, or JSON-LD identifier that would require an invented public origin. Indexing only in a later change that receives the real origin.
- `engineering/changes/20260901-codex-seo-landing-side-project-23b06c/brief.md`: showcase remains `noindex, nofollow` until a real canonical origin is supplied. Out of scope: customer-specific generated landing, production hostname, hosting, analytics, lead backend.
- `decisions.md` 2026-09-01: showcase remains `noindex, nofollow` until a real production origin is supplied and verified.

**Required for a generated landing with no domain:** do not invent canonical/OG/JSON-LD absolute origins; do not claim indexability. Follow the same pre-production safety: `noindex, nofollow`, omit origin-bound identifiers until a real URL is collected. Crawlability/Lighthouse SEO gates that need a deployed host are **BLOCKER**, not fabricated passes (`SKILL.md` §5, tech-spec §7).

---

## 3. PR-only delivery (required)

`AGENTS.md`:

- All product changes go through an isolated branch and pull request.
- Direct push to `main` or another protected/shared branch is prohibited.
- Local `grok_verify --mode pr` and route reviews are **preflight only**.
- Merge only after App-owned `adaptive-trust-ci/verified@<policy-sha12>` on the exact PR head (deployed name currently `adaptive-trust-ci/verified@06ecf1c875bc` per README / `PROJECT_STATE.json`).

`START_HERE.md`: follow PR-only delivery; never bypass the exact-SHA App-owned Trust CI check.

Codex SEO brief: merge, tag, release, production deployment **out of scope** for that side-project change. Same operational boundary applies unless the user separately delegates those actions.

---

## 4. No GitHub Actions (required)

`AGENTS.md`: never use GitHub Actions; do not add `.github/workflows/` or any GitHub Actions dependency.

`START_HERE.md` item 6: never add GitHub Actions.

`README.md` current-state: **No GitHub Actions**.

`PROJECT_STATE.json` `trust_ci.no_github_actions`: true.

Codex SEO brief: no changes to Trust CI, workflow dispatch, branch protection, dependencies, or GitHub Actions.

---

## 5. README before push vs architecture views (conditional)

`AGENTS.md` **README before push**:

- Trigger is **before proposing a release**, not every PR.
- Then update `README.md` so it matches the tree: VERSION, what exists, where it lives, how pieces connect.
- Keep README links to `architecture/system.yaml`, `architecture/rules.yaml`, and `architecture/generated/` current. Do not propose a **release** whose architecture links or current-state section are behind the tree.

`AGENTS.md` **Skip no-op checks**: if the product tree **did** change, run `python3 scripts/grok_verify.py --mode pr`. Adding files under `side-projects/seo-landings/` is a product-tree change → **verify required**. Analysis/review skip applies only when the product tree did not change.

Current README already documents:

- `.agents/skills/seo-landing/` — optional Codex SEO landing skill
- `side-projects/seo-landing-showcase/` — non-indexable Russian showcase

It does **not** mention `side-projects/seo-landings/` or any Winston Wolfe page.

### Required vs optional for a side-project-only change (no release)

| Artifact | Side-project-only PR (not a release) | If proposing a release |
| --- | --- | --- |
| Isolated branch + PR | **Required** | Required |
| Trust CI App check | Required for merge | Required |
| No GitHub Actions | **Required** | Required |
| `grok_verify --mode pr` | **Required** if product files change | Required |
| Root `README.md` map/current-state | **Optional** for a non-release PR; not demanded by “README before push” unless a release is proposed. Optional update if implementers want the map to list the new generated slug. | **Required** so README matches the tree |
| `architecture/system.yaml` / generated views | **Not required** solely because a generated landing was added. Node today covers skill + showcase only. Expand the model only with explicit architectural justification (`AGENTS.md` development discipline). | Architecture **links** in README must stay current; regenerate views only if the model actually changed |
| `START_HERE.md` / `PROJECT_STATE.json` | **Not required** for a local side landing; those files describe product/release/pilot state, not generated landings. START_HERE notes PR #19 delivered the optional SEO side project. | Only if the release narrative must mention new tree content |
| `decisions.md` | Optional unless a reusable ruling is needed (existing 2026-09-01 isolation/noindex decision already covers the pattern) | Optional |
| Showcase `README.md` | Do not treat as the generated landing contract | Unchanged unless showcase itself changes |

---

## 6. Other recovered constraints (generate mode)

From skill + tech-spec (not invented):

- Collect domain, language/direction/locale separately, keywords, business type, CTA; never invent identity, prices, reviews, or media facts.
- Stop point: show HTML and wait for user confirmation **before** validation/metrics.
- No external JS/CSS libraries, external fonts, or SVG images.
- JS budget ≤ 15 KB, one deferred file.
- Forms require a real submission destination or must be omitted/stubbed.
- Codex repository safety: no `.env`/secrets; no deploy/publish without exact authorization.
- Codex SEO change out of scope: customer landing **was** out of scope for PR #19; a **new** change may add a generated landing, but still without hostname/hosting/analytics/lead backend unless collected.

`mistakes.md` SEO-adjacent: do not copy showcase `noindex` into a spec that claims an indexed production target (2026-09 L5). For this task, no domain is documented → keep noindex; do not mix with “index, follow” from tech-spec §3.

---

## 7. What this change may do vs must not

**May (documented):** generate under `side-projects/seo-landings/<slug>/` using `$seo-landing` generate mode; keep noindex until a real origin exists; deliver via PR; leave Trust CI and GitHub Actions untouched.

**Must not:** write landings at repo root; invent a domain/canonical; index without origin; push to `main`; add GitHub Actions; treat the showcase as the Winston Wolfe page; claim a Winston Wolfe landing already exists (it does not).

**Not required** for a side-project-only, non-release PR: rewriting root README current-state, regenerating architecture views, or editing `PROJECT_STATE.json` / `START_HERE.md` solely to mention the landing.
