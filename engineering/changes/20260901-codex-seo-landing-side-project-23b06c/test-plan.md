# Test plan — Codex SEO landing side project

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Skill validates and exposes safe three-mode contracts | `tests/test_seo_landing_side_project.py`, `quick_validate.py` |
| P0 | Audit-only cannot write and approval stop precedes validation | focused contract tests and code review |
| P0 | Provenance and exact upstream commit are retained | focused contract tests |
| P1 | Showcase is noindex, dependency-free, semantic, and accessible | focused tests and viewport inspection |
| P1 | Existing repository behavior remains green | `python3 scripts/grok_verify.py --mode pr` |

## Automated checks

- Unit: `python3 -m unittest tests.test_seo_landing_side_project -v`.
- Integration: local HTTP 200 plus the versioned `side-projects/seo-landing-showcase/browser-contract.mjs` runner.
- Contract: frontmatter, UI metadata, modes, approval, provenance, noindex, and resource assertions.
- E2E: none; there is no backend or submission flow.
- Static analysis: Codex `quick_validate.py`, `git diff --check`, and repository PR verifier.

## Manual checks

- Inspect 320, 768, 1280, and 1920 px viewports for overflow and reflow.
- Verify keyboard order, visible focus, logical headings, and reduced-motion behavior.
- Confirm no network request leaves the local showcase origin on first load.

## Executed evidence — 2026-09-01

- Focused contracts: 9 tests passed, including structural mode, exact inventory, external-resource, and browser-runner contracts.
- Full unittest discovery: 208 tests passed in the latest full-suite run.
- W3C Nu: 0 errors and 0 messages after repairing two generic-div ARIA errors.
- Browser: no horizontal overflow at 320/768/1280/1920; first Tab exposes the skip link with a 3 px outline; reduced-motion computes `scroll-behavior: auto`.
- Versioned browser runner reports `passed: true`.
- Lighthouse 13.4.1 medians after accessible-name repair: Performance 100, Accessibility 100, Best Practices 96, SEO 60, LCP 901.6 ms, CLS 0, TBT 0 ms.
- The only Best Practices failure is the local `/favicon.ico` 404; the only weighted SEO failure is intentional `noindex` crawl blocking.
- Lighthouse Accessibility is automated evidence, not WCAG certification. SEO 60 is expected while the approved `noindex` boundary is active.
- Exact reports and screenshots: `evidence/showcase/`.
