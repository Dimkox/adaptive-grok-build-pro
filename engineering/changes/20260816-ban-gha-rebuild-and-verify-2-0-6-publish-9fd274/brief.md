# Ban GHA, rebuild and verify 2.0.6, publish

User rule: never GitHub Actions. Rebuild the 2.0.6 package under that rule, verify locally, finish the unpublished GitHub Release.

## Outcome

This repo and the installer do not ship GitHub Actions. `grok_verify --mode pr` is the gate. Working 2.0.6 zip is rebuilt and GitHub Latest becomes v2.0.6.

## In scope

- Remove workflows, dependabot, `--with-ci` copy
- Tests + decisions
- Rebuild `packages/adaptive-grok-build-pro-v2.0.6.zip*`
- Local verify
- Last mile: tag/push/release (already authorized)

## Out of scope

- Another CI vendor
- `pyproject.toml`
- Touch v2.0.5
