# Test plan — Add repository-scoped immutable policy profiles to the Python trust-ci webhook API and worker, selecting commands and holdout by exact repository, binding jobs to the selected profile digest, rejecting unknown repositories, and preserving schema-version-1 behavior with automated tests

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Legacy schema-v1 digest/check compatibility | Exact regression fixture and unit assertion |
| P0 | Two repositories select isolated commands/holdouts/digests | Policy + API + runner tests |
| P0 | Unknown, case variant, stale, removed, or mismatched profile fails before checkout | Negative API/worker/runner tests |
| P0 | Approval, check, attestation, retry, and replay preserve bound digest | Runner/API contract tests |
| P1 | A-only change leaves B digest stable; common change rotates both | Canonical digest tests |
| P1 | Duplicate webhook remains idempotent; changed digest creates new identity | API/store tests |
| P1 | Holdout root traversal and digest mismatch fail closed | Policy/runner tests |

## Automated checks

- Unit: `policy.py` catalog parsing, normalization, resolution, digest stability and failure modes.
- Integration: API enqueue with two profiles; worker dispatch to selected runner; retry/replay behavior.
- Contract: unchanged webhook/job/approval/attestation v1 fields and existing HTTP 403 contract.
- E2E: existing isolated Trust CI compose suite when available; no live GitHub or deployed-policy mutation in this change.
- Static analysis: route-selected `python3 scripts/grok_verify.py --mode pr` (`base`, `contracts`).

## Manual checks

- Inspect example catalog and README for exact repository names, immutable image/digest requirements, staged rollout, and rollback.
- Confirm no SQL migration, `.github/workflows`, secrets, deployed policy, or holdout artifact entered the diff.
