# Code review — `20260824-m0-consolidate-git-and-continue-live-authority-p-85a17e`

Reviewer: `code_reviewer` (read-only). Route `85a17ed2e935`.  
Commit: `ca1e88aad3dafcfeb81583f443f67c49c1faeab6` vs parent `1fc942065a124ce75659bd082519d8ebc37774e8` on `milestone/m0-live-trust-authority`.  
No push, merge, deploy, or `.env`/PEM reads.

## Verdict

**PASS** — slice matches the stated scope: unify live M0 facts in git, record host-local kill-switch + attestation GET 404, no push, tracked compose unchanged. Residual notes below are non-blocking.

## Inspected

- `git diff --name-only` / `--stat` / full patch for `ca1e88aa` vs `1fc94206` (38 files, +2256/−23).
- Surrounding tree: `trust-ci/tests/test_m0_invariants.py`, plan/spec under `docs/superpowers/`, `engineering/runbooks/trust-ci-activation-report.md`, `decisions.md` (top), this package `evidence/implementation.md`, overlay copy `engineering/changes/20260824-the-user-sent-a-message-while-you-were-working-u-3e6166/evidence/compose.host-socket.yaml` and that package’s `implementation.md`.
- Confirmed `trust-ci/compose.yaml` is **absent** from the changed-file list.

## Scope checks

| Check | Result |
| --- | --- |
| Tracked `trust-ci/compose.yaml` not edited | **Pass** — not in the commit. Overlay lives only as evidence YAML. |
| No PEM/JWT/webhook secret/private keys in the diff | **Pass** — no `BEGIN * PRIVATE KEY` blocks, no JWT/PEM bodies. Overlay lists **bind paths** (`./runtime/github-app-private-key.pem`, signing key path), not key material. App/installation numeric IDs and Check Run/job UUIDs are operator-safe. |
| Overlay is documentation only | **Pass** — header: “claw-only. Never merge into tracked compose this slice.” Residual risk in 3e6166 `implementation.md` states host-socket is host-root equivalent vs DinD. Product default compose is untouched. |
| Plan does not claim M0.2 complete or public webhook | **Pass** — webhook box unchecked “**not done** (no public HTTPS)”; Check Run box “**partial** … via **local HMAC** … Not M0.2 complete.” M0.3 still gated on unambiguous M0.2. |
| Spec live-gap is freeze snapshot | **Pass** — titled “freeze snapshot probed 2026-08-24”; “not the current claw state”; freeze table retained; live facts pointed at the activation report. |
| Characterization test not dangerously flaky/overfit | **Pass with notes** — asserts report exists, PEM markers absent, Check Run id cell not `UNKNOWN`, plan contains `local HMAC` and (`no public HTTPS` or `not done`). Does not assert live HTTP, docker.sock, or Check Run conclusion. |
| Four planes / host-socket not product default | **Pass**. |
| No GitHub Actions, branch-protect, forged check | **Pass** — no `.github/workflows/**`; plan/report keep `main` unprotected; Check Run recorded as `action_required`/`needs_approval`, not forged success. Commit does not push. |

## Findings

1. **Low — markdown cell parse in `test_activation_report_operator_safe`.**  
   `report.split("Check Run id", 1)[1].split("|", 2)[1]` depends on table punctuation. A heading/typo could fail the test or, less likely, skip the intended cell. Not a security hole; consider a tighter row regex later.

2. **Low — PEM marker set is incomplete.**  
   Markers are `BEGIN RSA PRIVATE KEY` and `BEGIN OPENSSH PRIVATE KEY` only. PKCS#8 `BEGIN PRIVATE KEY` / `BEGIN EC PRIVATE KEY` would not trip the new loop. No such material is in this diff.

3. **Info — historical contradiction in `decisions.md`.**  
   Newer entries say the worker runs via overlay; the earlier “M0.1-complete … worker never reached running” paragraph is still true as history but can be misread as present tense. Spec annotation is clearer than this stack of dated notes.

4. **Info — 3e6166 package landed in the same commit.**  
   Large analysis/route paperwork plus overlay copy. In-scope as “unify git”; does not change product compose or CI policy.

## Product / trust-boundary

- No compose-up, webhook registration, `branch-protect`, or SHA-change in this tree slice.
- Attestation documented as N/A (job `needs_approval`; GET 404) — consistent with incomplete M0.2.
- Kill-switch described as host-local STOP drill; rollback in implementation.md says do not leave STOP in place.

## Recommendation

Accept this documentation/test characterization slice. Do not merge overlay into tracked compose. Do not treat local HMAC Check Run as M0.2 complete.
