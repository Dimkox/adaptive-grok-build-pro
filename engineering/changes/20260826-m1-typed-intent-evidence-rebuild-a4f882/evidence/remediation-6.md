# Remediation 6 — blocked M1 review wave 6

The `review-code_reviewer-6.md` and `review-test_reviewer-6.md` BLOCKED reports and the `review-security_reviewer-6.md` PASS report in this directory are preserved verbatim as historical evidence for reviewed HEAD `9a6e27c193ec944a149e452ff7591fbc7493238c`. No passing receipt was created.

## Source repair

- `GitWorkspace` now treats checkout and trusted-config allocation as one constructor transaction. Both path references begin empty, every allocation and permission/XDG operation is guarded, and object attributes are published only after the complete workspace is ready.
- Constructor failure performs best-effort removal of every path that was actually allocated and then re-raises the original exception. Normal cleanup remains idempotent.
- Deterministic fault-injection regressions cover checkout `chmod`, the second `mkdtemp`, config-home `chmod`, and XDG `mkdir`; they require the original exception identity and an empty workspace base afterward. The successful lifecycle regression calls cleanup twice.

## Status

- Focused workspace suite: 15 tests executed successfully.
- Pinned Trust CI suite: 200 total, 10 honest conditional PostgreSQL skips, and 190 executed successfully because `TRUST_CI_TEST_DATABASE_URL` was not configured.
- Root suite: 223 tests executed successfully.

Exact-commit verification and fresh independent route-selected review remain required. This repository evidence does not mark the holdout, worker, policy, or service as deployed and does not replace the App-owned exact-SHA Trust CI check or external signed approvals.
