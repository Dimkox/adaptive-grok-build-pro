# task_analyst — M0.1 listener only (6346a398114f)
**Verdict:** this turn is **M0.1 dedicated-host listener on `claw` only.** Roadmap auto + user compose-up consent is `migration_or_external_write_approval` for host compose. PR #5 stays M0.0 draft. Write owner: `general_implementer`. This agent does not implement, push, merge, or open secrets.
## Outcome
On hostname `claw`, compose project `adaptive-trust-ci` is up; `GET http://127.0.0.1:18080/health/ready` returns **200**. GitHub webhook list stays empty. `main` stays unprotected. No App-owned Check Run this turn.
## In scope
- Host-owned copies of example env/policy/trust-store on `claw`; pin `name@sha256:` images + holdout digest; named volume `trust-ci-postgres`.
- `docker compose up -d postgres migrate api worker` (worker pulls `docker-engine` + `runner-loader`). Loopback health. Role split: API = webhook secret + trust-store **public** keys, **no** App RSA; worker = App ID/install ID/PEM + CI signing key, **no** webhook secret.
- Mint an exact delegated grant naming compose-up on `claw` only. Do not read `.env`, PEM, JWT, or human private keys.
## Out / forbidden
M0.2 webhook `/webhooks/github`; M0.3 `branch-protect` / disable workflow `340420982`; merge or ready PR #5; M2–M9; GitHub Actions / `.github/workflows/**`; forge `adaptive-trust-ci/verified@*`; publish host **8080** (SearXNG); steal existing containers/volumes/networks; `git add -A`; VERSION/tag/release; TLS webhook URL is not this exit.
## Acceptance
- `/health/ready` **200** on `127.0.0.1:18080` (503 until Postgres ping + ≥1 active trust-store public key). In-container healthcheck stays `:8080`. If no human **public** key exists, STOP — do not generate a human private key here.
- `docker compose ps`: project `adaptive-trust-ci`; published `127.0.0.1:18080->8080`; host `:8080` still SearXNG.
- `GET .../hooks` empty; `GET .../branches/main/protection` 404; leftover Actions `340420982` untouched.
- Product tree unchanged → skip `grok_verify`/reviews (`AGENTS.md` no-op). If product files change, `python3 scripts/grok_verify.py --mode pr` then route reviews.
