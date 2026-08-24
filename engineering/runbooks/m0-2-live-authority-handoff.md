# M0.2 Live Trust Authority — Claw handoff

> Canonical operator handoff for continuing M0.2 on `claw` with Grok Build CLI. This document contains no private keys, tokens, webhook secrets, admin credentials, or signed approval envelopes.

## Scope

Close only **M0.2 — Live authority proof**.

Do not begin M0.3 branch protection until all M0.2 exit criteria below are proven. Do not begin M1 or any later dark-factory milestone in this branch.

The required external chain is:

```text
GitHub pull_request webhook over public HTTPS
→ HMAC verification by Trust CI API
→ durable exact-SHA PostgreSQL job
→ worker-owned GitHub App Check Run
→ protected-path needs_approval
→ human Ed25519 approval submitted externally
→ exact job requeued into the same Check Run
→ independent verification
→ signed attestation verified offline
```

M0.2 must also prove:

```text
new head SHA invalidates the old result
policy or holdout change creates a new check-name epoch
tracked-source mutation fails closed even when the command exits 0
backup, restore, restart, and kill-switch behavior remain sound
```

`main` remains unprotected during M0.2.

## Domain rule

No public hostname is assumed by this repository or handoff.

The operator must explicitly choose and export:

```bash
export TRUST_CI_PUBLIC_FQDN='<operator-chosen-public-fqdn>'
export TRUST_CI_PUBLIC_URL="https://${TRUST_CI_PUBLIC_FQDN}"
```

Examples in documentation may use `ci.example.com`, but no unrelated project domain may be inferred or reused automatically.

## Repository state

Repository:

```text
Dimkox/adaptive-grok-build-pro
```

Working branch:

```text
milestone/m0-live-trust-authority
```

Draft pull request:

```text
PR #5
```

Remote PR state when this handoff was created:

```text
remote head: ce03c87b3d9b8767105c01270869e33b50af56df
base main: 48cb9737fac7f26fb70b425957a3ed64d4c1eb55
```

The operator reported a newer local commit:

```text
92ddbd9
```

That commit is intentionally **not pushed** by this handoff. Pushing it to PR #5 is a separate explicitly delegated action.

Do not switch branches, reset, rebase, stash, or discard local M0 work merely to read this handoff.

## Known live facts

Host:

```text
claw
```

Internal API listener:

```text
127.0.0.1:18080 → Trust CI API container :8080
```

Internal readiness probe:

```bash
curl -fsS http://127.0.0.1:18080/health/ready
```

GitHub App identity:

```text
slug: adaptive-trust-ci
App ID: 4694114
Installation ID: 156003193
```

Current policy epoch:

```text
policy digest: 6737355947c21eb561073cb506ebc5698afd170088a34f8eaace50007c57d1a5
check name: adaptive-trust-ci/verified@6737355947c2
```

Existing loopback proof:

```text
PR: #5
proved head SHA: 1fc942065a124ce75659bd082519d8ebc37774e8
Check Run ID: 97390635614
external_id/job_id: 1b63d10b-90c1-498a-97b8-7b5e0ea76aec
conclusion: action_required
job state: needs_approval
```

This was created by a loopback HMAC POST, not by a GitHub-delivered public webhook. It does not close M0.2.

Immutable artifacts currently recorded:

```text
API:    ghcr.io/dimkox/adaptive-trust-ci-api@sha256:70a80960486b6008dac2dfe2ffc8e0b8e28f7ed8c03c52e673188fdb11207b23
Worker: ghcr.io/dimkox/adaptive-trust-ci-worker@sha256:bffd013ce1510bda55c74fa7926647f0000c3fc84dbd55114f36ea74b5f62227
Runner: ghcr.io/dimkox/adaptive-trust-ci-runner@sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2
Holdout digest: b78d17006e270cec373aa130d7b0d11de357ffa236297b41075234e6ad7d5db8
```

Execution topology:

- nested rootless DinD is not used;
- worker runs through the untracked host-socket overlay;
- API must not receive the GitHub App private key;
- worker must not receive the webhook secret or human private approval key;
- human private approval key must never exist in an agent workspace;
- GitHub Actions remain forbidden;
- `main` remains unprotected until M0.3.

