# Release plan — Add repository-scoped immutable policy profiles to the Python trust-ci webhook API and worker, selecting commands and holdout by exact repository, binding jobs to the selected profile digest, rejecting unknown repositories, and preserving schema-version-1 behavior with automated tests

## Deployment

This PR does not deploy. After merge, first roll out compatible binaries while the legacy policy remains active. Then prepare and independently review the server-side catalog/holdouts, switch API and workers atomically during a drain window, and onboard repositories one at a time.

Repository-profile support is currently a code/config capability pending a separately approved server-mounted catalog and external holdout installation. The checked-in example is illustrative only and does not enable either repository in deployed Trust CI.

## Feature flags / staged rollout

The policy shape is the control: legacy mode remains unchanged until a reviewed catalog is installed. Prove each repository's new App-owned check before binding branch protection to its epoch; keep the previous policy/images available for coherent rollback.

## Metrics and alerts

- readiness: catalog generation/count and active legacy/profile mode;
- terminal failures: unknown/stale binding, holdout integrity, status publication;
- queue/lease/retry/dead-job metrics remain existing low-cardinality series;
- no repository, SHA, job ID, commands, or internal paths in unauthenticated metrics.

## Go/no-go criteria

- Full local verification and independent code/test reviews pass on exact HEAD.
- Legacy fixture digest/check name is unchanged.
- Two-profile failure/isolation/replay tests pass.
- Server policy, holdouts, App settings, branch protection, and deployment remain outside this PR.
- Rollout requires a separate exact delegated operation and external Trust CI approval.
