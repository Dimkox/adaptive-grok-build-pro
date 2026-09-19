# Test plan — durable delivery of the #104 post-merge audit

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | The shared append-only document is only extended: `git diff --numstat -- mistakes.md` shows additions with **0 deletions**, and the 6 recovered headings still appear exactly once each | AC-004, `SIG-001` |
| P0 | No machine-local absolute path or host name survives in committed evidence | AC-005: search this package's files for a leading home-directory or temporary-directory absolute path and for this host's user name; the check must return nothing (this row deliberately avoids quoting those literals) |
| P0 | The typed spec passes the repository validator in gate mode | `python3 scripts/grok_spec.py validate --gate` → `ok: true`, `errors: []` |
| P1 | Every numeric claim in the evidence is reproducible at the named SHA | re-run of the commands quoted in `controller-declared-inventory-table.md` in a throwaway clone of `d871ea6` |
| P1 | Nothing outside this package and `mistakes.md` changed | `git diff --name-only origin/main...HEAD` |
| P2 | Evidence files hold no `.py` that could trip the evidence-node network rule | `find engineering/changes/<pkg> -name '*.py'` → empty |

## Automated checks

- Unit: none added (documentation-only wave); the full root suite still runs through the gate.
- Integration: `GROK_VERIFY_CAPABILITY=repository-sandbox UV_LOCKED=1 python3 scripts/grok_verify.py --mode pr`.
- Contract: `grok_architecture.py fitness` must report no new finding, since no contract or model file changes.
- E2E: not applicable.
- Static analysis: ruff/bandit/diff-check as executed by the gate; plus the greps above.

## Manual checks

- Read the recovered six entries against the primary working tree's file to confirm they were copied verbatim.
- Confirm the chronological placement and that no existing entry's text was reflowed.
- Confirm each residual (R1–R4) is phrased as fail-closed incompleteness, not as a soundness defect, and that
  issue #146 is cited for the closure defect rather than re-litigated here.
