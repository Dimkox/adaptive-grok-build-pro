# Release plan — Winston Wolfe Pulp Fiction landing v2

## Deployment

This change does not deploy a host. Delivery is an isolated branch and pull request of static files. Local preview:

```bash
python3 -m http.server 4174 --directory side-projects/seo-landings/winston-wolfe-pulp-fiction-v2
```

No VERSION bump, no package rebuild, no tag, no GitHub Release.

## Feature flags / staged rollout

None. The page is `noindex, nofollow` until a later change supplies a real HTTPS origin.

## Metrics and alerts

None. Do not claim Lighthouse/LCP numbers before the HTML stop-point and a pinned run.

## Go/no-go criteria

- Focused landing tests pass.
- Skill/showcase tests still pass.
- `python3 scripts/grok_verify.py --mode pr` passes.
- Independent `code_reviewer` and `test_reviewer` pass on the final tree.
- Merge still requires the App-owned Trust CI check on the exact PR head. This package is not merge authority.
