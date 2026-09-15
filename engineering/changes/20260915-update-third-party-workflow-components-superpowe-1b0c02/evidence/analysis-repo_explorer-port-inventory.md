# Port inventory: workflow artifact adapters → origin/main

Analyst: repo_explorer role (read-only Explore agent). Transcribed verbatim by the single write owner after agent completion (the agent had no write tool).

Provenance: source `/home/pall/grok-projects/adaptive-grok-build-pro-workflow-adapters` (`feature/workflow-artifact-adapters` @ `dccaeec`, merge-base with `origin/main` = `1c06299`); target `/home/pall/grok-projects/adaptive-grok-build-pro-third-party-sync` (`feature/third-party-components-sync` = `origin/main` @ `7b14736`, VERSION 2.0.16). Main is +1600 files/400k insertions past the merge-base; the branch is +236 files/43k.

Disclosure: one redundant probe created `/tmp/x` (1778 bytes, git-apply verbose noise, no repository content). Neither product tree was touched by the analysis.

## 1. Untracked files — all 12 epic paths verified ABSENT on `origin/main`

Verified with `git ls-tree origin/main -- <path>` (empty) and a full-tree grep of `git ls-tree -r --name-only origin/main` for `^\.specify/|20260830|workflow_artifact|workflow-source|workflow-task|workflow-convergence|grok_artifacts` → zero matches; no renamed successor exists on main.

| Path (source worktree) | Lines | Bytes | Referenced by (source tree) | Classification |
|---|---|---|---|---|
| `.grok-stack/adaptive_grok/workflow_artifacts.py` | 1703 | 74933 | `scripts/grok_artifacts.py:12` (13 imported symbols), `tests/test_workflow_artifacts.py:15`, `tests/test_workflow_artifacts_adversarial.py:25`, `tests/test_workflow_artifacts_cli.py:27`, `verification.py` (new import), `architecture/system.yaml` node `repository_paths`, plan doc | PORT-AS-IS (pure add) |
| `scripts/grok_artifacts.py` | 158 | 6257 | `managed.json`, `install_into.py`, `test_structure.py:125`, `test_installer.py:160`, `README.md:58`, `QUICKSTART.md:93-95`, `tests/test_workflow_artifacts_cli.py:28`, system.yaml | PORT-AS-IS |
| `schemas/workflow-source-v1.schema.json` | 16 | 745 | system.yaml `CONTRACT-WORKFLOW-SOURCE-V1` + node paths, install_into.py, test_structure, test_installer, test_governance, README | PORT-AS-IS |
| `schemas/workflow-task-graph-v1.schema.json` | 29 | 2410 | same set (`CONTRACT-WORKFLOW-TASK-GRAPH-V1`) | PORT-AS-IS |
| `schemas/workflow-convergence-report-v1.schema.json` | 17 | 1682 | same set (`CONTRACT-WORKFLOW-CONVERGENCE-REPORT-V1`) | PORT-AS-IS |
| `tests/test_workflow_artifacts.py` | 572 | 25644 | plan doc Tasks 1-3 | PORT-AS-IS |
| `tests/test_workflow_artifacts_adversarial.py` | 827 | 37718 | plan doc, `AC-002/007/010` in change-spec.yaml | PORT-AS-IS |
| `tests/test_workflow_artifacts_cli.py` | 238 | 10406 | plan doc Task 4 | PORT-AS-IS |
| `docs/superpowers/plans/2026-08-30-workflow-artifact-adapters.md` | 76 | 6693 | `PROJECT_STATE.json` (`plan`), package `architecture.md`, `workflow/manifest.json` (role `plan`) | PORT-AS-IS (history doc; the `PROJECT_STATE.json` anchor is obsolete, see §2) |
| `docs/superpowers/specs/2026-08-30-workflow-artifact-adapters-design.md` | 46 | 7557 | `PROJECT_STATE.json` (`design`), `workflow/manifest.json` (role `spec`) | PORT-AS-IS |
| `.specify/specs/workflow-artifact-adapters/tasks.md` | 23 | 4855 | `workflow/manifest.json` (role `tasks`); `workflow_artifacts.py` `PATH_PREFIXES["spec-kit"] = (".specify/", "specs/")`; `architecture/system.yaml` node `repository_paths: [".specify"]` | PORT-WITH-DECISION — introduces a new top-level root entry; see §4/§5 |
| `engineering/changes/20260830-implement-a-new-model-agnostic-workflow-artifact-d41aa6/` (12 tracked-shape files incl. `workflow/manifest.json`, `workflow/task-graph.json` 5304 B, `workflow/convergence-report.json` 792 B, `route.json`, `change-spec.yaml`, state.json) | 227 | ~30 KB | only `.grok-stack/runtime/*` (git-ignored) | PORT (see rebase note) |

