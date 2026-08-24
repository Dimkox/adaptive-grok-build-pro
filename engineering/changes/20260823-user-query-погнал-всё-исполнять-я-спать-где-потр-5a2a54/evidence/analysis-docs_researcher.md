# docs_researcher — Dark Factory M0/M1, remaining Trust CI ops, merge trust

Change: `20260823-user-query-погнал-всё-исполнять-я-спать-где-потр-5a2a54`  
Route: `5a2a54f045d1` (`docs_researcher` is in `allowed_agents`)  
Sources: `DARK_FACTORY_ROADMAP.md`, `GROK_BUILD_HANDOFF.md`, `engineering/runbooks/trust-ci-rollout.md`, `AGENTS.md`, `trust-ci/README.md`. No APIs invented.

## M0 is operations, not in-tree product files

`DARK_FACTORY_ROADMAP.md` names **M0 — Activate and prove the external Trust Authority**. Objective: “Turn the existing Trust CI source into the actual merge authority for `main`.”

Primary surfaces (ops / host / GitHub, not a new product module):

```text
trust-ci/
engineering/runbooks/trust-ci-rollout.md
repository GitHub App installation
repository webhook configuration
main branch protection
CI host runtime configuration
```

Work items are verify App install, operator-only App IDs, worker-only RSA key, API-only webhook secret, pin images/holdout, deploy on isolated CI host, webhook, disposable PR Check Run, attestation, protected-path approval, kill switch, then branch protection. Execution notes: “Start with M0 only” and “Stop at M0 exit criteria; do not begin M1 in the same branch.”

M0 exit criteria (live authority):

```text
main protected = true
required check = current adaptive-trust-ci/verified@<policy-sha12>
required check app_id = adaptive-trust-ci App ID
exact-SHA disposable PR = success
signed attestation = independently verified
protected-path approval flow = proven
backup + restore + restart drill = pass
kill switch = pass
no GitHub Actions = true
```

## M1 is the first in-tree product milestone

**M1 — Typed Intent, Acceptance Criteria, and Evidence Traceability** is the first milestone that adds product files under the repo (schema, CLI, tests, holdout validator). It may proceed only after M0 live proof or a user-recorded bootstrap exception.

### Recommended file structure (quote)

```text
schemas/change-spec.schema.json
.grok-stack/templates/change/change-spec.yaml
.grok-stack/adaptive_grok/spec.py
scripts/grok_spec.py
tests/test_change_spec.py
trust-ci/holdout.example/change_spec_validate.py
```

### Markdown cannot override typed spec (quote)

M1 exit criteria include:

- Markdown text cannot silently override typed fields;

Constraint 12: “No Markdown-only authority. Markdown remains useful explanation; machine-readable specifications and policies drive gates.” Work item: “Link Markdown `brief.md`, `requirements.md`, and `architecture.md` to the typed spec instead of duplicating authority.”

## Remaining ops (`GROK_BUILD_HANDOFF.md`)

Current code on `feat/trust-ci-control-plane` / draft PR #2 is source-complete; remaining work is operational. Order:

1. Reproduce local baseline (unit/compile/`grok_verify`).
2. Real PostgreSQL integration (`TRUST_CI_TEST_DATABASE_URL`; concurrent claim, lease reclaim, heartbeat, dead-letter, nonce replay, attestation durability, restart).
3. Build and pin immutable artifacts (digests, policy digest, SBOM, vuln scan, CI public key, holdout digest). Do not commit private keys.
4. Create/verify GitHub App (Checks r/w, Contents read, PRs read; App ID, installation ID, worker-only key, API-only webhook secret).
5. Deploy isolated CI host (PostgreSQL, migrate, API, worker, runner, holdout, HTTPS, backup, metrics).
6. Register webhook; prove exact-SHA App-owned check + offline attestation.
7. Prove approval matrix (docs-only vs `trust-ci/**`, wrong scope, tamper, nonce, SHA/policy invalidation).
8. Protect `main` only after live check success (PR required, exact policy-epoch check + App ID, no force-push/delete).
9. Finish PR #2 with SHA, PG output, digests, check run ID, attestation, protection proof, residual risks. Do not auto-merge unless the user orders it after reviewing external evidence.

`trust-ci-rollout.md` matches that sequence: prove App-owned policy epoch on a disposable PR before `branch-protect`; kill switch does not remove protection; rollback is previous images/policy/holdout (new epoch).

## AGENTS.md merge trust (authoritative vs workflow)

- Local receipts, prompts, hooks, `.grok-stack/runtime`, delegated grants, change packages, local tests, and agent reviews are **not** merge authority.
- Merge gate: GitHub App-owned Check Run `adaptive-trust-ci/verified@<policy-sha12>` on the **exact PR head SHA**, bound to the App ID.
- No GitHub Actions; Trust CI lives in `trust-ci/` with PostgreSQL, exact-SHA runners, external holdout, mutation detection, signed attestations, human Ed25519 approvals.
- Agents must never generate/read/submit a human approval private key.
- Repo PRs cannot change deployed policy, holdout, images, PostgreSQL, CI keys, App key, trust stores, or branch protection.
- `scripts/grok_approve.py` materializes named local ops only; it cannot create the Trust CI check or a human security approval.

## `trust-ci/README.md`

Service: HMAC webhook → PostgreSQL jobs/leases → exact-SHA checkout → holdout → no-network runner → mutation fail → Ed25519 attestation → App Check Run with policy-epoch suffix. API cannot publish a successful check; worker has no webhook secret/human trust store. Rollout order: deploy → webhook → disposable PR → observe App-owned check → verify attestation → **then** branch protection.

## Implication for this change

User “execute everything / auto-approve while sleeping” does **not** override M0: human Trust CI approval keys stay off-agent; “automatic approval” is at most named local grants (`grok_approve.py`), never the merge check. First executable slice remains **M0 live ops**. M1 product files (`schemas/change-spec.schema.json` and listed companions) must not share M0’s branch unless a documented bootstrap exception exists.

## Gaps (docs only)

Live App installation, check run ID, `main` protection, and holdout/image digests are **not** proven by these Markdown files; they must be verified against the live environment (`DARK_FACTORY_ROADMAP.md` §3.3).
