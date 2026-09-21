# Test plan

Add meaningful regression tests in tests/test_change_spec.py, prove missing kinds fail before repair, then rerun after the additive enum repair. Run adjacent workflow-artifact parity tests. The coordinator runs GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr after the final tree is frozen, and dispatches independent code and test reviews. Preserve raw command results under evidence or external run cache; never infer a pass from a plan.
