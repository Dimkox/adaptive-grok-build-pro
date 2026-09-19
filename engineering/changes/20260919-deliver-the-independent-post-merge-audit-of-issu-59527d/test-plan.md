# Test plan — durable delivery of the #104 post-merge audit

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | The shared append-only document is only extended: `git diff --numstat -- mistakes.md` shows additions with **0 deletions**, and the 6 recovered headings still appear exactly once each | AC-004, `SIG-001`, harness block F |
| P0 | No machine-local absolute path or host name survives in committed evidence | AC-005: search this package's files for a leading home-directory or temporary-directory absolute path and for this host's user name; the check must return nothing (this row deliberately avoids quoting those literals) |
| P0 | The typed spec passes the repository validator in gate mode | `python3 scripts/grok_spec.py validate --gate` → `ok: true`, `errors: []` |
| P0 | No identifier in this package is ambiguous: the controller's residual list is `CAR-1 … CAR-5`, and the only surviving `R1 … R5` list is the `ai_architect` report's own rejection-branch mechanisms, mapped in the controller table's mapping section | `grep -rni "residual R[1-5]\b" <this package>` must return nothing; `grep -rn "R[1-5]" <this package>` may hit only `evidence/analysis-ai_architect.md` (its own list) and lines that discuss or map the collision — check each hit names which list it means |
| P1 | Every numeric claim in the evidence is reproducible at the named SHA | run `evidence/measurement-harness.md` blocks A–F in throwaway clones of `2f66ba6` and `d871ea6`, **one process per tree**, and compare against the printed result lines quoted in that file; every table in `controller-declared-inventory-table.md` names its block |
| P1 | The headline counts agree everywhere they appear (12/38 → 36/38 json_schema; 21/50 → 46/50 all kinds; unlocked 24 and 25) | `grep -rn -e "36/38" -e "46/50" -e "12/38" -e "21/50" <this package>` (one `-e` per pattern, so no shell pipe is needed) and read each hit against block A's printed lines |
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
- Confirm the eight new entries are internally chronological and that the base file's 12 pre-existing out-of-order
  date pairs are unchanged (harness block F prints both counts), and that no existing entry's text was reflowed.
- Confirm **CAR-1 … CAR-4 are phrased as fail-closed incompleteness** (no verdict rendered, so nothing wrong is
  certified), while **CAR-5 is phrased as a latent soundness defect** with its reachability measurement attached
  (41 `$id` values, none equal to a declared path, 0 of 86 `$ref` bases ambiguous → latent, not live) and its issue
  #147 citation. Do **not** smooth CAR-5 into fail-closed wording: it is the one item in this record that can
  certify a false `compatible`.
- Confirm the ablation line states both units with their denominators (json_schema unit over 38 declared records;
  all-kinds unit over 50 declared records) rather than one number under one label.
- Confirm issue #146 is cited for the closure defect rather than re-litigated here, and that the supersession notes
  keep the wrong numbers visible instead of deleting them.
