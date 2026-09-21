# Test plan

Add meaningful regression tests in tests/test_change_spec.py, prove missing kinds fail before repair, then rerun after the additive enum repair. Run adjacent workflow-artifact parity tests. The coordinator runs GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr after the final tree is frozen, and dispatches independent code and test reviews. Preserve raw command results under evidence or external run cache; never infer a pass from a plan.

Review follow-up: add RED/GREEN accepted/rejected vocabulary tests through both actual shipped Trust CI validators and parity checks against the schema/runtime vocabulary. Run relevant Trust CI metadata/holdout tests before renewed full PR verification and both independent reviews.
