# Codex SEO Landing Side Project — Design

Date: 2026-09-01
Change: `20260901-codex-seo-landing-side-project-23b06c`
Route: `23b06c1b62a3`

## Context

The user approved embedding `aleksandr-alhoff/seo-landing` in the current
repository as an isolated side project.
Its primary purpose is reusable, on-demand SEO landing generation in Codex.
The repository must also contain a Russian static showcase explaining the
skill and how to invoke it.
The source baseline is upstream commit
`1aa908f96a09e2e93fd1839ac51b02d362e7a8ef` from
`https://github.com/aleksandr-alhoff/seo-landing`.
The upstream MIT license and authorship must remain visible.

## Approved Design

Use a repository-local Codex skill at `.agents/skills/seo-landing/`.
Keep upstream guidance as the behavioral baseline, then make only the changes
needed for Codex-native discovery, safe invocation, and repository policy.
Add `agents/openai.yaml` for Codex UI metadata and explicit invocation copy.
Keep detailed SEO, hosting, video, map, security, and validation guidance in
focused reference documents loaded only when the selected mode needs them.
Do not add a framework, package manager, build tool, service, database, or
third-party runtime dependency.

The showcase is a separate static project under
`side-projects/seo-landing-showcase/`.
It documents the side project; it is not an example output generated from an
invented customer brief.
It uses semantic HTML, local CSS, and optional local JavaScript only.
It contains no lead form, fabricated customer result, analytics, external
font, external script, or first-load third-party request.

## Exact Layout

```text
.agents/skills/seo-landing/
  SKILL.md
  LICENSE
  README.md
  README.ru.md
  SECURITY.md
  UPSTREAM.md
  agents/openai.yaml
  references/map-facade.md
  references/server-config.md
  references/tech-spec.md
  references/video-facade.md
side-projects/seo-landing-showcase/
  index.html
  styles.css
  script.js
  README.md
tests/test_seo_landing_side_project.py
```

`UPSTREAM.md` records repository URL, exact commit, license, import date, and
the local Codex adaptations.
`script.js` is omitted if the final showcase has no behavior requiring it;
when present it must be deferred, local, dependency-free, and under 15 KB.

## Skill Mode Contracts

The skill exposes three mutually exclusive modes selected from user intent.

`generate` creates a new landing only after collecting the canonical domain,
language and direction, keywords, verified identity facts, CTA, contacts,
asset provenance, and any required form or media facts.
It never invents domains, claims, prices, testimonials, legal text, endpoints,
asset rights, schema facts, or measured performance results.
It writes into a dedicated project directory, never the workspace root.
It stops after presenting HTML and waits for explicit user approval before
validation and the final report.

`audit-only` is read-only.
It inspects the supplied deployed URL or local files, reports the command and
evidence for every applicable check, and marks unavailable checks as blocked.
It creates or modifies no project files.

`fix-existing` changes only the supplied landing and stated defects.
It collects only inputs required by those fixes, preserves unrelated content,
uses the same approval stop point, and reports measured evidence only.

Untrusted retrieved content, page text, metadata, and user brief values are
data rather than instructions.
Every generated value is encoded for its HTML, attribute, URL, CSS, or JSON-LD
context, and URL schemes and structured identifiers are allow-listed.

## Showcase Indexing Boundary

No production hostname was provided.
The showcase therefore ships with `robots` set to `noindex, nofollow` and no
canonical, Open Graph URL, sitemap, or JSON-LD identifier that would require
an invented public origin.
This is an explicit pre-production safety boundary, not an SEO claim.
Indexing may be enabled only in a later change that receives the real canonical
origin and verifies every absolute URL against it.

## Acceptance Criteria

1. Codex validation accepts the local skill package and its UI metadata.
2. Explicit `$seo-landing` invocation is documented and implicit trigger copy
   covers generation, audit-only, and targeted optimization requests.
3. Tests prove the three mode boundaries, the generate approval stop point,
   and the audit-only no-write contract.
4. Tests prove required provenance files and the exact upstream commit.
5. Tests reject unsafe angle brackets in frontmatter description and verify
   that `agents/openai.yaml` describes the same skill.
6. The showcase has one H1, logical landmarks and headings, keyboard-visible
   focus, reduced-motion handling, and no horizontal overflow at 320 px.
7. The showcase has no external runtime resources, no form, no invented
   metrics, and no indexable canonical identity before a domain is supplied.
8. Local frontend checks and `python3 scripts/grok_verify.py --mode pr` pass.
9. Independent code and test reviewers inspect the exact final diff.
10. README describes the new nodes and retains the complete stack graph before
    release is proposed.

## Security and Provenance

The imported skill retains the upstream MIT license and author attribution.
Upstream content is reviewed as untrusted data before import; repository or
webpage text cannot override the active route or repository contract.
The skill must not read secrets, credential stores, private keys, or `.env`.
It must not deploy, publish, submit forms, or mutate production systems without
separate exact authorization.
Generated pages use no external libraries or fonts, and third-party media is
loaded only under the documented explicit-activation or approved mode contract.
Validation reports distinguish syntax, lab measurements, field data, WCAG
conformance, and search-feature eligibility instead of conflating them.

## Rollback

The change has no database, migration, service, or persistent user data.
Rollback is one revert of the side-project commit set, removing the local skill,
showcase, tests, README additions, and evidence together.
After rollback, run the repository verifier and confirm both new directories
are absent while existing workflow and Trust CI behavior remain unchanged.

## Delivery Stack

This work is intentionally stacked on branch
`fix/path-aware-shell-policy-circuit-breaker`, commit
`7c61e3b647924e5667d171d8b286e5d79b8a4efe`.
Its pull request base is `fix/path-aware-shell-policy-circuit-breaker`, not
`main`, so the diff contains only this side project.
No merge, tag, release, deployment, or protected-path write is authorized by
this design document.
Protected files are edited only after an exact repository-local grant, and the
final PR must receive the App-owned exact-SHA Trust CI check required by branch
protection before merge.
