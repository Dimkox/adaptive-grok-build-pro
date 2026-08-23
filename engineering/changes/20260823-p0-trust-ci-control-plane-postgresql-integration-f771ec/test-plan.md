# Test plan — Trust CI activation

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Local root + Trust CI unit tests and compileall on current SHA | handoff baseline commands |
| P0 | `grok_verify --mode pr --no-record --json` | verify JSON |
| P0 | Live PostgreSQL: concurrent claim, lease reclaim, heartbeat ownership, attempts→dead, nonce replay, attestation durability | `tests.test_postgres_integration` with `TRUST_CI_TEST_DATABASE_URL` |
| P0 | PostgreSQL restart/recovery | `trust-ci/scripts/postgres-restart-drill.sh` |
| P0 | No `.github/workflows/` | structure test |
| P1 | Source mutation still fails after command exit 0 | runner unit test |
| P1 | Holdout example digest matches example bundle | ops unit test |
| P1 | Local two-file compose build-without-push of api/worker/runner-image; inspect `.Id` and JSON RepoDigests; no digest written to tracked examples | `evidence/implementation-images.md` plus `git diff --exit-code` on example policy/env |
| P1 | Branch-protection payload includes `app_id` | github unit test |
| P2 | App-owned check on PR #2 exact SHA | GitHub Checks API |
| P2 | Offline attestation verify with CI public key | `adaptive-trust-ci attestation-verify` |

## Automated checks

- Unit: `PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest discover -s tests -v`
- Unit: `PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest discover -s trust-ci/tests -v`
- Integration: `trust-ci/scripts/postgres-integration.sh` and restart drill
- Static: `python3 -m compileall` and `python3 scripts/grok_verify.py --mode pr`

## Manual checks

- GitHub App permissions and installation
- Webhook HMAC acceptance
- App-owned policy-epoch Check Run on exact SHA
- Direct push / merge without that check fail after protection
