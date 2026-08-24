# Test plan — M0 consolidate git and continue live authority proof

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | M0 invariants: spec/plan/report exist, no PEM, no Actions tree, compose loopback, claw named | `python3 -m unittest trust-ci.tests.test_m0_invariants` |
| P0 | Activation report Check Run id is not `UNKNOWN`; plan still says local HMAC is not a registered webhook | new characterization assertions |
| P0 | Kill-switch on blocks, off restores ready | live drill; report field |
| P1 | Attestation GET 404 for needs_approval job | live probe; report field |
| P1 | Leftover packages not staged | `git status` after commit |

## Automated checks

- Unit: `trust-ci.tests.test_m0_invariants`
- Integration: none (no store/schema change)
- Contract: none
- E2E: none
- Static analysis: `python3 scripts/grok_verify.py --mode pr`

## Manual checks

- `curl -fsS http://127.0.0.1:18080/health/ready` 200 after drill
- `git status` shows leftover `9d97f8`/`37bf04`/`33e0c2` still unstaged
- `git rev-parse origin/milestone/m0-live-trust-authority` still `1fc9420` (no push)
