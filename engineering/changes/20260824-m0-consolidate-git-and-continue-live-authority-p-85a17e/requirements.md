# Requirements — M0 consolidate git and continue live authority proof

## Acceptance criteria

- [ ] Given dirty M0 docs vs HEAD `1fc9420`, when the implementer stages an **explicit path list** (never `git add -A`) and commits on `milestone/m0-live-trust-authority`, then HEAD contains overlay + Check Run `97390635614` / App `4694114` / `action_required`, plan M0.1 worker-running, M0.2 Check Run marked partial/local HMAC/not complete, activation report PR 5 / SHA `1fc9420` / Check Run id / job id, and packages `…-3e6166/` + `…-85a17e/`.
- [ ] Given leftover paperwork, then these stay unstaged: `…-9d97f8/state.json`, `…-37bf04/`, `…-33e0c2/`.
- [ ] Given kill-switch on, then new webhook/approvals/claims are blocked (`503` or metric `adaptive_trust_ci_kill_switch 1`). Given kill-switch off, then `GET http://127.0.0.1:18080/health/ready` is 200 and the switch is off. STOP file is not left in place. No `compose down -v`.
- [ ] Given `GET /attestations/1b63d10b-90c1-498a-97b8-7b5e0ea76aec` from inside the API container (print status only), then 404 is recorded as `N/A (job needs_approval; GET 404)`. No fake envelope.
- [ ] Given the commit, then `python3 -m unittest trust-ci.tests.test_m0_invariants` and `python3 scripts/grok_verify.py --mode pr` pass. Characterization: report Check Run id is not `UNKNOWN`; plan still says local HMAC is not a registered webhook; spec/plan/report contain no PEM material.
- [ ] Given inspect of git / chat / report, then no PEM, JWT, webhook secret, installation token, or human approval private key appears.
- [ ] `origin/milestone/m0-live-trust-authority` and `main` are unchanged. PR #5 stays draft.

## Failure and edge cases

- Kill switch cannot be turned off → stop; restore off is P0; do not commit a red API.
- `/health/ready` not 200 after off → stop; do not `compose down -v`.
- Attestation GET 200 → verify offline with CI **public** key only; still do not push; do not print the envelope secrets if any.
- Hook denies `trust-ci` argv → structured Edit/Write + grant; no `sed`.

## Non-functional requirements

- Security: four planes; overlay untracked; no secrets in git/chat
- Reliability: leave live listener up; kill-switch restored off
- Observability: operator-safe ids only in the activation report
