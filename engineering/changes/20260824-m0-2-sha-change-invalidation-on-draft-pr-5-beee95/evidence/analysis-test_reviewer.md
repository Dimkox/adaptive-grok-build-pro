# test_reviewer — M0.2 SHA-change invalidation (PRE-implementation)

Route: `beee95e0b3c6`. Change: `20260824-m0-2-sha-change-invalidation-on-draft-pr-5-beee95`. Read-only. No secrets.

This slice’s product work is **docs + live proof on draft PR #5**, not new store/API code. Automated tests already encode SHA-change and Check Run `external_id` reuse. They do **not** replace GitHub App Check Runs on a **real** SHA.

## What unit/integration tests already cover

### Superseded head / enqueue on a new SHA

| Test | File | What it proves |
| --- | --- | --- |
| `StoreTests.test_new_head_cancels_old_active_job` | `trust-ci/tests/test_store.py` | Same repo+PR, new `head_sha` → old MemoryStore job `status=cancelled`, new job `queued`. |
| `StoreTests.test_enqueue_is_idempotent_for_same_sha_and_policy` | same | Same SHA+policy digest → same `job_id`, `created=False`. |
| `PostgresStoreTests.test_duplicate_webhook_identity_returns_same_job` | `trust-ci/tests/test_postgres_integration.py` | Durable uniqueness of `(repo, pr, head_sha, policy)` identity. **Does not** assert cancel-on-new-SHA against Postgres (gap vs MemoryStore). |
| `WebhookTests.test_synchronize_is_supported` | `trust-ci/tests/test_webhooks_github.py` | `pull_request` `synchronize` parses new head SHA. |
| `WebhookTests.test_draft_pull_request_is_enqueued` | same | Drafts are not skipped. |

No test named `superseded`. Store language is **`cancelled`**, not `superseded`. Roadmap “stale tasks become superseded” is not this job-status enum.

### Check Run reuse by `external_id`

| Test | File | What it proves |
| --- | --- | --- |
| `GitHubTests.test_create_check_run_uses_installation_token_exact_sha_and_external_id` | `test_webhooks_github.py` | POST `head_sha` + `external_id` + installation token; GET filtered by check name. Fake HTTP. |
| `GitHubTests.test_existing_check_run_is_restarted_instead_of_duplicated` | same | If GitHub returns a run with matching `external_id`, **PATCH** that id, **no** second POST. Same SHA in the fixture. |
| `JobRunnerTests.test_passing_job_uses_epoch_check_runs_holdout_and_signed_attestation` | `trust-ci/tests/test_runner.py` | Worker `ensure_check_run(..., external_id=job_id)`. Fake GitHub. |

Implication for this slice: reuse is **per job_id / external_id on one SHA**. A **new** job for a **new** SHA must create a **new** Check Run. Tests never assert “do not PATCH Check Run `97390635614` after a later SHA.” That is live-only.

## Live proof those tests do **not** cover

Automated tests use FakeTransport / FakeGitHub / MemoryStore (Postgres uniqueness only). They **cannot** prove:

1. GitHub App Check Run **id** `97390635614` remains listed on real SHA `1fc942065a124ce75659bd082519d8ebc37774e8` after PR #5 head moves.
2. A **different** App-owned Check Run id (`app.id=4694114`, name `adaptive-trust-ci/verified@6737355947c2`) appears on the **new** PR head SHA with `external_id` = **new** `job_id`.
3. Loopback HMAC `synchronize` to `127.0.0.1:18080` vs a **registered public** `POST https://<ci>/webhooks/github` (still **not done**).
4. Worker-only GitHub App RSA actually POSTs Checks API (tests inject tokens; no PEM in-repo).
5. Branch-protection / merge gate on `main` (out of scope; M0.3).

**Required evidence for this slice:** `gh api` on PR #5 + check-runs for **two** SHAs, plus API JSON `created: true` and a new `job_id`. Unit tests staying green is necessary but **not** sufficient.

## Characterization that **must stay green** after docs update

File: `trust-ci/tests/test_m0_invariants.py` → `test_activation_report_operator_safe` (and siblings in the same class).

After any edit to spec / plan / `engineering/runbooks/trust-ci-activation-report.md`:

| Assertion | Must remain |
| --- | --- |
| Check Run id not `UNKNOWN` | `assertNotIn("UNKNOWN", report.split("Check Run id", 1)[1].split("\|", 2)[1])` — the **Check Run id** cell stays a real id (today `97390635614`). Other report cells may still say `UNKNOWN`. |
| Local HMAC | `assertIn("local HMAC", plan)` — plan still names **local HMAC**, not a public webhook as complete. |
| No public HTTPS / not done | `assertTrue("no public HTTPS" in plan or "not done" in plan)` — M0.2 webhook registration remains incomplete. |

Also keep green (docs-sensitive):

- `test_m0_spec_and_plan_exist`: spec still has `adaptive-trust-ci/verified@` and base SHA `48cb9737fac7f26fb70b425957a3ed64d4c1eb55`; no `BEGIN RSA PRIVATE KEY`.
- `test_m0_docs_name_claw_not_laptop`: `claw` in spec+plan; no `laptop` in spec.
- `test_activation_report_operator_safe` PEM markers absent from spec, plan, report.

Do **not** assert “main is unprotected” (plan: would fight M0.3). Do **not** put PEM, JWT, webhook secret, or installation tokens in those files (tests scan PEM markers only; still do not leak HMAC material).

## Gaps (characterization this slice does **not** need to add unless code changes)

- Postgres `test_new_head_cancels_old_active_job` analog — live HMAC + store inspect is the proof; optional later.
- End-to-end GitHub Check API against a real SHA — **cannot** be a hermetic unit test; live `gh api` only.
- Public HTTPS webhook — out of scope; keep “not done”.

## Verification command (after docs, still hermetic)

```bash
python3 -m unittest trust-ci.tests.test_m0_invariants
```

Pass/fail of that file is **doc invariant** proof, not App-owned live SHA proof.

**Verdict:** existing unit/integration coverage is **adequate for store cancel + check-run external_id reuse**. **Inadequate as sole evidence** for M0.2 SHA-change on draft PR #5. Live GitHub Check Runs on two exact SHAs remain mandatory. Keep `test_m0_invariants` green under the three constraints above.
