# Finish 2.0.6: commit ban, verify, GitHub Release

GHA already removed on disk. User «go ahead»: commit that tree as 2.0.6, verify locally, publish Latest.

## In scope

- Commit ban + rebuilt zip (stay VERSION 2.0.6)
- `grok_verify --mode pr`
- Tag/push/`gh release` (already authorized; not GitHub Actions)

## Out of scope

- Restore GHA
- New CI vendor
- Touch v2.0.5
