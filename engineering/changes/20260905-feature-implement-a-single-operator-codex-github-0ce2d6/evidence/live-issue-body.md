The landing still identifies Adaptive Grok Build Pro as `v2.0.12`. Update only this stale version/status presentation on exact base `699010380f4f90a0193a9c22090c35e6aded7d2c`:

- Show `v2.0.14` in both root-page version locations and in each of the five localized landing pages; set root JSON-LD `SoftwareSourceCode.version` to `2.0.14`.
- Make the exact visible root-page product label `Governed Agentic Software Factory — Offline Technical Preview` and rename the root version signal from `Public package version` to exactly `Latest published release`.
- Update `tests/test_landing.py` to expect `2.0.14` and positively assert the exact visible version/labels without deleting or weakening existing checks.
- Recompute the `.htaccess` `script-src` SHA-256 source from the final exact inline JSON-LD bytes. Change only that hash token; preserve every CSP directive and do not add `unsafe-inline` or `unsafe-eval`.

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

Within the HTML, change only the version tokens, the two exact root labels above, and the minimum markup needed to expose the product label. Do not alter CSS, assets, generated/deployment artifacts, historical documents, unrelated copy, links, claims, or security policy. Do not claim enterprise readiness, production autonomy, M8/M9 activation, a live provider/publisher, hosting, indexing, deployment, or successful production release. Do not deploy or publish anything.

Run exactly:

```text
python -m unittest discover -s tests -v
```

Report the changed files and test result only.
