# Codex SEO landing side project

Change ID: `20260901-codex-seo-landing-side-project-23b06c`
Created: 2026-09-01T15:20:32+00:00
Risk: low
Complexity: standard
Domains: frontend

## Problem

Create an isolated side project inside this repository: adapt upstream aleksandr-alhoff/seo-landing into a Codex-native reusable skill for on-demand SEO landing generation, audit, and optimization; add a Russian static showcase page; preserve upstream license and provenance; add behavior tests plus frontend accessibility and performance checks; leave Trust CI behavior unchanged.

## Outcome

Codex can invoke a repository-local `$seo-landing` skill on demand to generate,
audit, or optimize static SEO landings, while a Russian static showcase explains
the capability without coupling it to Trust CI runtime behavior.

## Scope

### In scope

- Adapt upstream commit `1aa908f96a09e2e93fd1839ac51b02d362e7a8ef` into `.agents/skills/seo-landing/`.
- Add Codex `agents/openai.yaml`, safe three-mode routing, and retained MIT provenance.
- Add a dependency-free Russian showcase under `side-projects/seo-landing-showcase/`.
- Add deterministic skill, provenance, security, accessibility, and frontend contract tests.
- Update README and the decision log, then deliver as a stacked pull request.

### Out of scope

- A customer-specific generated landing, production hostname, hosting, analytics, or lead backend.
- Changes to Trust CI, workflow dispatch, branch protection, dependencies, or GitHub Actions.
- Merge, tag, release publication, or production deployment.

## Constraints

- Backward compatibility: existing runtime and Trust CI behavior remain unchanged.
- Data/privacy: no secrets, credentials, personal data, analytics, or production writes.
- Performance: showcase has no external runtime resources and optional JavaScript stays local and under 15 KB.
- Operational: showcase remains `noindex, nofollow` until a real canonical origin is supplied; PR base is `fix/path-aware-shell-policy-circuit-breaker`.
