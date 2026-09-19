# Test plan

- [x] Unit-test deterministic scope digest generation and invalidation when approved scope or route/change binding changes.
- [x] Test the decision CLI accepts only declared gates and explicit approve/reject values; malformed, missing, rejected, stale, and mismatched records fail closed.
- [x] Test workflow transitions block `approved` when `scope_and_design_approval` is absent or unsatisfied.
- [x] Test delegated production/external-write grant creation blocks on each matching pending gate.
- [x] Test `has_valid_approval()` and production/external-write consumers re-check the gate as well as the existing exact grant.
- [x] Test exact targets remain scoped and unrelated grant/action checks are not broadened.
- [x] Test removal of a declared gate from the active route with the same route_id blocks both protected action authorization and the approved transition.
- [x] Test removal of a declared migration/external-write gate with the same route_id blocks an exact-target external write even when its local grant and gate decision exist.
- [x] Test `grok_status.py` reports each declared gate and its evidence path; legacy packages without decision artifacts show pending.
- [x] Test explicitly that local gate records never satisfy or modify Trust CI approval scopes, attestations, or exact-SHA check behavior (an inert local `trust-ci.json` plus unrelated grant cannot satisfy a declared local gate; no Trust CI code or records are touched).

Run focused unit suites first, then `python3 scripts/grok_verify.py --mode pr`, then route-selected code, test, security, and release reviews. No production operation or external write is part of verification.
