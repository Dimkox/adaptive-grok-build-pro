# Code review — issue #73

## Review identity

- Candidate HEAD: `8504fd34553eae89b7f3f5dfb65bb30fd663abbe`
- Base: `origin/main` / `130ce4a42d9f9bbd1b56772d40b19ae530283205`
- Candidate tree fingerprint before/after: `5055e57ab5d01bbec79a057087e442e5cc231f7c23b705446fd24501ece0fa07`
- Git tree before/after: `25b2c8222d986b157b2cd4f7f6941b7d82cbed27`
- Scratch: `/tmp/agbp-review-issue73.wgiufb/repo`
- `reviewed-tree-modified: no`

## Result

No correctness, compatibility, immutability, or scope defects were found within the bounded
issue #73 change.

| Claim | Exact probe | Observed result | Mutant outcome |
| --- | --- | --- | --- |
| Exact candidate reproduced | `git clone --no-hardlinks --local /tmp/agbp-issue73-evidence-digest ...; git checkout --detach 8504fd34...` | Scratch HEAD/tree matched the candidate | killed |
| New producer emits the neutral field | `python3 -m unittest tests.test_policy` | 24 policy tests passed; producer emits `grant_binding_digest` and omits `tree_fingerprint` | killed |
| Legacy reader remains compatible | `python3 -m unittest tests.test_policy` | Legacy grant test passed | killed |
| Policy reader rejects both fields | Remove the dual-field branch in a scratch mutant, then run `python3 -m unittest tests.test_policy` | Conflicting-field test failed | killed |
| Landing publisher rejects both fields | Remove its dual-field branch in a scratch mutant, then run `python3 -m unittest factory.tests.test_landing_publication_cli` | The synthetic malformed dual-field test failed | killed |
| Historical evidence is immutable | `git diff --exit-code BASE HEAD -- <two historical evidence JSON files>` | unchanged | killed |
| Focused compatibility remains green | `python3 -m unittest tests.test_policy tests.test_history factory.tests.test_landing_publication_cli` | 76 tests passed | killed |
| Candidate stayed unchanged | `git status --porcelain`, HEAD/tree/fingerprint before and after | clean and identical | killed |

The implementation keeps repository, route, change, Git HEAD, scope, action, resource, expiry, and
tree-binding checks intact. Product changes are limited to the grant producer, landing publisher,
related tests, and package evidence. External Trust CI and GitGuardian were not evaluated here.

## Exact candidate rebind — 2026-09-24

- Independent re-review snapshot: HEAD `08b2a2881e8480f6bc8eeca0d8ea4570a619e81c`, tree `5ee5534d84ac8a78de4ca4e13e5043dc3f6f1d19`, working-tree fingerprint `8ead1eeef9855c06169f15fff2a3300e43c9142154c419f300373d1ed19c7e9d`, target `6cc360e48e608ef22fc6a68feff16ec9d78712b0`.
- The reviewer found no correctness or security defect, confirmed the 76 focused tests and historical-evidence immutability, and noted only the uncommitted route/evidence refresh.
- The coordinator committed that refresh as HEAD `13011c0610449c6f7a5b31917f67e87409589fb5`, tree `1f20160ffc1aef3541134380674985ea3bedfdc7`, working-tree fingerprint `bc54089ca2f0c7acca6ade20615bf3b68cf673178638af41ddd67b234115a65a`, with route base `6cc360e48e608ef22fc6a68feff16ec9d78712b0`.
- The final verifier and machine receipt must bind the post-report-persistence tree; exact-head Trust CI remains required.
- Verdict for the bounded code scope: **PASS**, pending final local receipt and exact-head Trust CI.

## Restack after issue-186 merge — 2026-09-24

- Protected main advanced to PR #191 merge `9312702d03f25e2256d1f3aa456bc41907c0c436`; the route now compares against that exact base.
- The new base contains the separate #186/#36 disposition package. `git diff origin/main...HEAD` remains the bounded 27-path #73 change, with no new product or Trust CI implementation path.
- The restacked candidate is HEAD `d1378a54b9e2beda0159f0dfa6647af1c0738cb8`, tree `856c6352a34daf30bd0b11dcbcbdb5846d2bc38d`, working-tree fingerprint `509b54886a0f36d6831270a0684d68f9bbb629a4905cdc2d059fd6d870707299`.
- This restack changes the exact base identity only; final verification, review receipts, and Trust CI must bind the restacked head.
