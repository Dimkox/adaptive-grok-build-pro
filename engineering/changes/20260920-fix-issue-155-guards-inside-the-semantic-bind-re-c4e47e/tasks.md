# Tasks — issue #155 repair-child rejection diagnostics

One application-code owner: route-selected `frontend_implementer` on
`fix/issue-155-repair-binding-rejections`. Independent reviewers inspect product
files read-only and own only their respective evidence reports.

- [x] Freeze contracts and the exact guard enumeration. Nine former NULL paths map
  to twelve allowlisted reasons; the acceptance predicates, locks, function
  signature, roles and migration resources 001–020 remain unchanged.
- [x] Reproduce the original diagnosis and fix the smallest vertical path. Add
  resource 021, the strict rejection reader and classification before binding
  parsing. Keep malformed payloads diagnostically distinct.
- [x] Remove the two affected fixtures' import-time clock coupling. Sample request
  or server time; preserve expired-proof and excessive-budget rejection controls.
  The mandatory tier blocker #164 is included under the recorded bounded ruling.
- [x] Recover the prior full-verifier failure. Preserve its limitations and the
  unowned-scratch negative control; the unexplained historical unit-test exit is
  not relabelled as a proven cause. See the archived root-suite diagnosis.
- [x] Resolve independent-review defects with evidence. A red/green cause/context/
  traceback regression now distinguishes legacy NULL, a named refusal and malformed
  data; the recovery procedure retains applied 021 and requires an additive fix.
- [x] Verify the corrected product. Full `grok_verify --mode pr` passed on d659558:
  785 root tests, 80% coverage, selected factory/pilot checks and the PostgreSQL tier.
  Earlier targeted-check failures remain historical in `evidence/postgres-evidence.md`.
- [x] Complete AC-005 on the corrected bytes. Four consecutive mandatory PostgreSQL
  passes, each 779 tests with two conditional skips and actual restart/reconciliation,
  share product digest `7bc1176912c7468329d825a1b5f1ef74b0025cc862505f04003050bca1aeac25`.
  Exact durations, host load and raw log hashes are in `evidence/final-20260921/`.
- [x] Complete independent code, test, security and data reviews. Current PASS
  verdicts and the resolved original findings are in `evidence/continuation-*-review.md`.
- [x] Prepare the immutable local handoff and receipt procedure. The final source
  commit includes this package, review reports and the PR description. Fresh full
  verification and four current review receipts must bind that clean commit before
  publication; machine-local `grok_status` is the current-state check, not this checkbox.
- [x] Preserve bounded follow-ups. #162/#163/#165/#166 remain separate. The next
  external pilot has a current-target investigation, reproduced gap and unposted
  two-file issue draft in `next-pilot/`; no target or provider effect occurred.

External delivery remains pending: obtain the named branch-push/PR delegation,
materialize an exact current grant, publish the branch/PR and await exact-head
App-owned Trust CI. This task list does not grant merge or deployment authority.
