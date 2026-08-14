# Release plan — v2.0.0

## Deployment

1. Commit assembly on `main`
2. Build `dist/adaptive-grok-build-pro-v2.0.0.zip` (gitignored)
3. Tag `v2.0.0`
4. Push `main` and the tag
5. Create public GitHub Release with zip + `.sha256`

No servers, databases, or feature flags.

## Go/no-go

| Check | Required |
| --- | --- |
| Unit suite green | yes |
| Doctor no FAIL | yes |
| Secret scan clean | yes |
| `.env` untracked | yes |
| User production approval unexpired | yes |

## Metrics and alerts

None. This is an MIT installable workflow pack, not a hosted service.
