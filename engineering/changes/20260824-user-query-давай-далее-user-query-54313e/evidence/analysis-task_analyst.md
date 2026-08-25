# task_analyst — remaining M0.3 after PUT branch protection

Route `54313e326a39`. Change `20260824-user-query-давай-далее-user-query-54313e`. Skills: `/adaptive-delivery`, `feature-workflow`. Allowed agents only. This agent does not implement, push, merge, disable workflows, POST statuses, read `.env`/PEM/JWT/admin tokens, or `funnel reset`.

**Question:** remaining M0.3 acceptance after PUT `main` protection already succeeded (`adaptive-trust-ci/verified@6737355947c2`, `app_id` 4694114, `enforce_admins`, no force-push/delete). Distinguish MUST-do now vs MUST-NOT. Name the proof that another actor posting the same check **text** does not satisfy `app_id` 4694114.

**Verdict:** PUT is live (GET matches the frozen payload). Leftover Actions workflow `340420982` is already `disabled_manually`. Remaining M0.3 is **prove the gate**, **supersede bootstrap-exception language**, and **fill the activation report**. Do **not** merge PR #5 while the App-owned Check Run is `action_required`. Do **not** treat PUT as M0.3 complete.

Write owner: `general_implementer` (docs/report after live proofs). Live GitHub negative tests need an exact delegated `external-write` / human admin git identity; this analyst does not run them.

---

## 1. Already done (do not repeat)

Live GET 2026-08-24, no secrets:

| Fact | Value |
| --- | --- |
| `GET /repos/Dimkox/adaptive-grok-build-pro/branches/main/protection` | **200** (no longer freeze 404) |
| Required check | `adaptive-trust-ci/verified@6737355947c2` |
| Bound `app_id` | **4694114** (`checks[]`, not name-only `contexts`) |
| `strict` (up-to-date) | true |
| `enforce_admins.enabled` | true |
| `allow_force_pushes.enabled` | false |
| `allow_deletions.enabled` | false |
| `required_linear_history` | true |
| `required_conversation_resolution` | true |
| `required_approving_review_count` | 0 (PR-required object present) |
| `restrictions` | null |
| Workflow `340420982` `trusted-ci` | **`disabled_manually`** (updated `2026-08-24T20:40:40+03:00`) |
| `.github/workflows/` in tree | absent (must stay absent) |

This matches `evidence/branch-protection-payload.json` and plan box 1 (`adaptive-trust-ci branch-protect` with epoch name **and** App ID). Plan box 3 (disable `340420982`) is **already true in the Actions catalog**. Do not re-PUT protection unless GET drifts. Do not re-enable the workflow. Do not add `.github/workflows/`.

PUT is configuration, not enforcement proof. Unit tests (`test_branch_protection_binds_epoch_check_to_app_id`) only assert the payload. Live GitHub must still refuse the wrong actor and the wrong git operations.

---

## 2. Live PR #5 (why merge is forbidden now)

