# Test plan — M0

## After design approval (M0.0, no GitHub writes)

- Characterization: no `.github/workflows/**`; API source has no `GitHubClient`/`GitHubAppAuth`; worker has `GitHubAppAuth`; compose publishes `127.0.0.1` not `0.0.0.0`; holdout forbids workflows.
- Existing `PYTHONPATH=trust-ci/src python3 -m unittest discover -s trust-ci/tests`
- `python3 scripts/grok_verify.py --mode pr`
- `docker compose -f trust-ci/compose.yaml config` (no `up`)
- Fixture-key crypto only; never `trust-ci/runtime/github-app-private-key.pem`

Do **not** assert that `main` is unprotected (would fight later live goal).

## Needs migration/external-write approval

- Dedicated-host `compose.yaml up`, webhook registration, disposable PR, live Check Run, `branch-protect`, disable workflow 340420982, PEM/JWT install-ID lookup.
- Postgres harness `compose.test.yaml` is local (no GitHub) but deferred until design approval; it does not qualify this laptop as the CI host.
