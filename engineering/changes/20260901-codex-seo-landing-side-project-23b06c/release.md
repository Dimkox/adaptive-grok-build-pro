# Release plan — Codex SEO landing side project

## Deployment

Push `feature/seo-landing-codex-side-project` only with exact delegation and
open a pull request based on `fix/path-aware-shell-policy-circuit-breaker`.
This change does not deploy a public site because no canonical origin exists.

## Feature flags / staged rollout

Repository-local installation is the isolation boundary. The skill activates
only through explicit `$seo-landing` or matching intent; the showcase remains
`noindex, nofollow` until a separate origin-enablement change.

## Metrics and alerts

- Codex skill validator exit code is zero (`Skill is valid!`).
- Focused contract test failures are zero: 9 passed.
- Full unittest failures are zero: 208 passed.
- W3C Nu errors are zero on final HTML.
- Lighthouse 13.4.1 medians are Performance 100, Accessibility 100, Best Practices 96, SEO 60, LCP 901.6 ms, CLS 0, and TBT 0 ms.
- Best Practices loses only the local `/favicon.ico` 404; SEO loses only intentional `noindex` crawl blocking.
- Versioned browser runner reports `passed: true`; overflow is false at all four widths and reduced-motion scrolling is auto.
- Repository PR verifier passes for the exact final fingerprint.
- Independent code and test reviews pass for the exact diff.
- App-owned policy-epoch check succeeds on the exact PR head SHA.

## Go/no-go criteria

Go only with a clean stacked diff, complete README graph, retained provenance,
passing focused and repository checks, fresh reviews/receipts, and the required
external Trust CI check. No-go on stale evidence, missing origin boundary,
unresolved review finding, or a diff containing Trust CI/GitHub Actions changes.
SEO 60 is not a release regression for this local artifact: removing `noindex`
before a real origin is supplied is explicitly a no-go condition.
Route verification base remains `1c06299894279a88b881defa3f19b004fa742223`;
the stacked delivery base remains `fix/path-aware-shell-policy-circuit-breaker`
at `7c61e3b647924e5667d171d8b286e5d79b8a4efe`.
