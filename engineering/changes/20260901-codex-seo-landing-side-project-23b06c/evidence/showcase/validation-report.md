# Showcase validation report

Validated: 2026-09-01
URL: `http://127.0.0.1:8765/`
Chrome: `/usr/bin/google-chrome`
Lighthouse: `13.4.1`

## Served identity

The existing local listener returned HTTP 200 with the expected title, H1, and
`noindex, nofollow`. It served the current files from
`side-projects/seo-landing-showcase/`.

## Lighthouse lab measurements

Each run used:

```bash
npx --yes lighthouse@13.4.1 http://127.0.0.1:8765/ \
  --only-categories=performance,accessibility,best-practices,seo \
  --output=json --output-path=<run-report> \
  --chrome-path=/usr/bin/google-chrome \
  --chrome-flags="--headless=new --no-sandbox --disable-dev-shm-usage" \
  --quiet
```

| Run | Performance | Accessibility | Best Practices | SEO | LCP | CLS | TBT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 100 | 100 | 96 | 60 | 901.8 ms | 0 | 0 ms |
| 2 | 100 | 100 | 96 | 60 | 901.5 ms | 0 | 0 ms |
| 3 | 100 | 100 | 96 | 60 | 901.6 ms | 0 | 0 ms |
| Median | **100** | **100** | **96** | **60** | **901.6 ms** | **0** | **0 ms** |

Artifacts: `lighthouse-run-1.json`, `lighthouse-run-2.json`, and
`lighthouse-run-3.json`.

Best Practices loses four points solely on `errors-in-console`: Chrome requests
an undeclared `/favicon.ico` and the asset-free showcase returns 404. SEO loses
its weighted `is-crawlable` audit because Lighthouse correctly detects `noindex`; this is the
approved pre-production boundary until a real canonical origin exists. Neither
finding is hidden or reclassified as a passing audit.

These are Lighthouse lab results for this local server, not field Core Web
Vitals. The automated accessibility score is not WCAG certification and does
not replace assistive-technology or expert conformance testing.

## W3C Nu

Command:

```bash
curl --silent --show-error --fail-with-body \
  -H 'Content-Type: text/html; charset=utf-8' \
  --data-binary @side-projects/seo-landing-showcase/index.html \
  'https://validator.w3.org/nu/?out=json' \
  -o engineering/changes/20260901-codex-seo-landing-side-project-23b06c/evidence/showcase/w3c-nu.json
```

Initial validation found two invalid `aria-label` attributes on generic divs.
After adding `role="group"`, the final artifact reports `0` errors and `0`
messages. `w3c-nu-before-fix.json` retains the original evidence.

## Browser contract

A headless Chrome DevTools Protocol run emulated 320, 768, 1280, and 1920 px
viewports under `prefers-reduced-motion: reduce` and retained one PNG per width.
The dependency-free runner is versioned at
`side-projects/seo-landing-showcase/browser-contract.mjs` and was run with the
exact command documented in the showcase README.

| Width | Document width | Horizontal overflow | Reduced motion | Scroll behavior |
| ---: | ---: | --- | --- | --- |
| 320 | 320 | false | true | auto |
| 768 | 753 | false | true | auto |
| 1280 | 1265 | false | true | auto |
| 1920 | 1905 | false | true | auto |

The first Tab focuses `.skip-link`, its target is `#content`, it is visible,
and computed focus styling is `solid 3px`. The first browser run exposed a CSS
specificity defect that left smooth scrolling active under reduced motion;
`browser-contract-before-reduced-motion-fix.json` retains that evidence. The
final `browser-contract.json` reports `passed: true` and its viewport PNGs prove
the repaired state. The redundant brand `aria-label` was removed so its
accessible name comes from visible `SEO Landing` text. Pre-repair Lighthouse
reports remain under `lighthouse-before-accessible-name-fix-run-*.json`.

## Syntax and local resources

Python's HTML parser completed without an exception. All eight local links and
anchors resolved, CSS braces were balanced, and JSON-LD count was zero. The
absence of JSON-LD is intentional because no production origin exists; no
origin-bound structured facts were invented.

## Automated tests

```bash
python3 -m unittest tests.test_seo_landing_side_project -v
```

Result: `Ran 9 tests — OK`.

```bash
python3 -m unittest discover -s tests -q
```

Result: `Ran 208 tests in 42.416s — OK`.

## Blockers and boundaries

- Public indexing remains blocked until the user supplies a canonical HTTPS origin.
- Production server headers and real-origin crawlability were not testable on the local Python server.
- No W3C, browser, focused-test, or full-unittest blocker remains for the local noindex showcase.
