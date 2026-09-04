# Code review — M3 restack on accepted M2

Verdict: **FAIL**

Route: `41eadaeae674`

Reviewed HEAD: `9e9cfbd6971dacd5772d3802d0b758a0c0c5ba83`

Merge parents:

- M3 first parent: `d4cc01fe8d6ec82cce93106191774fc32e8dbb46`
- Accepted M2 second parent / route base: `022411b05924618cfde0cb97b8c8aff4955e6013`

Reviewed verification fingerprint: `4c47bc953827c29edf37a61516c89529db55f70c2b7a8213fcd9c788caa967d8`

This is independent local review evidence. It is not merge authority and does not replace a fresh App-owned exact-SHA Trust CI check.

## Blocking finding

### CR-001 — Receipt conflict resolution restores branch-history-dependent status assertions

Priority: **Blocking**

Locations:

- `tests/test_change_receipts.py:366`
- `tests/test_change_receipts.py:502`

Both tests assert `result.status == 'fail'` for `_architecture_check()` performed against the repository-wide frozen-adoption comparison. This contradicts the active restack requirement:

> Whole-history architecture status may differ from isolated-diff applicability; tests assert invariant fields rather than a branch-history-dependent global status.

It also reverses the accepted M2 stabilization in `b897bf07b3f4c950a4f1d427b3f253d2f81f6eec`, which deliberately removed these global status assertions while retaining exact comparison-base, route-base, fingerprint, configured-state, result-name, and staleness bindings.

The assertions happen to pass at `9e9cfbd…` because the current cumulative diff from frozen adoption fails architecture fitness. They do not prove the named receipt contracts and will change when unrelated branch history changes. The restack's own architecture ruling explicitly says not to assert either `pass` or `fail` there.

Required remediation: return this conflict to the same write owner, remove only the two global `result.status == 'fail'` assertions, and keep the M2 typed assertions plus all M3 governance receipt/binding tests. Then rerun the focused receipt tests, full verifier, and all selected reviews on the new exact head/fingerprint.

## Verified preserved behavior

- The merge is a true two-parent merge. Exact accepted M2 and the preserved M3 head are both ancestors; the active route base exactly equals the accepted M2 second parent.
- `git show --remerge-diff` identifies the documented four conflict paths: `decisions.md`, `mistakes.md`, `tests/test_architecture_fitness.py`, and `tests/test_change_receipts.py`. No unresolved conflict markers remain outside historical evidence text.
- `decisions.md` retains both M3 authority/provenance decisions and M2 read-only packaging/process-cleanup decisions, then appends the restack decision. `mistakes.md` similarly retains both histories and adds concrete restack-command lessons.
- `tests/test_architecture_fitness.py` correctly combines the accepted M2 ROOT-independent applicability assertions with M3's mandatory `governance_promotion=pass` assertion. It does not reintroduce the obsolete whole-history `change_separation=pass` or absence-of-`trust-ci/**` claims. Dedicated fixture tests continue to enforce mixed-change rejection and finite code-budget failures.
- Accepted M2 Trust-CI workspace implementation and tests are blob-identical at the merge head: `trust-ci/src/adaptive_trust_ci/workspace.py` and `trust-ci/tests/test_workspace.py`. The bounded TERM/KILL flow, direct classifier tests, zombie-only acceptance, and live/unknown fail-closed behavior are preserved.
- M2 descriptor-bound packaging remains present. M3 changes to `install_into.py` and `test_installer.py` are the pre-existing M3 governance payload/target-owned-registry additions layered on the M2 implementation; they do not replace its no-follow/read-only/source-invariance logic.
- M3 governance engine, CLI, registries, four schemas, and governance/governance-fitness tests are blob-identical to the M3 parent.
- `architecture/rules.yaml` correctly unions both parents: governance/schema prefixes and `FIT-GOVERNANCE-HANDOFF-COMPATIBILITY` are retained, while `FIT-BOUNDED-ARCHITECTURE-CHANGE.max_changed_lines` remains exactly `10820` with severity `error`.
- No deployed Trust CI policy, holdout, image, signing material, human trust store, branch protection, GitHub Actions workflow, public API, event, database, or external integration is changed by the merge resolution.

## Verification inspected

The current full verifier receipt is PASS for the reviewed pre-report fingerprint and records:

```text
change-spec: pass (2 specs)
architecture: pass (drift, fitness, diagrams)
governance: pass
secret-scan: pass
contract-structure: pass (4 contracts)
sql-safety: pass
ruff: pass
bandit: pass
python-unittest: pass
coverage: pass
source-stability: pass
architecture exact base: 022411b05924618cfde0cb97b8c8aff4955e6013
architecture route base: 022411b05924618cfde0cb97b8c8aff4955e6013
```

Focused inspection also confirmed both parents as ancestors, the exact `10820` budget, the governance handoff compatibility rule, M2/M3 ownership blobs, and the relevant architecture/receipt tests. A passing verifier does not waive CR-001 because the defect is a brittle assertion that currently agrees with this branch's incidental cumulative status.

## Residual risks after CR-001

- Historical exact-state M3 handoffs and receipts remain stale after the merge and cannot be reused. Fresh evidence must bind the remediated exact head.
- The local merge and review do not inherit accepted M2's external attestation or approvals. PR #11 still requires a new App-owned policy-epoch check on its final exact SHA and any scopes required by deployed policy.
