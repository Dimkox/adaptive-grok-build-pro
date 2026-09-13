# Post-landing hardening of the L5 union

Three follow-ups created by landing the L5 stack into main `eb9df64` (2026-09-13):

1. **Issue #60** — `tests/test_architecture_model.py` pinned `len(records) == 41`; every future contract PR collides. Replaced with derived set-equality against `architecture/system.yaml` contracts plus a seed floor `>= 41`.
2. **Issue #61** — prohibited deploy members existed only in test scope. `factory/src/adaptive_factory/landing_artifact.py` now exports `PROHIBITED_DEPLOY_MEMBERS`, self-checks `DEPLOY_MEMBERS` at import, and every `deploy_members_for_source()` epoch resolution passes through `_approved_deploy_members`, failing closed with the offending member named. No sealed bytes change for valid epochs.
3. **Issue #63 residual** — the digest-pinned `resources/landing_pdf_worker.py` never executed in tests (media tests spawn a `python -c` stub). New `factory/tests/test_landing_pdf_worker.py` drives the real child through `extract_pdf_text` on both interpreter classes (with/without pinned pypdf).

`PROJECT_STATE.json` `l5_production_preparation` is switched to the landed state.
