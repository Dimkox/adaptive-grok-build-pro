# Codex SEO Landing Side Project Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable Codex SEO landing skill and an isolated Russian static showcase.

**Architecture:** Adapt upstream commit `1aa908f96a09e2e93fd1839ac51b02d362e7a8ef` into `.agents/skills/seo-landing/` with Codex metadata and retained MIT provenance. Keep the dependency-free showcase under `side-projects/seo-landing-showcase/` and non-indexable until a real production origin is supplied.

**Tech Stack:** Codex Agent Skills, semantic HTML5, CSS, optional vanilla JavaScript, Python `unittest`, Codex `quick_validate.py`, repository verification scripts.

**Spec:** `docs/superpowers/specs/2026-09-01-seo-landing-codex-side-project-design.md`

## Global Constraints

- Preserve upstream license, authorship, exact commit, and import date.
- Modes are `generate`, `audit-only`, and `fix-existing`; audit-only never writes.
- Generate and fix-existing stop for explicit HTML approval before validation.
- Never invent domains, claims, legal text, endpoints, asset rights, schema facts, or measured results.
- Showcase has no form, analytics, external runtime resource, or fabricated result.
- Showcase uses `noindex, nofollow` and no canonical until a production origin exists.
- No framework, dependency, GitHub Actions workflow, or Trust CI behavior change.
- PR base is `fix/path-aware-shell-policy-circuit-breaker`, not `main`.

---

### Task 1: RED and Atomic Protected Skill Import

**Files:**
- Create: `.agents/skills/seo-landing/{SKILL.md,LICENSE,README.md,README.ru.md,SECURITY.md,UPSTREAM.md}`
- Create: `.agents/skills/seo-landing/agents/openai.yaml`
- Create: `.agents/skills/seo-landing/references/{tech-spec,server-config,video-facade,map-facade}.md`
- Create: `tests/test_seo_landing_side_project.py`
- Modify: `README.md`, `decisions.md`

**Interfaces:** Consumes reviewed upstream; produces `$seo-landing` and executable contracts.

- [ ] Run RED missing-package check:

```bash
test -f .agents/skills/seo-landing/SKILL.md && test -f .agents/skills/seo-landing/agents/openai.yaml
```

Expected: exit `1`.

- [ ] Run RED upstream validation:

```bash
python3 /home/pall/.codex/skills/.system/skill-creator/scripts/quick_validate.py /tmp/seo-landing-architecture.drnnpb/repo
```

Expected: exit `1`, `Description cannot contain angle brackets (< or >)`.

- [ ] Obtain one exact protected grant for `.agents/skills/seo-landing/**`, `tests/test_seo_landing_side_project.py`, `README.md`, and `decisions.md`; apply all four targets in one `apply_patch` batch.
- [ ] In tests assert safe frontmatter, all three mode names, audit no-write wording, explicit approval stop, exact upstream commit, `$seo-landing` UI prompt, retained MIT notice, and showcase contracts.
- [ ] Use this Codex metadata:

```yaml
interface:
  display_name: "SEO Landing"
  short_description: "Generate, audit, and optimize static SEO landings"
  default_prompt: "Use $seo-landing to generate, audit, or optimize the requested SEO landing with measured evidence."
```

- [ ] Record in `UPSTREAM.md` the URL, exact commit, import date `2026-09-01`, MIT license, and local adaptations; update README nodes/complete graph and log the isolation decision in at most three sentences.

---

### Task 2: Static Noindex Showcase

**Files:**
- Create: `side-projects/seo-landing-showcase/index.html`
- Create: `side-projects/seo-landing-showcase/styles.css`
- Create: `side-projects/seo-landing-showcase/README.md`
- Create only if required: `side-projects/seo-landing-showcase/script.js`

**Interfaces:** Consumes `$seo-landing`; produces locally servable Russian product documentation.

- [ ] Write semantic HTML with skip link, landmarks, one H1, mode/workflow/guarantee/invocation/provenance sections, `<meta name="robots" content="noindex, nofollow">`, and no canonical, form, analytics, external runtime URL, or origin-bound JSON-LD.
- [ ] Write 320 px-safe CSS with system fonts, WCAG AA contrast, visible `:focus-visible`, and `prefers-reduced-motion: reduce`; omit JavaScript unless a necessary interaction cannot be native.
- [ ] Document local serving:

```bash
python3 -m http.server 4173 --directory side-projects/seo-landing-showcase
```

- [ ] Run focused GREEN tests:

```bash
python3 -m unittest tests.test_seo_landing_side_project -v
```

Expected: all skill, provenance, security, and showcase contracts pass.

---

### Task 3: Change Package and Verification

**Files:**
- Update: `engineering/changes/20260901-codex-seo-landing-side-project-23b06c/{brief,requirements,architecture,test-plan,rollback,release,tasks}.md`
- Update: `engineering/changes/20260901-codex-seo-landing-side-project-23b06c/change-spec.yaml`
- Create: `engineering/changes/20260901-codex-seo-landing-side-project-23b06c/evidence/red-baseline.md`

**Interfaces:** Consumes implementation and RED/GREEN output; produces complete local evidence.

- [ ] Fill every package field with approved scope, acceptance criteria, risks, rollback, noindex boundary, exact evidence refs, protected-path scope, and stacked delivery decision; remove every template marker.
- [ ] Record both RED commands, exit codes, and outputs in `red-baseline.md`.
- [ ] Validate skill and repository:

```bash
python3 /home/pall/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/seo-landing
python3 scripts/grok_verify.py --mode pr
```

Expected: `Skill is valid!`; repository base/frontend profiles pass.
- [ ] Serve the showcase and inspect 320, 768, 1280, and 1920 px for overflow, headings, focus, and reduced motion; record measured observations, never estimates.
- [ ] Commit with `git commit -m "feat: add Codex SEO landing side project"` after `git diff --check` and a clean focused test rerun.

---

### Task 4: Independent Reviews and Stacked PR

**Files:**
- Create: `engineering/changes/20260901-codex-seo-landing-side-project-23b06c/evidence/{code-review,test-review}.md`

**Interfaces:** Consumes exact committed diff; produces review receipts and a stacked PR awaiting Trust CI.

- [ ] Dispatch route-selected `code_reviewer` and `test_reviewer`; repair findings through the sole write owner, rerun Task 3 checks, and refresh stale receipts.
- [ ] Record passing reports:

```bash
python3 scripts/grok_review.py code_review --status pass --report engineering/changes/20260901-codex-seo-landing-side-project-23b06c/evidence/code-review.md
python3 scripts/grok_review.py test_review --status pass --report engineering/changes/20260901-codex-seo-landing-side-project-23b06c/evidence/test-review.md
```

- [ ] Confirm stack and diff:

```bash
git merge-base --is-ancestor 7c61e3b647924e5667d171d8b286e5d79b8a4efe HEAD
git diff --check fix/path-aware-shell-policy-circuit-breaker...HEAD
```

- [ ] With exact push delegation, push `feature/seo-landing-codex-side-project` and open a PR whose base is `fix/path-aware-shell-policy-circuit-breaker`.
- [ ] Wait for the GitHub App-owned `adaptive-trust-ci/verified@<policy-sha12>` on the exact head SHA; do not merge, tag, release, or deploy without separate exact authority.
