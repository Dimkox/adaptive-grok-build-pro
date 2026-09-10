# Delivery preparation

This change adds a local, explicit-file evidence accounting command and consumer installer enrollment. Two existing landing test fixtures also receive the same frozen clock as their services after mandatory preflight exposed expired fixture input. There is no service deployment, runtime activation, policy update, migration, version bump or GitHub Release in this scope.

## Candidate

Branch: `feat/historical-autonomy-evidence`, based on `be752872f3e5a9d6fe179872d9c8bdaec4338238`.

The public candidate contains generic implementation, synthetic data, operator instructions and sanitized workflow evidence. Private consumer snapshots and the detailed factual report remain outside this checkout.

## Validation and operation

From the controller checkout, run `python3 scripts/grok_history.py examples/historical-evidence/synthetic.json`. Installed consumers invoke the same CLI with their own explicit snapshot path. Invalid input returns an error before producing a report. Report completeness, unknown measurement counts and qualification gaps are operator signals; imported data never creates authority.

Local readiness requires `python3 scripts/grok_verify.py --mode pr` and independent code, test and security review receipts for the current fingerprint. The App-owned exact-SHA Trust CI check remains the merge gate. No local report or receipt replaces it.

## External actions

Branch push, PR publication, merge and release are not performed by this change package. An external operation may proceed only with the exact delegation required by AGENTS.md. There is no release proposal here; release-time README/version requirements remain in force for a future release.

## Recovery

Remove or forward-fix the optional command and installer enrollment through the normal PR path. Existing factory contracts and stored operational state are unchanged, so there is no data rollback.