## Open blockers

1. public HTTPS endpoint;
2. GitHub App webhook registration and successful signed delivery;
3. human Ed25519 key and server-side public trust-store entry;
4. human-signed exact-SHA requeue of the same Check Run;
5. completed attestation and offline verification;
6. new-head invalidation proof;
7. policy/holdout epoch retitle proof;
8. tracked-source mutation fail-closed proof;
9. current backup/restore/restart evidence.

---

# Phase A — public HTTPS edge

## A1. Select one ingress pattern

Use exactly one:

### Pattern A — direct DNS + Apache + Let’s Encrypt

Use when `claw` can accept public TCP 80 and 443. This is the preferred initial pattern because Apache already exists on the host.

### Pattern B — managed HTTPS tunnel

Use only when direct public 80/443 is unavailable. The tunnel must preserve the raw request body and GitHub headers, forward only to `127.0.0.1:18080`, use a stable operator-owned FQDN, and run under a managed service. Record the provider, tunnel identity, DNS ownership, and restart policy in the activation report.

Do not run both patterns for the same webhook URL.

The commands below implement Pattern A.

## A2. Configure DNS

Create an `A` record for `$TRUST_CI_PUBLIC_FQDN` pointing to the public IPv4 address of `claw`.

Do not create an `AAAA` record unless IPv6 routing, firewall, and Apache are deliberately configured.

Verify:

```bash
dig +short A "$TRUST_CI_PUBLIC_FQDN"
dig +short AAAA "$TRUST_CI_PUBLIC_FQDN"
```

Expected:

- `A` returns the public IPv4 of `claw`;
- `AAAA` is empty unless IPv6 is explicitly supported.

## A3. Verify listeners and firewall

```bash
sudo ss -ltnp | grep -E ':(80|443|18080)\s' || true
sudo apache2ctl -S
sudo systemctl status apache2 --no-pager
sudo ufw status
```

Required state:

```text
Apache owns public :80 and :443
Trust CI API remains on 127.0.0.1:18080
TCP 80 and 443 are open in host and provider firewalls
TCP 18080 is not exposed publicly
```

Do not change the API binding to `0.0.0.0:18080`.

## A4. Install TLS and proxy dependencies

```bash
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-apache dnsutils
sudo a2enmod ssl proxy proxy_http headers rewrite
```

## A5. Create ACME webroot and HTTP vhost

```bash
sudo install -d -m 0755 \
  /var/www/trust-ci-acme/.well-known/acme-challenge \
  /var/www/trust-ci-empty
```

```bash
sudo tee /etc/apache2/sites-available/trust-ci.conf >/dev/null <<APACHE
<VirtualHost *:80>
    ServerName ${TRUST_CI_PUBLIC_FQDN}
    DocumentRoot /var/www/trust-ci-acme

    <Directory "/var/www/trust-ci-acme">
        Options -Indexes
        AllowOverride None
        Require all granted
    </Directory>

    ErrorLog \${APACHE_LOG_DIR}/trust-ci-error.log
    CustomLog \${APACHE_LOG_DIR}/trust-ci-access.log combined
</VirtualHost>
APACHE
```

```bash
sudo a2ensite trust-ci.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
curl -I "http://${TRUST_CI_PUBLIC_FQDN}/"
```

The request must reach `claw`. Timeout or another host is a blocker.

## A6. Obtain the certificate

Set a real operator email in the shell only:

```bash
export TRUST_CI_ACME_EMAIL='<operator-email>'
```

```bash
sudo certbot certonly \
  --webroot \
  -w /var/www/trust-ci-acme \
  -d "$TRUST_CI_PUBLIC_FQDN" \
  --agree-tos \
  --non-interactive \
  -m "$TRUST_CI_ACME_EMAIL"
```

Verify:

```bash
sudo test -s "/etc/letsencrypt/live/${TRUST_CI_PUBLIC_FQDN}/fullchain.pem"
sudo test -s "/etc/letsencrypt/live/${TRUST_CI_PUBLIC_FQDN}/privkey.pem"
```

## A7. Install final Apache reverse proxy