| Field | Value |
| --- | --- |
| PR | [#5](https://github.com/Dimkox/adaptive-grok-build-pro/pull/5) draft, `state=open`, `merged=false` |
| `mergeable_state` | **`blocked`** |
| Base | `main` `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` |
| Head | `ac01326a4a3fde1d0630e621da51ef67379da191` |
| App Check Run | `97529209576` name `adaptive-trust-ci/verified@6737355947c2` |
| Owner | `app.id=4694114` slug `adaptive-trust-ci` |
| `external_id` (job) | `53870ce3-951c-4247-afe9-88969be5dc98` |
| `conclusion` | **`action_required`** (GitHub: not a passing conclusion) |
| Combined commit statuses | `total_count=0` (no same-text user status yet) |
| Other Check Run | GitGuardian `97529197793` `app.id=46505` name **`GitGuardian Security Checks`** `success` |

GitGuardian is a different **name** and a different **app**. It is **not** the actor-mismatch proof.

Activation report is stale vs this head (`56f5462` / `97527445754`, `main protected | false`, leftover workflow `UNKNOWN`). Filling those cells is remaining docs work, not a reason to merge.

---

## 3. MUST-do now vs MUST-NOT vs deferred

### MUST-do now

1. **App-bound actor-mismatch probe** (named below). Same check **text** from a non-4694114 actor must not satisfy protection.
2. **Negative git proofs** on `main` (expect GH006 / API 405–409; STOP if any succeed):
   - direct push (`git push origin HEAD:main`)
   - force-push (`git push --force`)
   - delete (`git push origin --delete main`)
   - merge-without-check (`gh pr merge 5` while App conclusion is not `success`)
   - same four as a **repository admin** (`enforce_admins` is on)
3. **Supersede bootstrap-exception language** (M1 start, PR #2, PR #4) in `README.md` L11, `decisions.md` (new 2026-08-24 revoke entry; do not silently delete history), CHANGELOG 2.0.12 current-state if it still claims the check is not live. Sibling `analysis-docs_researcher.md` lists the sentences.
4. **Fill** `engineering/runbooks/trust-ci-activation-report.md` with operator-safe IDs (no PEM/JWT/webhook secret/admin token/human private key):
   - `main` protected = **true**
   - Protection `app_id` = **4694114**
   - Leftover Actions workflow 340420982 = **`disabled_manually`**
   - Current disposable PR head / Check Run / `external_id` if the report is updated this slice
   - Bootstrap-exception superseded = dated pointer after the docs land
5. Tick plan M0.3 boxes that this slice actually proved (protect + disable already true; proofs + docs still open). Do **not** tick “Mark PR ready; merge…”.

### MUST-NOT (this slice and until a later named order)

| Forbidden | Why |
| --- | --- |
| **Merge PR #5** while Check Run `97529209576` (or any later head run of the required name) is `action_required` | Brief; GitHub `action_required` is not success; job is `needs_approval`; `mergeable_state=blocked`. A successful merge now would mean the gate failed. |
| `gh pr ready 5` / auto-merge | Last plan box is not this slice; draft is a second lock. |
| Grant repository **Administration** to App `4694114` | Spec/rollout: long-lived App stays Checks r/w, Contents read, PRs read. `branch-protect` uses a **temporary human** admin token only. |
| Mint, read, copy, or submit **human approval private keys** | M0.2 residual; keys never live on `claw` or in the agent workspace. Do not `approval-create` to unstick #5. |
| **Funnel reset** / change App webhook URL / add a repository webhook | Funnel `https://claw.taild9f611.ts.net/webhooks/github` is live M0.2 intake (`decisions.md`). Additive proofs must not `tailscale funnel reset`. |
| Forge `adaptive-trust-ci/verified@6737355947c2` **success** via App 4694114, user token, GitGuardian, or Actions | Same-text success from the **wrong** actor is the probe; success from the **right** App without attestation/approval is a forge. |
| Policy/holdout retitle | Would change `@6737355947c2` and invalidate the just-bound check name. Outside the PR trust domain. |
| Re-enable workflow `340420982` or add `.github/workflows/**` | Catalog leftover is already disabled; tree must stay Actions-free. |
| Re-PUT protection unless GET drifts | Avoid flapping `main` lock. |
| Print or commit PEM, JWT, webhook secret, admin token, human private key | Operator-safe evidence only. |

### Deferred — remaining M0.3 last box, not now

Plan: “Mark PR ready; merge only through the live App-owned check.”

That box is **merge-through-success**, not “merge the blocked draft.” It stays **unchecked** until an exact head SHA has App `4694114` Check Run `conclusion=success` (attestation-backed). That is blocked on M0.2 residuals (`needs_approval`, no human private key on claw, no live runner / source-mutation). User-closed M0.2 said those residuals are **not merge authority** — they also **do not authorize** merging `action_required`.

Do not invent a docs-only SHA to skip `needs_approval` in this bind-main slice unless a later user order names it.

---

## 4. Named proof: same check text from another actor ≠ App ID 4694114

**Name:** App-bound required-check **actor-mismatch probe**.

**Contract (already in git):** `required_status_checks.checks = [{context: "adaptive-trust-ci/verified@6737355947c2", app_id: 4694114}]`. `trust-ci/README.md`: “A status or check with the same text from another actor does not satisfy the requirement.” GitHub docs: a required check bound to an app fails with `Required status check "…" was not set by the expected GitHub App.`

PUT/GET of `app_id` is **necessary but not sufficient**. The missing proof is a live **wrong-actor** post of the **exact** context string plus a still-blocked merge.

### Setup (use PR #5 head; do not open a Funnel-resetting path)

- SHA: `ac01326a4a3fde1d0630e621da51ef67379da191` (refresh SHA if the PR moves; re-GET the App-owned run).
- Actor: a **user** PAT / `gh` user token with `repo:status` (or equivalent). **Not** App JWT, **not** installation token of 4694114, **not** Administration.
- Do **not** PATCH Check Run `97529209576`.

### Action

`POST /repos/Dimkox/adaptive-grok-build-pro/statuses/{head_sha}`

```json
{
  "state": "success",
  "context": "adaptive-trust-ci/verified@6737355947c2",
  "description": "M0.3 actor-mismatch probe; not App 4694114"
}
```

Exact `context` string. No extra suffix. This creates a **commit status**, not an App Check Run.

### Evidence that must all be true together

| # | Artifact (redact tokens) | Pass condition |
| --- | --- | --- |
| A | POST statuses response | `context` exact; `state=success`; `creator.type=User` **or** `app.id` absent / **≠ 4694114** |
| B | `GET /commits/{sha}/status` | Combined statuses list that context from the **user** actor |
| C | `GET /commits/{sha}/check-runs?check_name=adaptive-trust-ci%2Fverified%406737355947c2` | Required run still `id=97529209576` (or the current App-owned id), `app.id=4694114`, `app.slug=adaptive-trust-ci`, `conclusion=action_required`. User POST did **not** complete the App run. |
| D | `GET /pulls/5` | Still `draft=true`, `mergeable_state=blocked` |
| E | `PUT /pulls/5/merge` or `gh pr merge 5` | **Fails** (405/409). Prefer GitHub body `Required status check "adaptive-trust-ci/verified@6737355947c2" was not set by the expected GitHub App.` If GitHub only says the App-owned check is failing/`action_required`, that proves merge-without-success; **A+C** are then mandatory to prove **app_id** (same text exists from the wrong actor and does not own the required Check Run). |
| F | `GET /branches/main/protection` | Unchanged: `checks=[{context:"adaptive-trust-ci/verified@6737355947c2", app_id:4694114}]` |

Save redacted JSON under this change `evidence/` (status id, creator login/type, check-run `app.id`, merge error body, protection `checks[]`). No tokens.

### Not this proof

- GitGuardian `app.id=46505` / name `GitGuardian Security Checks`.
- Combined status empty (`total_count=0` today) — probe not started.
- Payload unit tests / PUT response `app_id` field alone.
- Forging App 4694114 `conclusion=success`.

### After the probe

Leave the user status as labeled probe evidence, or overwrite the **status** (not the App Check Run) with `state=failure` / a clear description. Do not “clean up” by completing the App run.

---

## 5. Other remaining Given / When / Then

**P0 — Direct push fails (including admin).**  
Given `main` protection as GET above and `enforce_admins`. When an admin (or any collaborator) `git push origin <any-sha>:main` without a PR. Then GitHub rejects (`GH006` / protected branch / required PR or required check). `main` SHA stays `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` unless a later legitimate merge happens. STOP if the push lands.

**P0 — Force-push fails.**  
When `git push --force origin main`. Then reject (`allow_force_pushes.enabled=false`). STOP if it lands.

**P0 — Delete fails.**  
When `git push origin --delete main`. Then reject (`allow_deletions.enabled=false`). STOP if it lands.

**P0 — Merge without App-owned success fails.**  
Given PR #5 `conclusion=action_required`. When `gh pr merge 5` (any method). Then fail; PR stays open/unmerged. This is both the merge-without-check proof and the MUST-NOT.

**P1 — Docs / report.**  
Given live GET + catalog disable. When the write owner edits operator docs. Then README no longer says the App-owned check is not live / PR #2 bootstrap exception is current; `decisions.md` has a **new** revoke entry (live check exists, not a forged one); activation report cells match GET (`main` protected true, `app_id` 4694114, workflow `disabled_manually`). No secrets. No claim “M0 complete” or “attestation verified.”

**P1 — Plan ticks.**  
Tick protect + disable + (after evidence) actor/git proofs + superseded language + filled report. Leave “Mark PR ready; merge only through the live App-owned check” **unchecked**.

---

## 6. Out of scope this slice

- Human Ed25519 `approval-create` / requeue of Check Run `97529209576`.
- Offline attestation verify (job `needs_approval`; GET attestation 404 is expected).
- Source-mutation fail-closed / start runner-loader.
- Policy/holdout retitle.
- M1–M9, `factory/`, VERSION bump, GitHub Release.
- Funnel / socat / compose recreate.
- Merging PR #5.

---

## 7. Residual risk

- Negative git tests are live mutations if GitHub unexpectedly allows them. Prefer a throwaway SHA; capture the **rejection** body; do not retry with bypass.
- `git push --dry-run` does **not** exercise GitHub branch protection; the proof needs a real rejected push or a rejected merge API call.
- Draft + `action_required` already blocks merge; the actor-mismatch probe must still show the **user** status is not the required App check.
- Sibling `analysis-repo_explorer.md` was written **before** this GET (it still says protection is not applied). Live GitHub now disagrees; prefer this report’s GET table for current `main`.
- Activation-report SHA/Check Run cells lag PR #5 head `ac01326` / `97529209576`. Update when filling the report; do not invent IDs.

---

## 8. Sources

Plan `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` M0.3; spec check contract + exit extras + forbidden; `engineering/runbooks/trust-ci-{rollout,activation-report}.md`; `trust-ci/README.md`; `trust-ci/src/adaptive_trust_ci/github.py` `branch_protection_payload`; this package `brief.md` + `evidence/branch-protection-payload.json`; siblings `analysis-docs_researcher.md` / `analysis-repo_explorer.md`; live GET protection, Check Run `97529209576`, workflow `340420982`, PR #5; GitHub support doc “Required status check … was not set by the expected GitHub App.” No `.env` / PEM.
