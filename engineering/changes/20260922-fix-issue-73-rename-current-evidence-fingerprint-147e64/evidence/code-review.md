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