```bash
sudo tee /etc/apache2/sites-available/trust-ci.conf >/dev/null <<APACHE
<VirtualHost *:80>
    ServerName ${TRUST_CI_PUBLIC_FQDN}

    Alias "/.well-known/acme-challenge/" "/var/www/trust-ci-acme/.well-known/acme-challenge/"
    <Directory "/var/www/trust-ci-acme/.well-known/acme-challenge/">
        Options None
        AllowOverride None
        Require all granted
    </Directory>

    RewriteEngine On
    RewriteCond %{REQUEST_URI} !^/\.well-known/acme-challenge/
    RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [R=308,L]

    ErrorLog \${APACHE_LOG_DIR}/trust-ci-error.log
    CustomLog \${APACHE_LOG_DIR}/trust-ci-access.log combined
</VirtualHost>

<VirtualHost *:443>
    ServerName ${TRUST_CI_PUBLIC_FQDN}

    SSLEngine On
    SSLCertificateFile /etc/letsencrypt/live/${TRUST_CI_PUBLIC_FQDN}/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/${TRUST_CI_PUBLIC_FQDN}/privkey.pem
    Include /etc/letsencrypt/options-ssl-apache.conf

    ProxyRequests Off
    ProxyPreserveHost On
    ProxyTimeout 25

    RequestHeader unset Proxy early
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port "443"

    LimitRequestBody 10485760

    ProxyPass "/webhooks/github" "http://127.0.0.1:18080/webhooks/github" connectiontimeout=3 timeout=25 retry=0
    ProxyPassReverse "/webhooks/github" "http://127.0.0.1:18080/webhooks/github"

    ProxyPass "/approvals" "http://127.0.0.1:18080/approvals" connectiontimeout=3 timeout=25 retry=0
    ProxyPassReverse "/approvals" "http://127.0.0.1:18080/approvals"

    ProxyPass "/health/" "http://127.0.0.1:18080/health/" connectiontimeout=3 timeout=10 retry=0
    ProxyPassReverse "/health/" "http://127.0.0.1:18080/health/"

    <Location "/webhooks/github">
        Require all granted
        <LimitExcept POST>
            Require all denied
        </LimitExcept>
    </Location>

    <Location "/approvals">
        Require all granted
        <LimitExcept POST>
            Require all denied
        </LimitExcept>
    </Location>

    DocumentRoot /var/www/trust-ci-empty
    <Directory "/var/www/trust-ci-empty">
        Options -Indexes
        AllowOverride None
        Require all denied
    </Directory>

    Header always set Strict-Transport-Security "max-age=31536000"
    Header always set X-Content-Type-Options "nosniff"
    Header always set Referrer-Policy "no-referrer"

    LogFormat "%a %t \"%r\" %>s %b delivery=%{X-GitHub-Delivery}i event=%{X-GitHub-Event}i" trustci
    ErrorLog \${APACHE_LOG_DIR}/trust-ci-error.log
    CustomLog \${APACHE_LOG_DIR}/trust-ci-access.log trustci
</VirtualHost>
APACHE
```

```bash
sudo apache2ctl configtest
sudo systemctl reload apache2
```

## A8. Change the deployment public URL

Change only the gitignored deployment environment:

```bash
cd ~/grok-projects/adaptive-grok-build-pro/trust-ci

sed -i \
  "s#^TRUST_CI_PUBLIC_BASE_URL=.*#TRUST_CI_PUBLIC_BASE_URL=${TRUST_CI_PUBLIC_URL}#" \
  env/common.env

grep '^TRUST_CI_PUBLIC_BASE_URL=' env/common.env
```

Find and reuse the existing untracked host-socket overlay:

```bash
find "$HOME" -name 'compose.host-socket.yaml' -type f -print
export HOST_SOCKET_OVERLAY='<absolute-path-returned-above>'
```

Recreate only API and worker through the same topology:

```bash
docker compose \
  -f compose.yaml \
  -f "$HOST_SOCKET_OVERLAY" \
  up -d --force-recreate api worker
```

Verify:

```bash
curl -fsS http://127.0.0.1:18080/health/ready
curl -fsS "${TRUST_CI_PUBLIC_URL}/health/ready"
```

## A9. Prove public TLS reaches the HMAC gate

