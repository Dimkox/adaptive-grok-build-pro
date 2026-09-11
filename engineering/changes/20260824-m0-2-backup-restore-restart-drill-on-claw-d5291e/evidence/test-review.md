# Test review (post-implementation)

Change: `20260824-m0-2-backup-restore-restart-drill-on-claw-d5291e`  
Commit inspected: `92ddbd9` (`ops: record M0.2 backup restore restart drill on claw`)  
Agent: `test_reviewer` (read-only)  
Route: `249c12b20197`

## Verdict: **pass**

Characterization and existing unittests still match committed docs. Live claw drill is recorded in `evidence/drill-report.md` rather than a new integration test; that split is acceptable. Residual: the new backup-cell block is tautological (does not fail if the cell reverts to `UNKNOWN`).

---

## Unittest re-run

From `trust-ci/` with `PYTHONPATH=src:tests`:

```text
python3 -m unittest tests.test_m0_invariants tests.test_backup tests.test_ops
Ran 28 tests in 0.093s
OK
```

(Loader from repo root without `PYTHONPATH` cannot import `_support`; that is pre-existing, not this slice.)

---

## `test_m0_invariants` vs committed docs

| Invariant | Evidence | Status |
| --- | --- | --- |
| Check Run id cell not `UNKNOWN` | Report row `Check Run id \| 97390635614`; `assertNotIn("UNKNOWN", …split("Check Run id"…)`) | holds |
| No PEM markers | `PEM_MARKERS` on spec, plan, report | holds |
| Plan still `local HMAC` | plan line 33 | holds |
| Webhook not done | plan: `not done` / `no public HTTPS` | holds |
| Do not assert `main` unprotected | no assertion on `main protected \| false` | holds |
| Backup cell dated pass (characterization) | report: `2026-08-24 pass (…backup-create…backup-verify…--confirm-disposable…compose restart postgres…)` | cell filled; **assert is tautological** |

Added in `92ddbd9`:

```python
backup_cell = report.split("Backup/restore/restart drill", 1)[1].split("|", 2)[1]
if "2026-" in backup_cell and "pass" in backup_cell:
    self.assertIn("2026-", backup_cell)
    self.assertIn("pass", backup_cell)
```

If the row is `UNKNOWN` again, the `if` skips and the test still passes. Pre-implementation analysis asked for an **unconditional** date+`pass` once the report is filled. Residual only; not enough to fail this slice because:

1. The row **is** currently dated `2026-08-24 pass` with operator-safe tokens.
2. The test still fails if PEM/HMAC/Check Run/webhook invariants regress.
3. Strengthening the assert is a one-line follow-up, not a coverage hole for library backup.

No assertion on DSN, restore URL values, dump bytes, PEM, JWT, webhook secret, or `main protected | false`.

---

## Adequacy vs test plan

| Priority | Scenario | Result |
| --- | --- | --- |
| P0 | `test_backup.py` still green | 28 tests OK including backup + ops |
| P0 | m0 invariants (PEM, Check Run, HMAC, webhook) | green |
| P0 | Report cell dated pass | documented; unittest weak (tautology) |
| P0 | Live dump/verify/restore/restart | `evidence/drill-report.md` |
| P0 | Live volume not restore target | drill-report: throwaway tmpfs, mounts exclude live named volume |

Library coverage (`create_backup` / `verify_backup` / `restore_drill` fail-closed, systemd/script strings) is unchanged and still green. Live path is operator evidence, not compose.test.

---

## Residual (non-blocking)

- Unconditional `self.assertIn("2026-", backup_cell)` / `self.assertIn("pass", backup_cell)` without the `if` would pin the activation-report contract.
- Optional: assert operator-safe tokens already in the cell (`backup-create`, `backup-verify`, `--confirm-disposable`) without requiring dump SHA of live data.

Do not treat this pass as M0.2 complete (webhook / public HTTPS still open in the plan).
