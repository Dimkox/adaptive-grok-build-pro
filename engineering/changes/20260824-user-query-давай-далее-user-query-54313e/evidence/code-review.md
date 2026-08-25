# Code review — M0.3 bind-main docs/tests

Reviewer: `code_reviewer` (read-only). Route `54313e326a39`. Change `20260824-user-query-давай-далее-user-query-54313e`.

Inspected the **working-tree git diff** (not committed) plus surrounding `test_m0_invariants.py`, plan, activation report, `README.md`, `decisions.md`, `DARK_FACTORY_ROADMAP.md`. Did not treat leftover unrelated `engineering/changes/*/state.json` as this slice. Did not read `.env` or keys. Did not push, merge, or deploy.

## Scope of this slice

Product/docs that belong to M0.3:

- `trust-ci/tests/test_m0_invariants.py` — new `test_m0_3_main_is_app_bound`; M0.2 test still requires `**Do not protect \`main\`**` plus `M0.3 bind follows`.
- `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` — M0.3 boxes ticked except merge; live GET/POST IDs recorded.
- `engineering/runbooks/trust-ci-activation-report.md` — `main` protected true, `app_id` 4694114, workflow `disabled_manually`, bootstrap superseded; M0.2 residuals still **not done**.
- `decisions.md` — new 2026-08-24 revoke; 2026-08-23 / M0.2 history kept (including historical “Do not protect `main` until M0.3”).
- `README.md` L11 — live pair `adaptive-trust-ci/verified@6737355947c2` + App ID `4694114`; PR #2 exception revoked; PR #5 not mergeable while Check Run `action_required`.
- `DARK_FACTORY_ROADMAP.md` — four M0.3 protection boxes `[x]`, with honest note that no live push to `main` was issued.

Unrelated dirty `state.json` under other change packages is **out of this slice** and must not be committed with it.

## Contracts vs live facts

| Requirement | Tree |
| --- | --- |
| Epoch name + `app_id` 4694114 encoded together | README, decisions, plan, report, tests |
| Bootstrap exception superseded, not erased | New revoke entry; 2026-08-23 text remains |
| PR #5 merge box unchecked | Plan: `- [ ] Mark PR ready; merge…`; test `assertNotIn("- [x] Mark PR ready; merge")` |
| No secrets in this diff | IDs/digests only; PEM markers still scanned in existing tests |
| No GitHub Actions workflows | No `.github/workflows`; leftover `340420982` documented `disabled_manually` |
| M0.2 residuals not claimed done | Plan + report keep human Ed25519 / attestation / mutation / policy retitle **not done** |
| Historical “Do not protect `main`” | Still in M0.2 plan line and `test_m0_2_webhook_stage_closed_on_github_delivery` |

Live GitHub objects are **not** in git (correct). Docs/tests characterize: protection pair, `enforce_admins`, no force-push/delete, workflow disabled, user Checks 403, spoof status `52802341946`, Check Run `97529209576` `action_required`, PR #5 `mergeable_state=blocked`. Tests do not re-hit GitHub; they pin operator text. That matches a docs/characterization slice.

## Findings

1. **No product runtime change.** API/worker/compose/policy untouched. Risk is documentation drift vs live GitHub, not a code regression.
2. **Pair encoding is present** in current-state README and the new decision, and asserted in `test_m0_3_main_is_app_bound`.
3. **Roadmap “direct push / force-push / delete fail”** is explicitly qualified as protection flags + blocked PR, not a live `main` push. Acceptable honesty, not overclaim of M0.2 human/attestation/mutation work.
4. **Working tree noise:** other packages’ `state.json` plus many untracked change dirs. Implementer must not fold those into the M0.3 commit.
5. **Characterization gap (non-blocking):** tests do not string-assert `52802341946`, `97529209576`, or `mergeable_state=blocked`; those live only in the plan paragraph. Sufficient if the plan stays the operator record; test_reviewer may still want those pins.

No secrets, no Actions YAML, no merge of PR #5, no claim that M0.2 human Ed25519 / offline attestation / source-mutation are complete.

## Verdict

**PASS**
