# Test review — issue #73

## Review identity

- Candidate HEAD: `8504fd34553eae89b7f3f5dfb65bb30fd663abbe`
- Base: `origin/main` / `130ce4a42d9f9bbd1b56772d40b19ae530283205`
- Candidate tree fingerprint before/after: `5055e57ab5d01bbec79a057087e442e5cc231f7c23b705446fd24501ece0fa07`
- Scratch: `/tmp/agbp-issue73-review-y9fKzu/repo`
- `reviewed-tree-modified: no`

## Result

The focused tests adequately cover new writes, legacy reads, ambiguous grants, the landing
publisher consumer, and immutable historical evidence.

| Claim | Exact probe | Observed result | Mutant outcome |
| --- | --- | --- | --- |
| Exact candidate and tree are stable | `git rev-parse HEAD; git rev-parse HEAD^{tree}; tree_fingerprint(.)` before/after | HEAD `8504fd34…`; Git tree `25b2c822…`; fingerprint `5055e57a…` unchanged | killed/inconclusive |
| Focused suite passes | `PYTHONPATH=.grok-stack python3 -m unittest tests.test_policy tests.test_history factory.tests.test_landing_publication_cli` | `Ran 76 tests ... OK` | killed |
| New field is emitted | `tests.test_policy.PolicyTests.test_new_grant_uses_neutral_binding_digest_key` | passed | killed producer-revert mutant |
| Legacy field remains valid | `tests.test_policy.PolicyTests.test_legacy_tree_fingerprint_grant_remains_valid` | passed | killed fallback-removal mutant |
| Policy dual-field rejection | `tests.test_policy.PolicyTests.test_conflicting_grant_binding_fields_fail_closed` | passed | killed permissive-reader mutant |
| Publisher accepts either valid field and rejects both | `LandingPublicationBoundaryTests.test_synthetic_stale_foreign_and_duplicate_grants_cannot_advance_intent` | passed, including both fields equal to current digest | killed |
| Publisher dual-field guard is mutation-tested | Remove the publisher dual-field rejection in scratch and run the specific publisher test | `AssertionError: PublicationError not raised` | killed |
| Historical bytes remain identical | `sha256sum` on both September 13 historical probe files | both SHA-256 values `f69eedc41e41be3920e36dd243d719de861b64a96a674983bd256f978e329e9b` | killed |
| Full route verification | `python3 scripts/grok_verify.py --mode pr` | exit 0; route-selected checks passed | killed/inconclusive: receipt recorded separately |

An earlier review found the publisher dual-valid-fields mutant survived; the existing write owner
added the direct regression before this final review. No external writes were performed.

## Exact candidate rebind — 2026-09-24

- Independent re-review snapshot: HEAD `08b2a2881e8480f6bc8eeca0d8ea4570a619e81c`, tree `5ee5534d84ac8a78de4ca4e13e5043dc3f6f1d19`, working-tree fingerprint `8ead1eeef9855c06169f15fff2a3300e43c9142154c419f300373d1ed19c7e9d`, target `6cc360e48e608ef22fc6a68feff16ec9d78712b0`.
- The reviewer ran the bounded compatibility/security suite and observed all targeted checks passing; the only failure was that the route-base refresh was not yet committed.
- The coordinator committed that refresh as HEAD `13011c0610449c6f7a5b31917f67e87409589fb5`, tree `1f20160ffc1aef3541134380674985ea3bedfdc7`, working-tree fingerprint `bc54089ca2f0c7acca6ade20615bf3b68cf673178638af41ddd67b234115a65a`.
- Final verification and the machine receipt must be recorded after this report update; exact-head Trust CI remains a separate gate.
- Verdict for the bounded test scope: **PASS**, pending final local receipt and exact-head Trust CI.
