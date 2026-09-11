# Docs research — plan / activation-report cells after GitHub `pull_request` 200 on SHA `92ddbd9`

Change: `20260824-user-query-далее-user-query-5b9bcb`. Route `5b9bcb7d60d7`. Read-only.

Sources: `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`, `engineering/runbooks/trust-ci-activation-report.md`, `trust-ci/tests/test_m0_invariants.py`, `engineering/changes/20260824-configure-github-app-webhook-pull-request-https-cec0c7/evidence/release-review.md`.

Assumed live facts (operator/this slice, not invented APIs): GitHub App `pull_request` delivery HTTP **200** (`accepted` + `job_id`) and a Trust CI job/Check Run for exact head **`92ddbd9f69c5c560f257fd61fa9c902f43f67e50`**. Do not invent Check Run numeric ids.

## Invariant (must keep)

`test_activation_report_operator_safe` requires **`local HMAC` in the plan** and (`not done` **or** `no public HTTPS`). Keep SHA-change **history** as local HMAC: Check Run `97390635614` on `1fc9420`, later local HMAC `97406973020` on `ce03c87`. Do not claim M0.2 complete. Do not protect `main`.

## Plan (`docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`) — allowed edits

| Line | May update | Must not |
| --- | --- | --- |
| Register GitHub App webhook | Reword from “no pull_request delivery” / unsubscribed to **App webhook** + **GitHub `pull_request` 200** on Funnel URL. May tick **this** checkbox only if that delivery is operator-proven. | Tick from ping-only or UI Active. Drop Funnel URL. |
| Disposable docs PR / Check Run | **Partial:** current identity = GitHub-delivery Check Run on **`92ddbd9`** (id/`external_id` when known). Keep **local HMAC** history in the same bullet. Keep “Not M0.2 complete.” | Replace history; drop `local HMAC`; mark M0.2 complete. |
| SHA change / policy retitle | Keep SHA-change **proven** on local HMAC pair. Policy/holdout retitle stays **open**. | Check the combined line as done. |
| Attestation, Ed25519 requeue, source-mutation, protect `main` | Unchanged `[ ]`. | Tick. |
| Backup/kill-switch | Already `[x]` host-local; leave. | Tie them to M0.2 complete. |

## Activation report — allowed **current-identity** cells

| Cell | After `pull_request` 200 + job on `92ddbd9` |
| --- | --- |
| GitHub App webhook URL (inbound) | Keep Funnel URL. Replace “not a pull_request delivery” with **GitHub `pull_request` 200** (ping 200 may stay as history). |
| Disposable PR number | Stay **5** unless GitHub says otherwise. |
| Disposable PR head SHA | **Current cell → `92ddbd9f69c5c560f257fd61fa9c902f43f67e50`**. Old SHAs stay in **SHA-change history** prose (local HMAC). |
| Check Run id / `external_id` | **Current cells → GitHub-delivery Check Run / job** (numeric, never `UNKNOWN`). Old ids stay history. |
| Product base SHA | Stay `48cb973…`. |
| `TRUST_CI_PUBLIC_BASE_URL` | Stay `http://127.0.0.1:18080` until public HTTPS `/health/ready` is Trust CI. Funnel inbound ≠ this cell. |
| `main` protected / Protection `app_id` / leftover Actions / bootstrap | Stay **false** / UNKNOWN as today. |
| Images, policy, holdout, drills | Unchanged unless independently re-probed. |

Prose: first Check Run remains **loopback HMAC**, not a registered hook **at that time**. New sentence may name GitHub-delivery job on `92ddbd9`. Keep “Local HMAC … history”. Repo hooks stay empty (do not add a repository webhook).

## Not M0.2 complete

Plan M0.2 still needs: public HTTPS as designed (report public base still loopback), offline attestation, policy/holdout retitle, human Ed25519 requeue of the **same** Check Run, source-mutation fail-closed, **do not protect `main`**. One `pull_request` 200 does not close the milestone.
