# Release plan — qwen-omni-intl profile and probe classification

Source-only change. Nothing is installed, enabled or restarted: the installed units keep their releases and their current `selected_profile`, and live execution stays default-off in source. Selecting `qwen-omni-intl` on a host is a separate operational action requiring its own exact delegated grant, a config change and a restart — out of scope here and not performed.

## Deployment

Merge to `main`; no service change. The next release chain carries the profile in its artifact.

## Feature flags / staged rollout

Capability selection remains an explicit host-config choice (`selected_profile` + `live_enabled`); there is no automatic enablement path.

## Metrics and alerts

- Probe output state/category/http_status for a deliberate bad key.
- Durable observation category for a live rejection.

## Go/no-go

Go when the three landing suites and the repository verifier are green and reviews pass. No-go if the profile was added by relaxing the credential or output contract, or if any installation was touched.