An unsigned request must reach FastAPI and receive `401`:

```bash
curl -sS \
  -o /tmp/trust-ci-webhook-unsigned.out \
  -w 'HTTP=%{http_code} TLS_VERIFY=%{ssl_verify_result}\n' \
  -X POST \
  "${TRUST_CI_PUBLIC_URL}/webhooks/github" \
  -H 'Content-Type: application/json' \
  -H 'X-GitHub-Event: ping' \
  --data '{}'

cat /tmp/trust-ci-webhook-unsigned.out
```

Expected:

```text
HTTP=401
TLS_VERIFY=0
```

Verify renewal:

```bash
sudo certbot renew --dry-run
```

Stop before GitHub registration if TLS fails, Apache returns `404`/`502`, readiness returns `503`, or the unsigned HMAC probe does not return `401`.

---

# Phase B — GitHub App webhook

## B1. Configure the existing App

Open the existing App settings page:

```text
https://github.com/settings/apps/adaptive-trust-ci
```

Configure:

```text
Webhooks: Active
Webhook URL: ${TRUST_CI_PUBLIC_URL}/webhooks/github
Webhook secret: exactly TRUST_CI_WEBHOOK_SECRET from the API deployment environment
SSL verification: Enabled
Subscribe to events: Pull request
```

Do not paste the secret into Git, chat, PR descriptions, logs, or evidence.

Do not add a duplicate repository webhook while the App webhook is active.

## B2. Prove signed delivery

Use GitHub App **Recent deliveries**.

Expected `ping` result:

```text
HTTP 200
```

A response saying the event was ignored is acceptable: HMAC passed and `ping` is not a pull-request event.

Monitor:

```bash
sudo tail -f \
  /var/log/apache2/trust-ci-access.log \
  /var/log/apache2/trust-ci-error.log
```

```bash
cd ~/grok-projects/adaptive-grok-build-pro/trust-ci

docker compose \
  -f compose.yaml \
  -f "$HOST_SOCKET_OVERLAY" \
  logs -f api worker
```

Diagnostic table:

| Result | Meaning |
| --- | --- |
| TLS failure | DNS, certificate, firewall, or invalid AAAA |
| timeout | firewall or Apache listener |
| `404` | wrong path or proxy rule |
| `401` | GitHub and API webhook secrets differ |
| `502` | Apache cannot reach loopback API |
| `503` | PostgreSQL, trust store, or kill switch not ready |
| `200` | public signed webhook path works |

## B3. Trigger a real pull-request event

Do not push automatically.

After the user explicitly delegates pushing local commit `92ddbd9`:

```bash
cd ~/grok-projects/adaptive-grok-build-pro

git status --short --branch
git log --oneline --decorate -5
git show --stat --oneline 92ddbd9
```

Materialize only the named `git-push-branch` delegated grant and push `milestone/m0-live-trust-authority`.

The push must generate a real GitHub App `pull_request/synchronize` delivery.

Capture without secrets:

```text
GitHub delivery ID
HTTP response code
PR number
exact new head SHA
job ID
Check Run ID
Check Run App ID
check name/policy epoch
```

A diff touching `trust-ci/**` is expected to enter `needs_approval` with Check Run conclusion `action_required`.

---

# Phase C — human Ed25519 approval

## C1. Generate the human key outside Claw and outside agent workspaces

Run on a human-controlled workstation:

```bash
mkdir -p ~/.config/adaptive-trust-ci
chmod 700 ~/.config/adaptive-trust-ci

adaptive-trust-ci keygen \
  --private ~/.config/adaptive-trust-ci/operator.pem \
  --public ~/.config/adaptive-trust-ci/operator.pub.pem
```

The private key must never be copied to `claw`, the repository, an agent workspace, API, worker, container image, logs, or chat.

Record only the printed `key_id` and public key.

## C2. Add only the public key to the server trust store

On `claw`, edit the gitignored server-side trust store. Use schema version 2:

```json
{
  "schema_version": 2,
  "keys": [
    {
      "key_id": "<key-id>",
      "actor": "dmitry",
      "scopes": ["governance", "database", "production"],
      "not_before": "<UTC timestamp>",
      "not_after": "<UTC timestamp>",
      "revoked_at": null,
      "public_key_pem": "<public Ed25519 PEM only>"
    }
  ]
}
```

