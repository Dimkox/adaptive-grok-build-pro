# Release plan — Release v2.0.19 with fail-closed factory issue fixes

## Deployment

No production deployment is part of this source release. Delivery is a protected PR followed by
the App-owned exact-head Trust CI check; tag, archive, GitHub Release and deployment are separate
delegated operations after merge.

## Feature flags / staged rollout

## Metrics and alerts

## Go/no-go criteria

- Fix tree contains only accepted #35/#39/#48/#73/#167 changes plus their tests/evidence; #36 is
  explicitly dispositioned through #186 rather than fabricated.
- Focused issue tests and full `python3 scripts/grok_verify.py --mode pr` pass on the final tree.
- Independent code/test reviews and fingerprint-bound receipts are current.
- Release metadata and README describe the exact candidate tree and retain architecture links.
- PR has successful `adaptive-trust-ci/verified@<policy-sha12>` on the exact final head.
- No merge/tag/release/deploy occurs before the external gate and required human authority.
