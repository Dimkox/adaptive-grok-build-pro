# Tasks — fix(verify): reject same-inode CAS tampering by content digest, not by filesystem ctime granularity

- [x] Reproduce: read the retained Trust CI job record for PR #64 head `23dd5c58` and capture the exact failing frame into `evidence/ci-failure-traceback.md`.
- [x] Root-cause: confirm the rejected scenario is carried by the expected-digest comparison and that `_post_exchange_identity_matches` already treats ctime as `>=`, so the strict ctime precondition was never a product guarantee.
- [x] Replace the filesystem-dependent precondition with the restored-field equalities plus a content-difference assertion.
- [x] Add the deterministic companion test that pins the rejection to code `cas` while every non-content identity field is equal.
- [x] Record the durable rules in `mistakes.md` (timestamp-granularity preconditions; read retained external command output before re-running suites).
- [x] Run the targeted modules and `ruff`; then `grok_verify --mode pr` on the frozen tree.
- [x] Independent code review and test review (both PASS, zero findings) — see `evidence/review-code.md`, `evidence/review-test.md`.
- [ ] Deliver the branch through a pull request and merge only after the App-owned exact-head check succeeds.
