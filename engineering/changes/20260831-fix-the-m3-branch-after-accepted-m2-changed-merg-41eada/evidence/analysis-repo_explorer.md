# Repository analysis — M3 restack onto accepted M2

Route: `41eadaeae674`  
M3 head: `d4cc01fe8d6ec82cce93106191774fc32e8dbb46`  
Accepted M2: `022411b05924618cfde0cb97b8c8aff4955e6013`  
Common ancestor: `635c9ddf2d63c1ea823074106976a8f3de6299a9`

## Ancestry

Neither target is an ancestor of the other. M3 descends from `635c9dd`; M2 is
the accepted merge of the packaging/read-only compatibility work and the Trust
CI zombie-cleanup hotfix. A three-way merge (`base=635c9dd`, `ours=d4cc01f`,
`theirs=022411b`) produces exactly four content conflicts; all other M2 and M3
changes are additive or automatically mergeable.

## Conflicts and exact resolution ownership

| Path | M3 content | Accepted-M2 content | Required resolution |
| --- | --- | --- | --- |
| `decisions.md` | Governance/provenance/frozen-handoff lessons | Read-only packaging, zombie-only process groups, receipt scoping, procfs tests | Keep both chronological decision sets. |
| `mistakes.md` | Governance lifecycle/evidence/schema/snapshot root causes and generated projection framing | Descriptor/manifest/output publication and zombie-cleanup root causes | Keep both; resolve only ordering/header duplication. |
| `tests/test_architecture_fitness.py` | Adds `governance_promotion` required category and its pass assertion | Removes broad current-tree `code_budget`/whole-report pass assertions; adds exact-root `safe.directory` regression | Retain both changes. M2 intentionally avoids a broad cumulative-stack pass claim; M3 must require governance promotion. |
| `tests/test_change_receipts.py` | Governance fixtures/imports/receipt binding; concrete pre-adoption architecture status is `fail` | Isolated clone Git configuration and removal of obsolete `result.status == pass` assertions | Retain all. Where assertions differ, retain M3's concrete `fail` expectation; M2's deletion is compatible. |

`git merge-tree --write-tree d4cc01fe 022411b059` reports only these four
unmerged paths.

## Overlaps that merge cleanly

- `README.md`: retain M3's governance/M4 state, commands, map, and installer
  exclusions plus M2's descriptor-bound read-only packaging paragraph.
- `architecture/rules.yaml`: retain M3's governance/schema path boundaries and
  governance-handoff policy plus M2's `max_changed_lines: 10820` ceiling.
- M2's update to its historic M2 requirements package auto-merges and should
  remain accepted-M2 history.

## Payloads and tests that must survive

M2-owned implementation is independent of M3 requirements and must be inherited
unchanged: `.grok-stack/adaptive_grok/architecture_diff.py`,
`.grok-stack/adaptive_grok/manifest.py`, `scripts/package_stack.py`,
`tests/test_manifest_package.py`,
`trust-ci/src/adaptive_trust_ci/workspace.py`, and
`trust-ci/tests/test_workspace.py`, plus the two M2 change packages dated
20260829 and 20260831.

M2 commit `6a2ccca` is particularly material: it adds bounded post-SIGKILL
procfs classification, preserving the original command error only for proven
all-zombie groups while live/incomplete evidence fails closed. Its regression
authority is `trust-ci/tests/test_workspace.py`.

M3-owned scope is the governance layer: `governance/**`, the four governance
schemas, `scripts/grok_governance.py`, governance logic under
`.grok-stack/adaptive_grok/`, architecture model/rules/generated diagrams, and
the governance, architecture, receipts, spec, installer, structure, and
verification tests.

Run both cohorts after resolving conflicts:

```bash
python3 -m unittest trust-ci.tests.test_workspace -v
python3 -m unittest tests.test_manifest_package tests.test_architecture_fitness tests.test_change_receipts -v
python3 -m unittest tests.test_governance tests.test_governance_fitness tests.test_architecture_model tests.test_change_spec tests.test_installer tests.test_structure tests.test_verification_doctor -v
python3 scripts/grok_architecture.py validate --json
python3 scripts/grok_architecture.py diagram --check --json
python3 scripts/grok_governance.py validate --json
python3 scripts/grok_governance.py check-projections
```

Then run `python3 scripts/grok_verify.py --mode pr` against only the final
restacked fingerprint and conduct the route-selected review wave.

## Risks

- Taking either test file wholesale loses the other milestone's safety
  regression; merge assertions deliberately.
- The documentation conflicts are append/add history, not competing authority:
  deleting either side loses durable operating context.
- The merged tree includes Trust-CI and local implementation paths. Do not add
  unrelated edits while resolving; validate M3's new architecture/risk binding.
- The restacked head invalidates PR #11's former exact-SHA check and local
  receipts. Fresh external Trust CI and required signed approval evidence remain
  necessary.
