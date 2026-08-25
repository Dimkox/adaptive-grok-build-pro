# test_reviewer — M0.2 SHA-change invalidation (POST-implementation)

Route: `beee95e0b3c6`. Change: `20260824-m0-2-sha-change-invalidation-on-draft-pr-5-beee95`. Read-only. No secrets.

**Verdict: pass**

Commit `ce03c87` did not change `trust-ci/tests/test_m0_invariants.py`. Product docs remain bound to SHA `1fc942065a124ce75659bd082519d8ebc37774e8` and Check Run id `97390635614`. That is the intended freeze: a later live SHA must not rewrite activation-report invariants or the test would fight the infinite-SHA ruling.

## Unit characterization vs committed docs

Re-ran `python3 -m unittest trust-ci.tests.test_m0_invariants` → **8 tests OK**.

| Constraint | Current docs | Test |
| --- | --- | --- |
| Check Run id cell not `UNKNOWN` | report: `97390635614` | `test_activation_report_operator_safe` |
| Disposable head still `1fc9420` | report + plan partial M0.2 line | not asserted as equality; cell is numeric, not `UNKNOWN` |
| `adaptive-trust-ci/verified@` + base `48cb9737…` | spec | `test_m0_spec_and_plan_exist` |
| `local HMAC` and `not done` / no public HTTPS | plan | `test_activation_report_operator_safe` |
| `claw`, no `laptop` in spec | spec+plan | `test_m0_docs_name_claw_not_laptop` |
| No PEM markers | spec, plan, report | same |

Committed docs still match those assertions. Live SHA `ce03c87` is **not** written into the activation report (correct).

## Live SHA-change coverage (not a new unit test)

Hermetic tests cannot mint GitHub App Check Runs. Characterization of the real SHA move is `evidence/sha-invalidation.md` (uncommitted on purpose):

- Old SHA `1fc9420` keeps Check Run `97390635614` / `external_id` `1b63d10b-…`
- New SHA `ce03c87` has Check Run `97406973020` / `external_id` = job `54e2c6f4-…`
- Loopback HMAC `pull_request`/`synchronize` HTTP 200, `created: true`
- `action_required` expected (no forged approval)

That is adequate for this slice. Do not add a FakeGitHub test that pretends to be Check Run `97390635614`.

## Residual gaps (accepted, not fail)

- Postgres store still has **no** `test_new_head_cancels_old_active_job` analog (pre-impl note). MemoryStore covers cancel-on-new-SHA. Live proof is HMAC + distinct Check Run ids, not SQL.
- Public HTTPS webhook remains **not done** (plan + invariant).
- Policy-epoch pass + Ed25519 scopes are later slices.

## Adequacy

Store cancel + `external_id` reuse tests unchanged and still the right hermetic layer. M0 invariants still describe the **first** published Check Run. Live two-SHA evidence is the missing piece those tests never claimed to replace. No product test file needed for `ce03c87`.