Validate without printing private material:

```bash
cd ~/grok-projects/adaptive-grok-build-pro/trust-ci

PYTHONPATH=src python3 -m adaptive_trust_ci.cli trust-store-validate \
  --trust-store runtime/trust-store.json
```

Recreate only the API so it reloads the trust store:

```bash
docker compose \
  -f compose.yaml \
  -f "$HOST_SOCKET_OVERLAY" \
  up -d --force-recreate api
```

Verify readiness again.

## C3. Obtain the exact job binding

For the current `needs_approval` job record:

```text
repository
PR number
base SHA
head SHA
policy digest
required scope
job ID
Check Run ID
```

Do not guess or reuse values from an older SHA.

Download or securely transfer the exact deployed public policy JSON to the human workstation. It contains no private key but must be treated as reviewed configuration.

## C4. Create and verify approval on the human workstation

```bash
adaptive-trust-ci approval-create \
  --private-key ~/.config/adaptive-trust-ci/operator.pem \
  --policy ./deployed-policy.json \
  --actor dmitry \
  --repository Dimkox/adaptive-grok-build-pro \
  --pr-number 5 \
  --base-sha '<exact-base-sha>' \
  --head-sha '<exact-head-sha>' \
  --scope governance \
  --reason 'Reviewed exact M0 Trust CI governance diff' \
  --ttl 900 \
  --output /tmp/m0-approval.json
```

Verify locally before submission:

```bash
adaptive-trust-ci approval-verify \
  --approval /tmp/m0-approval.json \
  --trust-store ./public-trust-store.json \
  --policy ./deployed-policy.json \
  --repository Dimkox/adaptive-grok-build-pro \
  --pr-number 5 \
  --base-sha '<exact-base-sha>' \
  --head-sha '<exact-head-sha>'
```

## C5. Submit through public HTTPS

```bash
adaptive-trust-ci approval-submit \
  --approval /tmp/m0-approval.json \
  --url "$TRUST_CI_PUBLIC_URL"
```

Required proof:

- approval ID and nonce are accepted once;
- replay returns conflict/rejection;
- wrong scope, expired TTL, changed SHA, or changed policy digest is rejected;
- the exact `needs_approval` job is requeued;
- the **same Check Run ID** is resumed rather than a duplicate check being created.

## C6. Complete and verify the attestation

After the job passes, retrieve its attestation through the authenticated operator path or directly from operator-controlled storage.

Verify on a machine with the published CI public key:

```bash
adaptive-trust-ci attestation-verify \
  --attestation ./attestation.json \
  --public-key ./trust-ci-signing-key.pub.pem
```

Record only:

```text
attestation ID
job ID
repository
base SHA
head SHA
policy digest
status
CI key ID
verification result
```

Do not record private keys or raw credentials.

---

# Phase D — invalidation and policy epoch proofs

## D1. New-head invalidation

After a successful exact-SHA result, create a separate reviewed disposable docs commit and push it only with explicit authorization.

Required behavior:

```text
old Check Run remains bound to old head SHA
new pull_request/synchronize delivery creates a job for new head SHA
old approval is not valid for new head SHA
old success cannot satisfy the new head
```

Capture old and new head SHAs, job IDs, and Check Run IDs.

## D2. Policy/holdout retitle and source-mutation drill

Perform this only while `main` is unprotected.

Use a temporary, operator-reviewed **probe policy epoch** that adds one mandatory sandbox command which:

1. modifies a tracked disposable file in the checkout;
2. exits with status 0.

Procedure:

1. archive the current deployed policy and its digest;
2. create a reviewed probe policy outside Git;
3. calculate its policy digest and expected new check name;
4. restart API and worker with the probe policy;
5. trigger a disposable PR synchronization;
6. verify the check name changed to the probe epoch;
7. verify the job fails because tracked source changed, not because the command exited non-zero;
8. restore the reviewed production policy;
9. restart API and worker;
10. verify the production policy digest and check name are restored or intentionally replaced by a reviewed final epoch.

Do not commit the probe policy. Do not enable branch protection while a temporary probe epoch is active.

