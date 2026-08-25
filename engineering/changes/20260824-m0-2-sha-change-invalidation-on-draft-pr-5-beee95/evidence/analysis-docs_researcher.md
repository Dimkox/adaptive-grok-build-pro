# Docs research — SHA-change invalidation vs tracked docs

Change: `20260824-m0-2-sha-change-invalidation-on-draft-pr-5-beee95`  
Route: `beee95e0b3c6`  
Sources: activation report, M0 plan M0.2, `trust-ci/tests/test_m0_invariants.py`, `decisions.md` top entries, README current-state on `main` 2.0.12. No secrets.

## Current bound identities (must not be invented)

From `engineering/runbooks/trust-ci-activation-report.md`:

- Product base SHA: `48cb9737fac7f26fb70b425957a3ed64d4c1eb55`
- Disposable PR: **5** (draft)
- Disposable PR head SHA: `1fc942065a124ce75659bd082519d8ebc37774e8`
- Check Run id: `97390635614`
- Check Run `external_id` (job id): `1b63d10b-90c1-498a-97b8-7b5e0ea76aec`
- Required check name: `adaptive-trust-ci/verified@6737355947c2`
- Policy digest (full): `6737355947c21eb561073cb506ebc5698afd170088a34f8eaace50007c57d1a5`
- First Check Run: **loopback HMAC POST**, not a GitHub-registered webhook
- `main` protected: **false**
- Public webhook: **absent** (plan + report narrative)

From `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` M0.2:

- Webhook `POST https://<ci>/webhooks/github` — **not done** (no public HTTPS)
- Disposable docs PR / Check Run — **partial** on SHA `1fc9420…` / Check Run `97390635614` via **local HMAC**, `conclusion=action_required`. **Not M0.2 complete.**
- Combined checkbox: “SHA change invalidates old check; policy/holdout retitles epoch” — **one line, two proofs**
- Human Ed25519 requeue, source-mutation, public webhook remain open; kill-switch host-local drill already passed
- **Do not protect `main`** in M0.2
- M0.3 only after M0.2 is unambiguous

From `trust-ci/tests/test_m0_invariants.py` (`test_activation_report_operator_safe`):

- Check Run **id cell** (text after `Check Run id` through the next `|`) must **not** contain `UNKNOWN` — a numeric GitHub Check Run id is required.
- Plan must contain `local HMAC`.
- Plan must contain `no public HTTPS` **or** `not done`.

From `decisions.md` (2026-08-24 top):

- SHA-change invalidation waits for an **explicit push** of draft PR #5; “unify git” did **not** name `git-push-branch`.
- Policy/holdout retitle and human Ed25519 requeue remain **blocked by the trust boundary**.
- First App-owned Check Run via loopback HMAC; public webhook registration and `main` protection **out of scope**.
- GitHub webhook registration stays blocked until a public HTTPS URL exists.

From `README.md` on product **2.0.12**:

- “The App-owned check is not live in this release; merge of PR #2 is a bootstrap exception.”
- Local `grok_verify` / reviews / hooks / receipts are **not merge authority**.

## After a successful SHA-change proof — what must change

Tracked files that **must** be updated so facts match the new exact head SHA (still host-local HMAC unless a public webhook appears, which it must not be claimed):

1. **`engineering/runbooks/trust-ci-activation-report.md`**
   - **Current cells bind PR #5 head SHA `1fc9420…` and Check Run `97390635614`.** After SHA-change those cells must describe the **new** exact-SHA Check Run (numeric id, not `UNKNOWN`).
   - **Replace vs history:** Either is allowed by tests. The invariant only forbids `UNKNOWN` in the **Check Run id** table cell. Replacing the two cells (`Disposable PR head SHA`, `Check Run id`, and `external_id` if it is the new job id) is OK if the new id is a number. Keeping the old pair as **history** (prose or extra rows) plus current cells for the **new** SHA/check is also OK and better for proving invalidation. Do **not** leave only the old SHA as if it were still the live head.
   - Do **not** fill webhook/`main` protection as done. Empty M0.3 fields may stay `UNKNOWN`.

2. **`docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` — M0.2**
   - The line “SHA change invalidates old check; policy/holdout retitles epoch” is **two items**. After SHA-change proof **only** the SHA-invalidation half may be checked (or split into two checkboxes). **Policy/holdout epoch retitle stays blocked** (`decisions.md`); do not check that half.
   - Update the **partial** Check Run bullet to the **new** head SHA and Check Run id; keep **local HMAC** and **Not M0.2 complete**.
   - Keep webhook checkbox unchecked (`not done` / no public HTTPS) so `test_m0_invariants` stays green.
   - Do **not** check M0.2 complete, offline attestation, human requeue, or public webhook.

3. **`decisions.md`**
   - After a real SHA-change proof, add a short fact: old Check Run id vs new SHA/check, HMAC still local, webhook/`main`/policy-retitle still blocked. Do not treat SHA-change as M0.2 exit.

Optional if the spec repeats live IDs (characterization already pins base SHA `48cb9737…` and `adaptive-trust-ci/verified@`): update live-head IDs there only if the spec currently names `1fc9420` / `97390635614` as current; do not change the **product base SHA** or policy-epoch name unless policy actually retitled (it must not in this slice).

Change-package files under `engineering/changes/20260824-m0-2-sha-change-invalidation-on-draft-pr-5-beee95/` should record the new SHA/check as evidence **after** the proof; they are not the activation-report source of truth.

## What must stay (do not rewrite as complete)

| Path | Stay |
| --- | --- |
| `README.md` (2.0.12 on `main`) | Must **not** claim live merge authority. Keep “App-owned check is not live in this release” / bootstrap exception for PR #2. SHA-change on draft PR #5 does not make `main` merge-gated. |
| Plan M0.2 webhook line | Stay **not done**; no public HTTPS. **Do not claim public webhook done.** |
| Plan M0.2 overall | **Do not claim M0.2 complete.** Partial HMAC Check Run ≠ live authority. |
| Policy digest / required check name in the activation report | Stay `6737355947c2` / full digest unless an approved policy/holdout retitle happens (blocked). |
| App ID / Installation ID / images / holdout digest | Stay as filled; not SHA-change outputs. |
| `main` protected = false; protection `app_id` UNKNOWN | Stay until M0.3. |
| Leftover Actions workflow / bootstrap-exception superseded / backup-restore | Stay UNKNOWN or M0.3. |
| `trust-ci/tests/test_m0_invariants.py` | Keep: no `UNKNOWN` in Check Run id cell; `local HMAC`; webhook not-done language. |

## Ruling for implementer

- Activation report: **current** head SHA + Check Run id cells **must** become the post-synchronize identities. Old `1fc9420` / `97390635614` may remain as **history** (preferred for invalidation evidence) or be replaced; replacement is test-legal if the id cell is still a number.
- Plan: **split** the combined checkbox; check SHA-change only; leave policy/holdout retitle **unchecked**.
- Never mark public webhook done. Never mark M0.2 complete.
- Do not edit README 2.0.12 to claim live merge authority after this proof.
