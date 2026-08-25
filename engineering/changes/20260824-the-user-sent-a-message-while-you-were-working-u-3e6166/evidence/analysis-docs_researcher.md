# docs_researcher — M0 live Trust Authority facts

Route `3e61666b8de2`. Change `engineering/changes/20260824-the-user-sent-a-message-while-you-were-working-u-3e6166`. Read-only. No invented APIs.

Sources: M0 spec/plan, activation report, rollout, `trust-ci/README.md`, `AGENTS.md`, `decisions.md`, `mistakes.md`, `DARK_FACTORY_ROADMAP.md` M0, `QUICKSTART.md` Trust CI. Compose cited only to confirm DinD vs host socket as recorded in operator docs.

## 1. Host Docker socket vs nested DinD

**No listed operator/spec document authorizes mounting the host Docker socket instead of nested DinD.**

Privileged nested DinD is the recorded execution model and residual risk:

- Spec `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md:62`: “privileged DinD remains residual risk the user accepted”.
- Plan `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md:22-25`: compose-up of `docker-engine` + `runner-loader` + `worker`; “DinD unhealthy so worker did not reach running”.
- Activation report `engineering/runbooks/trust-ci-activation-report.md:5`: “`docker-engine` is restarting unhealthy (`rootlesskit: fork/exec /proc/self/exe: operation not permitted`)”.
- `decisions.md:7`: “Compose-up of `docker-engine`/`runner-loader`/`worker` was issued; DinD stayed unhealthy”.
- `QUICKSTART.md:57`: “Do not colocate privileged rootless DinD with production workloads.”
- `QUICKSTART.md:139`: jobs that need a runner require `docker-engine` and `runner-loader` (or systemd), not host-socket substitution.
- `trust-ci/README.md:35`: worker has “Docker-socket access” as a privileged component; runner never receives the socket (`trust-ci/README.md:45`, rollout `engineering/runbooks/trust-ci-rollout.md:58,144`).
- `trust-ci/compose.yaml:64-73`: service `docker-engine` is `privileged: true` with `TRUST_CI_DIND_IMAGE` and unix `unix:///run/user/1000/docker.sock` **inside** that container, not a host `/var/run/docker.sock` bind.

Runner: no Docker socket (`spec:48`, `trust-ci/README.md:45`).

## 2. `TRUST_CI_PUBLIC_BASE_URL` (HTTPS) vs local HMAC POST for first Check Run

Spec requires **HTTPS** for the public URL and GitHub webhook:

- `spec:62`: “`TRUST_CI_PUBLIC_BASE_URL` must still be HTTPS.”
- `spec:64`: “TLS reverse proxy to `/webhooks/github` and `/approvals`”.
- `spec:69-71` rollout order: deploy, then register `POST https://<ci>/webhooks/github` (API-only HMAC, `pull_request`; drafts enqueue).
- `trust-ci/README.md:58,155-166`: HTTPS reverse proxy; payload URL `https://ci.example.com/webhooks/github`.
- Rollout `engineering/runbooks/trust-ci-rollout.md:17,50`: HTTPS reverse proxy; “Configure an HTTPS GitHub pull-request webhook … API-only HMAC secret.”
- `QUICKSTART.md:57,141-146`: TLS in reverse proxy; register HMAC GitHub webhook; prove Check Run on a disposable docs PR.

M0.1 recorded **loopback HTTP**, not a public webhook:

- Activation report `engineering/runbooks/trust-ci-activation-report.md:11`: `TRUST_CI_PUBLIC_BASE_URL` = `http://127.0.0.1:18080`.
- `engineering/runbooks/trust-ci-activation-report.md:5`: “Webhook stays blocked (no public HTTPS).”
- Plan `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md:22`: “Webhook is M0.2 (blocked: no public HTTPS).”
- `decisions.md:7`: “GitHub webhook registration stays blocked until a public HTTPS URL exists.”

**No listed source describes a local HMAC POST (curl-to-loopback) as the first Check Run path.** First Check Run is M0.2: GitHub webhook → worker publishes App-owned Check Run (`plan:30-32`, `spec:71-72`, `QUICKSTART.md:141-146`).

`trust-ci/README.md:5-8` and `AGENTS.md:11` name the check `adaptive-trust-ci/verified@<policy-sha12>`; they do not define a simulated webhook substitute.

## 3. Policy digest / required check name (recorded)

Activation report (`engineering/runbooks/trust-ci-activation-report.md:16-17`):

| Field | Value |
| --- | --- |
| Policy digest (full hex) | `6737355947c21eb561073cb506ebc5698afd170088a34f8eaace50007c57d1a5` |
| Required check name | `adaptive-trust-ci/verified@6737355947c2` |

Shape matches `spec:54`, `trust-ci/README.md:7-9`, `AGENTS.md:11`, `DARK_FACTORY_ROADMAP.md:253`, `QUICKSTART.md:41,146`.

Live Check Run id / `external_id` remain `UNKNOWN` (`activation-report:20-21`). `main` protected = false (`activation-report:27`).

## 4. Operator-safe App IDs in activation report

`engineering/runbooks/trust-ci-activation-report.md:13-15`:

