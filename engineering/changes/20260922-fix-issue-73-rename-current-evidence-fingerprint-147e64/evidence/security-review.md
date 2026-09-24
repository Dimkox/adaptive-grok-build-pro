# Security review — issue #73

## Review identity

- Candidate HEAD: `8504fd34553eae89b7f3f5dfb65bb30fd663abbe`
- Base: `origin/main` / `130ce4a42d9f9bbd1b56772d40b19ae530283205`
- Candidate tree fingerprint before/after: `5055e57ab5d01bbec79a057087e442e5cc231f7c23b705446fd24501ece0fa07`
- Git tree: `25b2c8222d986b157b2cd4f7f6941b7d82cbed27`
- Scratch: `/tmp/issue73-review.LrLg3P/repo`
- `reviewed-tree-modified: no`

## Result

No security defect was found within the bounded scope. The implementation remains fail-closed for
ambiguous, malformed, stale, foreign, or mismatched grants.

| Claim | Exact probe | Observed result | Mutant outcome |
| --- | --- | --- | --- |
| Candidate is exact and clean | `git rev-parse HEAD; git status --porcelain; git rev-parse HEAD^{tree}` | HEAD matched; status empty; tree stable | killed |
| Focused authorization behavior passes | `python3 -m unittest tests.test_policy tests.test_history factory.tests.test_landing_publication_cli` | `Ran 76 tests ... OK` | killed |
| New grants use `grant_binding_digest` | `PolicyTests.test_new_grant_uses_neutral_binding_digest_key` | new field present; legacy and historical detector-shaped fields absent | killed |
| Legacy grants remain readable | `PolicyTests.test_legacy_tree_fingerprint_grant_remains_valid` | passed | killed |
| Dual fields fail closed | policy conflicting-field test plus publisher dual-valid test | both rejected | killed |
| Repository/route/change/HEAD/tree binding is exact | policy tree/commit tests and publisher stale/foreign/wrong-identity cases | rejected when any binding differs | killed |
| Action/resource/expiry/source checks remain exact | full focused policy/publication suite | passed | killed |
| Historical evidence is byte-identical | `sha256sum` on both historical files | both `f69eedc41e41be3920e36dd243d719de861b64a96a674983bd256f978e329e9b` | killed |
| No trust/key paths changed | `git diff --name-only BASE..HEAD | rg -i '(^|/)(trust-ci|governance|.*key|.*pem|.*approval|\.github/workflows)'` | no output | killed for candidate diff scope |
| Diff is whitespace-clean | `git diff --check BASE..HEAD` | no output | killed |

The change does not touch historical evidence, trust stores, approval keys, deployed Trust CI
policy, GitHub Actions, production systems, or external writes. GitGuardian detector/allow-list
behavior and App-owned Trust CI remain external limitations and are not claimed as fixed here.

## Exact candidate rebind — 2026-09-24

- Independent re-review snapshot: HEAD `08b2a2881e8480f6bc8eeca0d8ea4570a619e81c`, tree `5ee5534d84ac8a78de4ca4e13e5043dc3f6f1d19`, working-tree fingerprint `8ead1eeef9855c06169f15fff2a3300e43c9142154c419f300373d1ed19c7e9d`, target `6cc360e48e608ef22fc6a68feff16ec9d78712b0`.
- The security reviewer found no correctness or security findings, validated the neutral binding field, legacy compatibility, dual-field fail-closed behavior, historical immutability, and focused tests.
- The coordinator committed the route/evidence refresh as HEAD `13011c0610449c6f7a5b31917f67e87409589fb5`, tree `1f20160ffc1aef3541134380674985ea3bedfdc7`, working-tree fingerprint `bc54089ca2f0c7acca6ade20615bf3b68cf673178638af41ddd67b234115a65a`.
- Final verification and the machine receipt must bind the post-report-persistence tree; exact-head Trust CI remains required.
- Verdict for the bounded security scope: **PASS**, pending final local receipt and exact-head Trust CI.
