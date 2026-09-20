# Test plan — Winston Wolfe Pulp Fiction landing v2

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Missing tree / missing referenced asset | `tests/test_winston_wolfe_seo_landing_v2.py` |
| P0 | Invented origin, form, external runtime URL, SVG, iframe | same |
| P0 | Skill/showcase mutation | existing `tests/test_seo_landing_side_project.py` must stay green |
| P1 | Viewport overflow 320/768/1280/1920 | reuse `browser-contract.mjs` against the new directory; skip if Node/Chrome missing |
| P2 | Keyboard, contrast, reduced motion, JS-disabled | recorded in evidence; not WCAG certification |

## Automated checks

- Unit: `tests/test_winston_wolfe_seo_landing_v2.py`
- Integration: none
- Contract: empty OpenAPI/events remain empty; `contracts` profile checks existing repo contracts only
- E2E: optional local Chrome contract
- Static analysis: selected `grok_verify.py --mode pr` profiles (`base`, `contracts`)

## Manual checks

- HTML stop-point: show the page to the user before reporting Lighthouse/LCP.
- Inspect rasters for actor likeness.
- Do not claim Lighthouse 100 or WCAG AA in landing copy.
