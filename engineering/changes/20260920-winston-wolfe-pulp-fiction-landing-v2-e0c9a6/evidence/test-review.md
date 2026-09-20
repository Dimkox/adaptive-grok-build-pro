# Test review — Winston Wolfe Pulp Fiction landing v2

**Agent:** test_reviewer (route `e0c9a65c0d53`, `allowed_agents` on the change package).  
**Verdict:** **FAIL** for merge-quality local test evidence. Characterization tests **pass when invoked by path**, but they are **not on the verifier discovery path**, and the skill **STOP POINT** (Lighthouse / host crawl / `browser-contract.mjs`) is **unrun (BLOCKER)**.

**Change package:** `engineering/changes/20260920-winston-wolfe-pulp-fiction-landing-v2-e0c9a6`  
**Tests reviewed:** `evidence/test_winston_wolfe_seo_landing_v2.py` (3 methods, `unittest`). Direct run: `Ran 3 tests … OK`.

## Route and bindings

Typed `change-spec.yaml` AC-001..003 bind to the three methods in the evidence file (not `tests/`). AC-004 is receipts (`verification`, `code_review`, `test_review`). INV-001 binds existing `tests/test_seo_landing_side_project.py::SeoLandingSkillTests.test_exact_package_inventory_and_codex_metadata`. INV-002 is verification of empty contracts.

`requirements.md` AC-001..007 is **not byte-aligned** with typed spec IDs (noindex/forms/images split across spec AC-002/003). Review uses **typed spec as authority**, with requirements as extra coverage questions.

## Showcase / skill mutation

`git status --short` on `tests/test_seo_landing_side_project.py`, `side-projects/seo-landing-showcase`, and `.agents/skills/seo-landing` showed **no dirty product files** (only untracked `evidence/test_winston_wolfe_seo_landing_v2.py` in the combined listing). INV-001 is **not re-executed in this evidence file**; it relies on the existing suite remaining green. That is acceptable for “did not mutate,” not a substitute for a recorded `python3 -m unittest tests.test_seo_landing_side_project` receipt in this package.

## AC coverage (typed spec)

| ID | Statement (abbrev.) | Test | Adequacy |
| --- | --- | --- | --- |
| AC-001 | Tree + local assets exist | `test_project_tree_and_local_assets_exist` | **Covered:** robots, favicon, ASSETS, SERVER-SETUP; no sitemap/script.js/styles.css; hashed hero/method families at 320–1920 × avif/webp/jpg; every HTML/CSS local URL resolves under the project. |
| AC-002 | ru-RU, ltr, one H1, no invented origin/form | `test_language_landmarks_noindex_and_no_form` | **Mostly covered:** lang/dir, charset before title, one H1, noindex/nofollow, no canonical/og:url, no form/mailto/tel/iframe/svg/video, landmarks, robots `Disallow: /` without Sitemap. **Gap vs requirements AC-002:** “visible unofficial-fan attribution” is only weakly proxied by `"не услуга"` casefold, not an explicit tribute/disclaimer string. JSON-LD origin is **not** asserted in this method. |
| AC-003 | First-party first-load; no likeness claims in ASSETS.md | `test_no_external_runtime_urls_or_likeness_claims` | **Covered** via shared `external_runtime_urls`; system-ui; focus-visible; reduced motion; ASSETS “no actor likeness” / Russian equivalent; no “harvey keitel” in ASSETS; JSON-LD types ⊆ Movie/Person/FAQPage. **Gaps:** method `<img loading="lazy">` not asserted; LCP `fetchpriority="high"` lives in AC-002 test, not here; HTML body *may* mention Harvey Keitel (copy) — only ASSETS is blocked; invented JSON-LD `@id` host is not regex-checked (current graph uses Wikidata Q104123, which is fine, but unenforced). |

FORBID-001 (forms, likeness, skill/showcase, GHA, Trust CI) is bound to **code_review receipt**, not tests. Tests still encode several of those negatives.

## Gaps (material)

1. **Unittest discovery:** `grok_verify` python-unittest uses `discover -s tests`. There is **no** `tests/test_winston_wolfe_seo_landing_v2.py` (protected-path deny). CI/PR unittest will **not** run this landing contract unless someone invokes the evidence path. `test-plan.md` still names `tests/test_winston_wolfe_seo_landing_v2.py`. **Mismatch.**
2. **Lighthouse / Nu / crawl-on-host / `browser-contract.mjs`:** not run. Skill STOP POINT. Viewport overflow 320/768/1280/1920 is P1 in the test plan and **skipped**. Unrun gates are **BLOCKER**, not scores.
3. **Method image lazy** and **hero not lazy** (beyond LCP regex) — incomplete AC-005 from requirements.
4. **Copy claims** (official affiliation, prices, guarantees) — only Lighthouse/PageSpeed/WCAG regex; no price/phone/messenger assertions.
5. **INV-001** not executed in this package’s evidence run.
6. No characterization of CSP hashes vs actual inline style/script, `form-action 'none'`, or `images/_source` not referenced from HTML.

## Is local test evidence enough for a PR of this side-project?

**No.** For a static fan landing, three focused tests **directly run** are a good contract for AC-001 and most of AC-002/003, and they **passed**. They are **insufficient** as PR gate evidence because:

- they will **not** execute under repository `python-unittest` discovery;
- browser overflow / Lighthouse / HTML-approval STOP POINT remain **BLOCKER**;
- typed AC-004 still needs a **fresh** `verification` receipt after the product tree, plus independent code review.

**Pass condition for a later test_review:** land tests under `tests/` (or extend verifier discovery), re-run INV-001, record browser-contract skip-or-pass with Node/Chrome facts, and keep Lighthouse as explicit unrun-until-HTML-approval rather than implied green.

## Recommendation

Keep **FAIL** on `scripts/grok_review.py test_review` until discovery + STOP POINT are addressed or explicitly accepted in the change package as residual with a named skip. Do not treat the evidence-path `OK` as Trust CI or merge authority.