Runtime residue that must NOT be ported (gitignored): `.grok-stack/runtime/workflow-cas/20260830-*/.agb-recovery-*` and `runtime/receipts/d41aa61075eb/verification.json`.

Package detail: `route.json` carries `base_commit dccaeec…` / `base_fingerprint 5cc5cd418ab5…` — a commit outside main's ancestry. `workflow/task-graph.json`/`convergence-report.json` derive from the route and the three source docs; task IDs are content-derived and never include a full-tree fingerprint, so if `route.json` is ported verbatim the generated pair is consistent as-is; if the route binding is rewritten, they must be regenerated with `grok_artifacts.py compile/converge --write --expected-digest …`.

## 2. Modified tracked files — per-hunk classification

Applicability measured by piping each `git diff -- <file>` into `git apply --check` against the target (read-only).

| File | Raw diff | Real diff (quote/blank/wrap-normalized) | apply→target | Classification |
|---|---|---|---|---|
| `.grok-stack/adaptive_grok/receipts.py` | +126 −8 | +122 −6 (5 regions) | CLEAN | PORT-AS-IS (shared authority code — review) |
| `scripts/install_into.py` | +4 −0 | +4 −0 | CLEAN (hunk 2 offset +24) | PORT-AS-IS |
| `tests/test_governance.py` | +3 −0 | +3 −0 | CLEAN (hunk 1 offset +2) | PORT-AS-IS |
| `.grok-stack/adaptive_grok/verification.py` | +344 −190 | +197 −45 (29 regions) | conflict | PORT-WITH-REBASE (extract 3 epic hunks) |
| `tests/test_verification_doctor.py` | +554 −498 | +77 −24 (22 regions) | conflict | PORT-WITH-REBASE (extract 1 class + 1 import) |
| `.grok-stack/config/managed.json` | +2 −0 | +2 −0 | conflict | PORT-WITH-REBASE (1 of 2 lines is not epic scope) |
| `architecture/system.yaml` | +185 −0 | +185 −0 (3 blocks) | conflict | PORT-WITH-REBASE (append in place) |
| `architecture/generated/{context,container,data-flow,deployment,trust-boundary}.mmd` | +24 −0 | same | conflict (all 5) | DROP-AS-TEXT → REGENERATE |
| `README.md` | +6 −0 | +6 −0 | conflict | PORT-WITH-REBASE / re-derive (hunk 1 anchor deleted by PR #90) |
| `QUICKSTART.md` | +12 −0 | +12 −0 | conflict | PORT-WITH-REBASE (anchor survives) |
| `CHANGELOG.md` | +7 −0 | +7 −0 | conflict | DROP-OBSOLETE as written (pinned by test) |
| `PROJECT_STATE.json` | +13 −6 | same | conflict | DROP-OBSOLETE |
| `tests/test_architecture_model.py` | +13 −1 | +13 −1 | conflict | PORT-WITH-REBASE (hunk 1 DROP, hunk 2 PORT) |
| `tests/test_installer.py` | +4 −0 | +4 −0 | conflict | PORT-WITH-REBASE (new list members) |
| `tests/test_structure.py` | +5 −0 | +5 −0 | conflict | PORT-WITH-REBASE + missing registration |
| `decisions.md` | +12 −0 | +12 −0 | conflict (append context moved) | PORT-AS-IS-APPEND |
| `mistakes.md` | +60 −0 | +60 −0 | conflict (append context moved) | PORT-AS-IS-APPEND |

Format-noise warning (load-bearing): `verification.py` and `test_verification_doctor.py` were reformatted on the branch (single→double quotes, reflow): 898 diff lines reported, only 274 real. Main still uses single quotes and wrapped layout (`verification.py:31-32`, `:1013-1015`). Port only the real epic hunks.

Real epic hunks to carry:

- `verification.py`: (a) `from .workflow_artifacts import WorkflowArtifactError, validate_stored_workflow` plus `validate_evidence` added to the existing `from .receipts import (...)` block; (b) `def _workflow_artifacts_check(root, route, active_change, current_fingerprint) -> tuple[CheckResult, dict[str, object]]` (source lines 244-320); (c) call site + `workflow_check` in the `results` list + `"workflow_artifacts": workflow_metadata` in the report. Target anchors: import block `verification.py:16-20,22`; call site `verification.py:975-989` (insert after `governance_check, governance_metadata = _governance_check(...)` at :977 and after `governance_check,` at :985); report dict `'governance': governance_metadata,` at `verification.py:1031` (add the new key right after). Check-name assertions use `names.index(...)`/`assertIn` (`tests/test_verification_doctor.py:662-664`, `:1472-1475`, `tests/test_change_receipts.py:723`), so an extra `workflow-artifacts` check does not break them.
- `receipts.py`: `import re`, `RECEIPT_KINDS`/`MAX_RECEIPT_BYTES` constants, descriptor-bound `get_receipt()`, and `validate_evidence(root, route, *, current_fingerprint=None)` with closed-set/envelope hardening. Blast radius: main has no callers of `get_receipt` outside `receipts.py`; all `validate_evidence` callers pass two positional args (`tests/test_change_receipts.py:261,264,282,...`, `adaptive_grok/deploy.py`) — the new keyword is additive. Main's `write_receipt` already emits all ten `base_fields` (`receipts.py:527-536`) and no main test hand-forges partial receipts. Re-run `tests/test_change_receipts.py` + `tests/test_hooks.py` first.
- `test_architecture_model.py` hunk 1 (`len(records)==5`→8) is DROP-OBSOLETE: main replaced it with a floor at `tests/test_architecture_model.py:1329-1332` (`assertGreaterEqual(len(records), 41, "seed-completeness floor…")`). Main declares 41 contracts; +3 workflow contracts keeps the floor green. Hunk 2 (`CONTRACT-WORKFLOW-*` id-set assertion) ports, re-anchored next to the `evidence_records`/`semantic_records` assertions at `:1334-1355`.
- `managed.json` hunk 2 adds `"grok_spec.py"` — not epic work: main's `managed.json` omits it while `scripts/install_into.py:46` ships it. Recorded as an incidental finding; decide separately.

## 3. Committed M3-era branch content: nothing to port

`git log origin/main..HEAD` = 139 commits; `git cherry` marks all `+` (squash merges break patch-ids). Blob-level classification of all 236 files in `git diff origin/main...HEAD --stat`: 0 BRANCH-ONLY, 199 SAME-IN-MAIN, 37 DIVERGED — and every diverged file is "both-moved" (main evolved past it). `git log origin/main..HEAD` restricted to the epic paths is empty. Conclusion: the adapter epic was never committed anywhere; do not cherry-pick or merge `dccaeec`; port the working-tree delta only.

## 4. Target registration points (quote-and-append anchors)

Insertion must be literal, not re-serialized. `mistakes.md:19-21` (main): editing the canonical model requires appending in insertion order (the 1889-line re-serialization trap). `architecture/system.yaml` is JSON-with-a-.yaml name: insertion order required for `contracts`, `edges`, `nodes` (currently 41 contracts / 38 nodes / 40 edges). Expected epic diff there: exactly +185/−0.

1. `architecture/system.yaml` — append the three `CONTRACT-WORKFLOW-{SOURCE,TASK-GRAPH,CONVERGENCE-REPORT}-V1` objects at the contracts tail (after `CONTRACT-ADAPTIVE-DEMO-OPENAPI`); append five edges (`EDGE-ROUTE-WORKFLOW-COMPILER`, `EDGE-WORKFLOW-SOURCES-COMPILER`, `EDGE-CHANGE-EVIDENCE-WORKFLOW-COMPILER`, `EDGE-WORKFLOW-COMPILER-CHANGE-EVIDENCE`, `EDGE-WORKFLOW-COMPILER-LOCAL-VERIFIER`); append nodes `NODE-WORKFLOW-ARTIFACT-SOURCES` (`repository_paths: [".specify"]`) and `NODE-WORKFLOW-ARTIFACT-COMPILER` (module + 3 schemas + CLI). Nested-path ownership is precedented (`NODE-GOVERNANCE-VALIDATOR` owns narrow paths under nodes owned by others).
2. `architecture/generated/*.mmd` — regenerate from the rebased model via `python3 scripts/grok_architecture.py diagram …`; the drift gate `compare_generated(root, rendered)` in `verification.py:106-110` fails stale projections.
3. `scripts/install_into.py` — insert `"scripts/grok_artifacts.py",` in `MANAGED_FILES` between `grok_spec.py` and `grok_verify.py` (target ~:46-47); append the three workflow schemas after `"schemas/canonical-example.schema.json", "schemas/governance-handoff-v1.schema.json"` before the closing paren (~:72-74).
4. `.grok-stack/config/managed.json` — insert `"grok_artifacts.py",` after `"grok_approve.py",` in `scripts`. Only `adaptive_grok/doctor.py:45` reads this file; no test asserts completeness.
5. `tests/test_structure.py` — `test_core_product_files_exist` tuple: insert `"scripts/grok_artifacts.py",` after `"scripts/grok_spec.py",`; after `"scripts/grok_governance.py",` (line 217) append `workflow_artifacts.py` + three schema entries as in the source hunk. NEW WORK not present in the source diff: `ROOT_ENTRIES` (lines 16-29) is enforced bidirectionally (`test_repository_root_holds_only_canonical_entries`); committing `.specify/…` requires adding `.specify` to the frozenset (on the branch the test passed only because `.specify` stayed untracked).
6. `tests/test_installer.py` — re-anchor `"scripts/grok_artifacts.py"` next to `"scripts/grok_governance.py",` (line 159) and the three schemas after `"schemas/governance-rule.schema.json",` (166) inside `test_payload_is_sorted_safe_duplicate_free_and_profile_explicit`; payload paths must stay byte-sorted (`:147-149`).
7. `tests/test_governance.py:288-297` — widen the copied-schema tuple with the three workflow schema names (compiled model resolves those contract paths).
8. `tests/test_manifest_package.py:264-277` — required-set is a subset and `manifest.py` walks the tree: new files ship automatically; extending the subset is optional.
9. `Makefile` — nothing to add. Test discovery `unittest discover -s tests` picks the new modules automatically. Coverage floor `fail_under 74` (.coveragerc): 1703-line module + 1637 test lines is the main risk to watch.

## 5. Fixture / port-red risk check

- The three adapter tests read no repository fixtures; all `.specify/…`, `_bmad/…`, `docs/superpowers/…` strings are paths inside `tempfile` project roots. Tests port green.
- Port-red #1 (structural): committing `.specify/` violates `ROOT_ENTRIES` unless added — decision required (§4.5). Keeping it uncommitted would leave `workflow/manifest.json` naming a missing source for the active-change check.
- Port-red #2: `CHANGELOG.md` hunk breaks `test_structure.py:279` pin (`startswith("# Changelog\n\n## 2.0.16 — 2026-09-13\n")`). No `## Unreleased` heading; re-derive at release sync only.
- Port-red #3: the `PROJECT_STATE.json` hunk targets schema v1 (`completed_milestones`, `active_work`); main is v2 with `tests/test_project_state.py` pins (`OBSERVED_MAIN_SHA`, `CURRENT_CHECK`). Drop; express visibility through current v2 fields only.
- Port-red #4 (README): hunk 1 anchor was deleted by PR #90; hunks 2/3 have live anchors (`README.md:79` Map list, `:119` "What this is" bullet). Keep additions minimal per `mistakes.md:942`.
- README/QUICKSTART coupling: `tests/test_structure.py:736-750` requires specific `](path)` links and QUICKSTART literals; adding is safe, deleting/reflowing is not.

## 6. Uncommitted decisions/mistakes additions in the source worktree (net-new appends)

Target-tree duplicate grep (`workflow artifact|WorkflowArtifact|grok_artifacts|Spec Kit|BMAD`) → none; main's last headings are `## 2026-09-15 — Keep README architecture references tied to the reviewed model` (decisions) and `## 2026-09-15 — Do not preserve decorative inventory as an architecture requirement` (mistakes). All 13 entries are net-new appends:

- decisions.md +12 lines / 3 entries: `2026-08-30 — Compile framework artifacts through one advisory boundary`; `2026-08-30 — Serialize workflow artifact publication around atomic exchange`; `2026-08-30 — Separate tracked source claims from effective receipt state`.
- mistakes.md +60 lines / 10 entries (source `mistakes.md` lines 190-249): `2026-08-30 — Treated imported verification metadata as executable-shaped authority`; `… Reimplemented receipt freshness incompletely`; `… Called check-then-replace an atomic CAS`; `… Let schemas and runtime validation drift`; `… Validated a CAS competitor before restoring its name`; `… Persisted receipt authority in task source state`; `… Kept parser scope across independent BMAD headings`; `… Left authority readers and parser failures outside the shared boundary`; `… Dropped ctime and trusted a stat-before-unlink cleanup`; `… Treated a final pre-syscall identity check as linearization proof`.

## 7. Suggested port order (single write owner)

1. Add the 8 code/test/schema new files + 2 superpowers docs (pure adds).
2. `architecture/system.yaml` in-place appends (+185 expected), then regenerate all 5 `architecture/generated/*.mmd`; confirm no re-serialization churn.
3. Registration: `install_into.py` → `test_installer.py` → `test_structure.py` (incl. `ROOT_ENTRIES` `.specify` decision) → `managed.json` (grok_spec drive-by decided separately) → `test_governance.py`.
4. `receipts.py` (applies clean; run `tests/test_change_receipts.py`, `tests/test_hooks.py` immediately).
5. `verification.py` epic hunks only, then `tests/test_verification_doctor.py` `WorkflowArtifactsVerificationTests` + import only.
6. `test_architecture_model.py` hunk 2 only.
7. Port/rebase the `20260830-*` package onto the new base; regenerate or verbatim-keep `workflow/task-graph.json` + `convergence-report.json` per §1 note.
8. Docs last: README (Map + What-this-is re-derived), QUICKSTART (section between step-6 block and step 7), CHANGELOG untouched, `decisions.md`/`mistakes.md` pure appends (incl. the root-worktree 2026-09-14/15 entries), `PROJECT_STATE.json` per reconciliation design.
9. `python3 scripts/grok_verify.py --mode pr`.