- GitHub App slug: `adaptive-trust-ci`
- App ID: `4694114`
- Installation ID: `156003193`

Repeated in `decisions.md:7` and `plan:22` (gitignored worker env; PEM unread).

## 5. Compose-up grants and webhook grants the runbook/plan names

`trust-ci-rollout.md` does **not** name `grok_approve.py` action tokens for compose-up or webhook. It lists operational steps (`rollout:45-50`) and says delegated grants may authorize branch/tag/release, never the App-owned Check Run (`rollout:102-104`).

Named grants live in the **plan** (`docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md:51-56`):

| Action | When |
| --- | --- |
| `git-push-branch` on `milestone/m0-live-trust-authority` | M0.0 draft PR |
| `external-write` `gh pr create` | M0.0 draft PR |
| Host compose / webhook / `branch-protect` / disable workflow 340420982 | M0.1–M0.3 only |

M0.1 also requires `migration_or_external_write_approval` (`plan:22`, `spec:62`). Spec forbidden: “`compose-up` / webhook / `branch-protect` in this host-name slice” (`spec:114`) — that STOP was M0.0; M0.1 later issued compose-up of DinD/worker (`plan:22-25`).

Webhook grant: same M0.1–M0.3 host-compose/webhook row; M0.2 still blocked without public HTTPS (`plan:22,32`).

## 6. Language forbidding local simulated GitHub webhook POSTs

**No explicit “do not POST a simulated GitHub webhook to loopback” sentence** in the listed sources.

What *is* written:

- Webhook is GitHub → `POST https://<ci>/webhooks/github` (`spec:71`, `plan:32`, `trust-ci/README.md:160-166`).
- Forging `adaptive-trust-ci/verified@*` is forbidden (`spec:104`, `decisions.md:24`).
- Local receipts/delegated grants are not merge authority (`spec:106`, `AGENTS.md:141`, `trust-ci/README.md:13`).
- Webhook registration blocked until public HTTPS (`decisions.md:7`, activation report line 5).

Absence of a simulated-POST prohibition is not authorization of that API.

## 7. Host is `claw`; laptop leftovers in listed product docs

M0 spec/plan/activation report: **zero** `laptop` matches (grep). Host language:

- `spec:42,60-62,111`: host is `claw`; agent workspace on claw untrusted; “Misnaming hostname `claw` (it is the named CI host, not a portable workstation)”.
- `plan:22`: named host **is `claw`**.
- Activation report line 10: Dedicated CI host = `claw`.
- `decisions.md:130-132`: “Never call it a laptop”.

`QUICKSTART.md:39`: “Consumer laptops do not stand up PostgreSQL” — consumer install path, not CI host naming.

`DARK_FACTORY_ROADMAP.md:117,533,633`: “laptop session” as factory/workspace independence — not M0 host naming.

Do **not** rewrite those consumer/DARK_FACTORY uses (prior host-name analysis already distinguished them).

## 8. Image pins and holdout digest as recorded

Activation report `engineering/runbooks/trust-ci-activation-report.md:23-26`:

- API: `ghcr.io/dimkox/adaptive-trust-ci-api@sha256:70a80960486b6008dac2dfe2ffc8e0b8e28f7ed8c03c52e673188fdb11207b23`
- Worker: `ghcr.io/dimkox/adaptive-trust-ci-worker@sha256:bffd013ce1510bda55c74fa7926647f0000c3fc84dbd55114f36ea74b5f62227`
- Runner: `ghcr.io/dimkox/adaptive-trust-ci-runner@sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2`
- Holdout digest: `b78d17006e270cec373aa130d7b0d11de357ffa236297b41075234e6ad7d5db8`

Policy digest (separate from holdout): `6737355947c21eb561073cb506ebc5698afd170088a34f8eaace50007c57d1a5` (line 16).

`trust-ci/README.md:90-99` and `QUICKSTART.md:105`: pins are `name@sha256:`; changing runner/policy/holdout changes policy digest and required check name.

DinD image pin is **not** in the activation report table.

## M0 status snapshot (docs only)

- API health on `127.0.0.1:18080` recorded ready (`plan:26`).
- Worker/DinD not running (`plan:25`, activation report line 5).
- `main` unprotected; leftover Actions workflow `340420982` still UNKNOWN / must disable by M0.3 (`spec:28,96`, `plan:47`, activation report line 29).
- Bootstrap exception still in `decisions.md:13-16,22-24` until live check exists (`DARK_FACTORY_ROADMAP.md:247`).
- `mistakes.md` has no Trust CI host/DinD/webhook entries.

## Implications for implementers (facts, not new APIs)

1. Fixing DinD (`rootlesskit` `operation not permitted`) is the recorded M0.1 gap; docs do not switch to host `/var/run/docker.sock`.
2. First Check Run still needs public HTTPS webhook, not loopback HMAC POST.
3. Use recorded App ID `4694114`, installation `156003193`, check name `adaptive-trust-ci/verified@6737355947c2`, image/holdout pins above.
4. Keep host name `claw`; do not reintroduce laptop language in spec/plan/activation report.
