# First live issue draft — do not create yet

- Target repository: `Dimkox/ai-dark-factory-landing`
- Exact base: `699010380f4f90a0193a9c22090c35e6aded7d2c`
- Base tree: `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`

## Title

Update the landing to v2.0.14 with the offline-preview label

## Body

The landing still identifies Adaptive Grok Build Pro as `v2.0.12`. Update only
this stale version/status presentation on exact base
`699010380f4f90a0193a9c22090c35e6aded7d2c`:

- Show `v2.0.14` in both root-page version locations and in each of the five
  localized landing pages; set root JSON-LD `SoftwareSourceCode.version` to
  `2.0.14`.
- Make the exact visible root-page product label
  `Governed Agentic Software Factory — Offline Technical Preview` and rename
  the root version signal from `Public package version` to exactly
  `Latest published release`.
- Update `tests/test_landing.py` to expect `2.0.14` and positively assert the
  exact visible version/labels without deleting or weakening existing checks.
- Recompute the `.htaccess` `script-src` SHA-256 source from the final exact
  inline JSON-LD bytes. Change only that hash token; preserve every CSP
  directive and do not add `unsafe-inline` or `unsafe-eval`.

The changed-path set must be exactly these eight mode-`100644` files:

```text
.htaccess
index.html
km/index.html
ko/index.html
lv/index.html
nl/index.html
tests/test_landing.py
zh-cn/index.html
```

Within the HTML, change only the version tokens, the two exact root labels
above, and the minimum markup needed to expose the product label. Do not alter
CSS, assets, generated/deployment artifacts, historical documents, unrelated
copy, links, claims, or security policy. Do not claim enterprise readiness,
production autonomy, M8/M9 activation, a live provider/publisher, hosting,
indexing, deployment, or successful production release. Do not deploy or
publish anything.

Run exactly:

```text
python -m unittest discover -s tests -v
```

Report the changed files and test result only.

## Expected semantic assertions

These are independent acceptance checks for the sealed candidate, not extra
issue scope:

1. Candidate parent is the exact base SHA above; its diff is non-empty, all
   eight paths above and no others changed, and every resulting mode is
   `100644`.
2. `index.html` has no `2.0.12`; its two visible version claims are `v2.0.14`,
   JSON-LD `SoftwareSourceCode.version` is `2.0.14`, visible text contains the
   exact product label, and the version signal pairs `v2.0.14` with exactly
   `Latest published release`.
3. Each of `km/index.html`, `ko/index.html`, `lv/index.html`, `nl/index.html`,
   and `zh-cn/index.html` changes only its single visible `v2.0.12` token to
   `v2.0.14`; no localized page retains `v2.0.12`.
4. The only `.htaccess` byte change is the existing `script-src` hash token.
   It equals the base64 SHA-256 of the final inline JSON-LD body; if JSON-LD is
   otherwise byte-identical, the expected source is
   `'sha256-AonynhQfwgonwmV3yEjVfIApl1NoEQsvaHziDMi+CY0='`. All directives,
   including `style-src 'self'`, remain unchanged and neither unsafe source is
   present.
5. `tests/test_landing.py` only repins the expected JSON-LD version and adds
   positive assertions for the exact visible version/product/signal labels;
   no existing assertion is removed or relaxed.
6. Forbidden readiness, autonomy, live integration, hosting/indexing, and
   deployment claims are absent; no artifact or deployment action occurs.
7. One exact configured unit-suite invocation exits `0`, and validation leaves
   the sealed commit/tree unchanged.
