# Code review — M0.1 product docs (route `6346a398114f`)

**Status:** pass  
**Scope:** product diff only — `engineering/runbooks/trust-ci-activation-report.md`, `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` checkboxes, `decisions.md`.  
**Ignored:** `engineering/changes/*/state.json`, untracked change packages, credentials, `.env`.

## Verdict

The three product files record a bounded M0.1 listener (`postgres` + `migrate` + `api` on claw loopback `127.0.0.1:18080`). They do not claim worker start, do not steal host `8080`, and do not paste secrets.

## Pass gates

| Gate | Result |
| --- | --- |
| No secrets | **Pass.** Activation report still forbids PEM/JWT/webhook/admin token/approval private keys. Values are hostname, loopback URL, SHAs, image `name@sha256` pins, policy/holdout hex digests, `App ID`/`Installation ID` remain `UNKNOWN`. `decisions.md` states bootstrap public key only and unlinked private file; no key material in the diff. |
| Worker not claimed started | **Pass.** Plan checkbox for `compose up … worker` is still **unchecked** with explicit **deferred**. Ready check documents worker env on disk with App IDs `UNKNOWN` and **not started**. Decision: “Worker stays off until GitHub App ID and installation ID exist”. Report: “Worker and DinD were not started”. |
| Host 8080 not stolen | **Pass.** Public bind is `127.0.0.1:18080` mapping to **container** 8080. No claim of host port 8080. TLS proxy explicitly out of this slice. |

## Contract fit

- Brief: health on `18080`, webhook absent, `main` unprotected — matches report (`main` protected `false`, webhook absent) and checked plan items.
- Out of scope honored: no webhook, branch-protect, merge PR #5, GHA, host 8080, PEM in chat.
- Remaining honest `UNKNOWN` fields (App/installation IDs, disposable PR, Check Run, attestation, leftover Actions, kill switch) are appropriate; M0.2/M0.3 not claimed done.

## Residual (non-blocking)

- Worker compose line stays an open checkbox on purpose; do not tick it until App IDs exist without reading PEM.
- `TRUST_CI_PUBLIC_BASE_URL` as loopback HTTP is operator-safe for M0.1, not a public TLS URL.

## Files reviewed

- `decisions.md` (+4 lines)
- `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` (M0.1 checkboxes)
- `engineering/runbooks/trust-ci-activation-report.md`