Evidence:

```text
old policy digest and check name
probe policy digest and check name
exact probe head SHA
probe job and Check Run IDs
command exit code 0
source-mutation failure code
restored/final policy digest and check name
```

A real reviewed holdout enhancement may be used instead of a temporary policy command. Do not add meaningless marker files to the long-lived holdout merely to change a digest.

---

# Phase E — recovery drills

## E1. Kill switch

The existing host-local drill passed. Reconfirm after the public edge is active:

```text
kill switch on → readiness 503, new jobs and approvals rejected
kill switch off → readiness 200, no guardrail disabled
```

## E2. PostgreSQL restart

With a durable queued or non-terminal test job:

1. restart PostgreSQL;
2. confirm jobs, attempts, approvals, and attestations persist;
3. confirm expired lease reclaim works;
4. confirm no duplicate Check Run is created.

## E3. Backup and restore

Use the existing backup CLI and restore only into an explicitly disposable database.

Required evidence:

```text
backup manifest SHA-256 verified
restore into disposable database succeeds
schema migration status is clean
known job and attestation rows are present
production database is untouched
```

---

# M0.2 exit criteria

All must be true:

```text
operator-selected public FQDN resolves correctly
TLS certificate validates publicly
unsigned public webhook request reaches HMAC gate and returns 401
GitHub App ping delivery returns 200
real pull_request delivery reaches API through public HTTPS
exact-SHA PostgreSQL job is created
App-owned Check Run uses App ID 4694114
trust-ci diff enters needs_approval
human Ed25519 approval requeues the exact job and same Check Run
approval replay, wrong scope, stale SHA, stale policy, and expiry are rejected
completed signed attestation verifies offline
new head SHA invalidates old evidence
policy/holdout change retitles the check epoch
source mutation fails despite command exit 0
kill-switch, restart, backup, and restore drills pass
main remains unprotected
no GitHub Actions are added or used
```

Only after these criteria are recorded may M0.3 begin.

# Evidence updates

Update these files on the milestone branch after the live proof:

```text
docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md
engineering/runbooks/trust-ci-activation-report.md
decisions.md or mistakes.md only when a durable reviewed lesson exists
```

Operator-safe activation report may include:

```text
public FQDN
App ID and Installation ID
GitHub delivery IDs
exact base/head SHAs
job IDs and Check Run IDs
policy and holdout digests
image digests
attestation ID and public key ID
branch protection state
backup/restart/kill-switch results
```

Never include:

```text
PEM private keys
JWTs
installation tokens
webhook secret
read/admin tokens
human signed approval payload
filled secret env files
```

# Git discipline

Before any push:

```bash
git status --short --branch
git diff --check
git log --oneline --decorate -5
```

Do not push `92ddbd9` until the user explicitly delegates that exact branch push.

Do not push directly to `main`.

Do not mark PR #5 ready and do not merge it during M0.2.

# Grok Build CLI instruction

```text
Read AGENTS.md, decisions.md, mistakes.md,
docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md,
docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md,
engineering/runbooks/trust-ci-activation-report.md, and
engineering/runbooks/m0-2-live-authority-handoff.md.

Continue only M0.2 on the current milestone/m0-live-trust-authority branch.
Do not switch branches, stash, reset, rebase, discard local work, protect main,
start M1, or add GitHub Actions.

Do not infer a domain name. Require the operator to set TRUST_CI_PUBLIC_FQDN
and TRUST_CI_PUBLIC_URL explicitly. Never print or commit secrets.

First prove public HTTPS and HMAC behavior. Then configure the existing
adaptive-trust-ci GitHub App webhook and prove a real signed GitHub delivery.
Do not push local commit 92ddbd9 until the user explicitly delegates that
branch push.

Human Ed25519 key generation and approval signing happen only on a
human-controlled workstation. The agent may work with the public key and
operator-safe identifiers, but must never read or handle the human private key.

Close human requeue, offline attestation verification, new-SHA invalidation,
policy/holdout retitle, source-mutation failure, and recovery drills. Update the
operator-safe plan/report with exact evidence. Stop when M0.2 exit criteria are
met. Do not begin M0.3.
```
