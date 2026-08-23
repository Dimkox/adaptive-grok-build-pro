# Trust CI P0 local verification

Verified on 2026-08-23 against the self-hosted Trust CI implementation reconstructed from `feat/trust-ci-control-plane`.

## Commands

```bash
PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest discover -s tests -v
PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest discover -s trust-ci/tests -v
python3 -m compileall -q .grok-stack/adaptive_grok scripts trust-ci/src tests trust-ci/tests
```

## Results

- root delegated-approval and policy suite: 32 passed;
- Trust CI suite: 97 passed;
- PostgreSQL integration tests: 4 skipped because `TRUST_CI_TEST_DATABASE_URL` was not available in the verification environment;
- compileall: passed;
- GitHub Actions remain forbidden and absent from the self-hosted branch.

## Scope

This is local preflight evidence only. It is not the authoritative merge verdict. The authoritative verdict must be produced by the deployed GitHub App through an app-bound policy-epoch check on the exact pull-request head SHA.

## Remaining external activation

1. create and install the GitHub App;
2. provide App ID, installation ID and worker-only private key;
3. run the PostgreSQL integration suite against a disposable live database;
4. deploy PostgreSQL, API, worker, immutable runner image and holdout bundle;
5. register the HMAC-protected pull-request webhook;
6. prove the App-owned check on a disposable PR;
7. bind branch protection to the exact policy-epoch check and App ID.
