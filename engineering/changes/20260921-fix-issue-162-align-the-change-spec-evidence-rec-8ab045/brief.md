# Issue #162 — all route review kinds can be cited

Typed authority: [change-spec.yaml](change-spec.yaml).

The user authorized parallel issue fixes on 2026-09-21. Route 8ab045fd89e1 has no named human gate. Four independent analyses agree that the runtime vocabulary has seven kinds while the spec enum has five.

## Bounded decision

Add bitrix_review and data_review to the existing closed schema enum. Add exact runtime/schema parity, validation of all seven known values, and rejection of an unknown value. No receipt issuance, binding, route review requirement, draft creation behavior or external merge authority changes.

## Branch and delivery

This isolated branch is based on frozen PR #170 head 1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48, retaining its #164 test-clock correction. Its issue-specific delta is independent of the other issue branches. A separate PR should target the #170 branch until that dependency lands; external publication and merge require applicable explicit delegation and exact grants.

## Ownership and next action

The route-selected general_implementer is the sole application/test writer. Next: regression first, minimal schema repair, focused tests, coordinator full verification, then code_reviewer and test_reviewer. Analysis reports are under evidence/.

## Review follow-up — shipped validator parity

Independent code review reproduced two additional five-kind consumers in checked-in Trust CI runner.py and holdout.example/change_spec_validate.py. Architecture follow-up confirms these sets validate metadata vocabulary and do not issue receipts or approvals. The authorized issue fix therefore also aligns these source-only closed sets and their regression tests with the existing seven runtime names; independent validators retain their own lists, guarded by parity tests rather than importing candidate code into the trusted validator.

Allowed additions: trust-ci/src/adaptive_trust_ci/runner.py, trust-ci/holdout.example/change_spec_validate.py, trust-ci/tests/test_spec_metadata.py, trust-ci/tests/test_change_spec_holdout.py (or the existing directly corresponding validation test files). Preserve unknown-kind rejection and all metadata bounds, statuses, signatures, approval scopes and policy enforcement. No deployed worker/holdout/policy/store/key or service is changed. External rollout remains separately reviewed and authorized; local source verification cannot claim deployed acceptance.
