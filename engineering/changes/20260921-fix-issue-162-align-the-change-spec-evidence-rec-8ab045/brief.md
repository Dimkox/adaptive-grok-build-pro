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

Independent code review reproduced two additional five-kind consumers in checked-in Trust CI runner.py and holdout.example/change_spec_validate.py. An attempted source follow-up passed focused tests but failed architecture fitness: `FIT-TRUST-CI-SEPARATION` forbids mixing `schemas/**` implementation changes with `trust-ci/**` changes in one diff. Commit `4c683f7864a3bdfda1782b7e265fa9ea07b136a6` preserves that historical attempt; its four Trust CI source/test paths are inverted in this branch's working tree so the final #162 delta remains schema-only.

A separately routed Trust CI successor must start from an actual base containing the delivered schema-only fix and its inherited PR #170 changes, then change only the two checked-in validator allowlists and their tests. Against main `90078959` or PR #170 alone, the schema fix remains in the changed-path set and the separation rule still fails. The source patch is preserved at `/home/pall/.cache/agbp-run/issues-wave-20260921/issue162/trust-ci-successor.patch`. No deployed worker/holdout/policy/store/key or service is changed here; external rollout remains separately reviewed and authorized. Until that successor and deployment occur, new domain-review spec references may still fail Trust CI metadata or holdout validation.
