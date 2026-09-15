# Architect analysis — porting the workflow-artifact-adapters epic onto `main` @ `7b14736`

Tree analyzed: `/home/pall/grok-projects/adaptive-grok-build-pro-third-party-sync` (VERSION `2.0.16`, HEAD
`7b14736 docs: remove decorative README graph and clarify package guidance (#90)`).
Source of the epic: `/home/pall/grok-projects/adaptive-grok-build-pro-workflow-adapters` @ `dccaeec` (M3-era base)
+ uncommitted working tree. Route authority:
`.grok-stack/runtime/active-route.json` → route `1b0c02b8a134`, `write_agent: integration_implementer`,
`required_evidence: [verification, code_review, test_review, security_review]`, `base_commit: 7b147366a1f9…`,
`delivery_expected: true`, risk `medium`, profiles `[base, contracts, integration]`.

All `file:line` anchors below are TARGET unless prefixed `SRC:` (source worktree).

> **Scope of this analysis.** Read-only; the single artifact written is this file. Every judgement below is about
> the **tracked** tree at `7b14736` (`git ls-tree HEAD`), which is what the gate, `ROOT_ENTRIES` and
> `validate_repository_drift` evaluate. While this report was being written, the target worktree was being populated
> concurrently by other route agents: `workflow_artifacts.py`, `scripts/grok_artifacts.py`, the 3
> `schemas/workflow-*.schema.json`, the 3 `tests/test_workflow_artifacts*.py`,
> `docs/superpowers/{specs,plans}/2026-08-30-*`, the old epic package `engineering/changes/20260830-…-d41aa6/` and
> a copied `.specify/` directory now appear as **untracked** entries in `git status`. None of them are in `HEAD`,
> so the `.specify` finding in §3.3 and the "do not port the old package" finding in §1.5 are now live decisions,
> not hypotheticals.

## 0. Verdict

Port is viable and mostly additive, but it is **not a cherry-pick**. Concretely:

| Epic file | Applies to main? | Action |
|---|---|---|
| `.grok-stack/adaptive_grok/workflow_artifacts.py`, `scripts/grok_artifacts.py`, 3× `schemas/workflow-*.schema.json`, 3× `tests/test_workflow_artifacts*.py` | clean (new files, absent from main) | copy as-is |
| `.grok-stack/adaptive_grok/receipts.py` | **clean** — main blob `1292557` **is** the epic's pre-image | apply as-is |
| `.grok-stack/adaptive_grok/verification.py` | **diverged** — main blob `ed42c7f` ≠ pre-image `d718b0d`; 586 ins / 347 del | re-hand-anchor 5 touch points; **discard the reformat** |
| `architecture/system.yaml` | patch-rejects (`git apply --check: patch failed: architecture/system.yaml:40`), lands with fuzz | re-apply as 3 pure additions; **must fix `.specify` + contract role** |
| `architecture/generated/*.mmd` (5 files) | all 5 hunks fail | **regenerate**, never merge |
| `tests/test_architecture_model.py` | epic hunk targets a line that no longer exists (`len(records) == 5` → `8` at SRC `:1040`) | re-anchor one new block |
| `tests/test_structure.py`, `tests/test_installer.py`, `scripts/install_into.py`, `.grok-stack/config/managed.json`, `tests/test_verification_doctor.py` | anchors moved | re-apply semantically |
| epic change package `SRC:engineering/changes/20260830-…-d41aa6/` (incl. `workflow/manifest.json`) | n/a | **do not port** (§1.5) |
| `decisions.md`, `mistakes.md`, `PROJECT_STATE.json`, `README.md`, `QUICKSTART.md`, `CHANGELOG.md` | epic's versions are M3-era | redo against current main (§2, §4) |

Nothing in main's `manifest.py` or `policy.py` gates a new core module: packaging is a **denylist** walk
(`.grok-stack/adaptive_grok/manifest.py:55-72` `is_included_relative_path`, `EXCLUDED_PARTS:10-12`), so new
tracked files are auto-packaged; `.grok-stack/config/policy.json` `protected_paths` covers `.grok-stack/**`,
`scripts/grok_*.py`, `tests/test_*.py`, `decisions.md`, `mistakes.md`, `README.md`, `CHANGELOG.md`, `VERSION`
(hook guardrail → needs a protected-write grant) but **not** `architecture/**` or `schemas/**`.

## 1. Authority integration (verification / receipts / manifest / policy)

### 1.1 Current check registration list — the thing to touch, verbatim

`verification.py:965-989` (main today):

```python
def verify(root: Path, mode: str = 'pr', profiles: list[str] | None = None, record: bool = True) -> dict[str, object]:
    checked_fingerprint = tree_fingerprint(root)          # :964
    route = get_active_route(root)
    active_profiles = profiles or (route.get('quality_profiles', ['base']) if route else ['base'])
    git_ranges = _git_range_selection(root, route, mode)   # :967  (PR#77-90 addition, absent from epic base)
    files, changed_file_inventory = _changed_file_inventory(
        root, route, mode, git_ranges,
    )

    spec_check, spec_metadata = _change_specs(root, files, route, mode)
    architecture_check, architecture_metadata = _architecture_check(root, route)
    governance_check, governance_metadata = _governance_check(
        root, route, architecture_metadata
    )

    results: list[CheckResult] = [
        _git_diff_check(root, mode, git_ranges),           # :982  signature changed: epic had (root)
        spec_check,
        architecture_check,
        governance_check,
        _secret_scan(root, files),
        _contracts(root, files),
        _sql_safety(root, files),
    ]
```

Exactly **five** insertions are required, none of them in the fingerprint or source-stability path:

1. `:15-20` import block — add `validate_evidence` to the existing `from .receipts import (…)` tuple
   (main's tuple is `active_architecture_binding, active_governance_binding, write_receipt`).
2. `:22-23` — add `from .workflow_artifacts import WorkflowArtifactError, validate_stored_workflow`.
   `get_active_change` is **already imported** on `:22` (`from .state import get_active_change, get_active_route`),
   used only inside `_change_specs` today — no import churn.
3. After `_governance_check` returns (main `:241`, the `def _command_check` boundary at `:245`) — insert
   `_workflow_artifacts_check` (SRC `verification.py:244-320`, ~77 lines).
4. `:979/980` — call it, and `:985` — append `workflow_check,` immediately after `governance_check,`.
   Pass **`checked_fingerprint`** (`:964`), not `final_fingerprint`.
5. `:1031` — add `'workflow_artifacts': workflow_metadata,` after `'governance': governance_metadata,` in the
   report dict (`:1020-1034`).

The epic's `verify()` body must **not** be copied: it still contains the pre-PR#77 lines
`base = route.get('base_commit')` / `files = changed_files(root, base)` and `_git_diff_check(root)`. Replacing
main's range-union inventory with those two lines would silently revert the PR#77-90 base-selection work — the
highest-risk regression in this port.

### 1.2 Source-stability and fingerprint logic stay untouched

* `:1005-1017` `final_fingerprint = tree_fingerprint(root)` / `source_stable = …` / the `source-stability`
  `CheckResult` — no edit.
* `:1035-1042` the receipt guard `if record and route and governance_check.status != 'fail' and source_stable:` —
  no edit.
* `tree_fingerprint` (`util.py`) hashes `git HEAD` + `changed_files(root)`. Receipts live in
  `.grok-stack/runtime/receipts/<route_id>/` (`receipts.py:457-460` `receipt_dir`) which is gitignored
  (`.gitignore:2 .grok-stack/runtime/*`), so the new check **reading** canonical receipts cannot move the
  fingerprint. `validate_stored_workflow` (`SRC:workflow_artifacts.py:1296-1335`) is pure-read; nothing in the
  check writes.
* Check-count safety: `summarize_verification_report` caps `checks` at 64 (`:937`); main emits ~12 in pr mode.
* No test pins the check-name list of `verify()`. The only name-sensitive assertions are
  `_check(report, 'source-stability')` (`tests/test_verification_doctor.py:724`) and `_names(_python(root))`
  (`:1077, :1178, :1206, :1353`) — order-insensitive for our insertion point.
* The epic's own additions to `test_verification_doctor.py` are importable as-is
  (`from adaptive_grok.verification import (…, _workflow_artifacts_check, …)` + class
  `WorkflowArtifactsVerificationTests`) — strip its quote-style churn.

### 1.3 `receipts.py` — applies cleanly, and is the only core file that does

`git hash-object` proves main's `receipts.py` == `1292557bebdcff1a9dd033b87c8683c845561eff`, which is the epic
diff's **pre-image** blob. The hunks (`+RECEIPT_KINDS`/`+MAX_RECEIPT_BYTES` after `:38`, and the
`get_receipt`/`validate_evidence` rewrite at main `:555-605`) land byte-exactly. Main has received no
`receipts.py` change since the M3 base — the l5/factory/PR#77-90 work went to `verification.py`,
`architecture*`, `factory/`, `delivery/`, docs. Behavior deltas that matter to us:

* `get_receipt` becomes descriptor-bound/no-follow/bounded with duplicate-key and identity-race rejection, and
  raises for a `route_id`/`kind` outside the closed set.
* `validate_evidence(root, route, *, current_fingerprint=None)` gains the keyword the workflow check needs, plus
  envelope-shape findings. Main's `validate_evidence(root, route)` at `:560` has no callers outside
  `scripts/grok_verify.py`/hooks — signature is backward-compatible (keyword-only, defaulted).

### 1.4 `verification.py` divergence judgement (main drifted, the epic mostly did not)

Main-only code the epic never saw, which must survive: `_git_range_selection`, `_select_local_pr_target`,
`_resolve_commit`, `_existing_ref_candidates`, `GitRangeBase`/`GitRangeSelection` (`:41-58`, `:277-508`),
`_changed_file_inventory` (`:520-560`), `os` import, `factory-unit` + `factory-postgres-exit` steps in `_python`
(`:889-918`), and the `'changed_file_inventory'` report key (`:1028`).

**Do not carry the epic's reformatting.** `git diff -U2 --ignore-all-space` shows ~398 of its 403 added lines in
`verification.py` are `'` → `"` and 120-column re-wrapping of untouched functions. Main is single-quote/long-line
and `ruff.toml` selects only `["E4","E7","E9","F"]` (E501 off, `line-length` advisory) — the reformat buys
nothing and would put ~600 spurious lines of a protected control-plane file into a security review. Port only the
five touch points in main's existing style.

### 1.5 The opt-in trigger, and the decision about activating it in *this* PR

`_workflow_artifacts_check` gates on
`engineering/changes/<active change_id>/workflow/manifest.json` (`SRC:verification.py:256-270`): no active change
→ `skip`; no manifest → `skip` + `{"configured": false, "status": "not_configured"}`; symlink/non-regular
manifest → `fail`. It also hard-`fail`s when `active_change["path"] != f"engineering/changes/{change_id}"`.

Recommendation: **ship the check with the trigger un-fired** (this PR's package gets no `workflow/` directory),
proving both branches in unit tests only. Three independent reasons:

1. The epic's own package (`SRC:engineering/changes/20260830-…-d41aa6/workflow/manifest.json`) references
   `.specify/specs/workflow-artifact-adapters/tasks.md`, which is **untracked** in the source tree (
   `git status: ?? .specify/`). Committing it fails `test_structure.py:31-37` (§3); not committing it makes
   `load_source_manifest` fail on a clean checkout — i.e. the gate would go red for the PR that delivers the gate.
2. The stored graph is **route-bound**: `compile_task_graph`/`_validate_route`
   (`SRC:workflow_artifacts.py:519-543`) embed `write_agent`, `review_agents`, `required_evidence` from the
   **gitignored** `.grok-stack/runtime/active-route.json`. A committed graph is only reproducible in the exact
   route context that produced it, so a second host/agent with a different route recomputes a different graph →
   `stored task graph differs from current sources/native route` (`:1321-1322`) → hard gate failure.
3. `receipt_errors` is deliberately **non-blocking** — `ok` is computed only from stored-vs-recompiled drift and
   blocking findings (`:1327-1333`); receipts move `effective_status` pending→verified
   (`effective_task_statuses:1103-1118`). That bootstrap is sound but self-referential inside a single PR whose
   receipts are written by the same verifier run that consumes them. Not worth spending on the delivery PR.

Corollary: do **not** port `SRC:engineering/changes/20260830-…-d41aa6/` at all. `_change_specs` validates every
changed `engineering/changes/**/change-spec.yaml` at the gate (`:975` + `:660-668`), so shipping a second,
M3-era spec package adds a gate surface for zero value; design/plan docs belong under
`docs/superpowers/{specs,plans}/` (already the repo convention, and the roadmap §11 steps 2-3 require it).

## 2. Governance projection: `decisions.md` / `mistakes.md`

### 2.1 It is generated, and the generator never writes

* Renderer: `.grok-stack/adaptive_grok/governance.py:2872-2941` `render_markdown_projections(snapshot, now=…)`;
  markers `:83-84` `_PROJECTION_BEGIN/_END`.
* CLI: `scripts/grok_governance.py:143-165` — `project` prints proposed content + digests, `check-projections`
  compares **whole-file bytes** (`(root / name).read_text() != content`) and reports `mismatches`.
* Splice: `scripts/grok_governance.py:72-92` `_merge_projection` — requires exactly one balanced BEGIN/END pair
  (`begin_count != end_count or begin_count > 1` → `GovernanceError("…projection markers are malformed")`),
  replaces **only** the marked region, and preserves everything outside it. With no markers it inserts after the
  first newline. Both commands assert `"mutated": False`.
* Test enforcement: `tests/test_governance.py:1972-1985` pins only the rendered block's own text
  (`"NON-AUTHORITATIVE PROJECTION"`, `"cannot approve, activate, repay, or accept"`, the four `## ` sub-headings);
  `:2023-2039` proves `project`/`check-projections` are deterministic and byte-preserving, on **copies** of ROOT's
  two files (`:1633-1634`, `:1741-1742`). No test reads the root files' non-projection prose.

Conclusion: human prose outside the markers is unconstrained; the only way to break this is to edit *inside*
lines 3-13.

### 2.2 Exact safe insertion point

**Append at end of file.** `decisions.md` is 646 lines; the newest entries are already at the tail
(`:604`, `:616`, `:621` 2026-09-14; `:626-646` five 2026-09-15 entries). Same in `mistakes.md` (944 lines;
`:900-944` are 2026-09-14/15). Do **not** insert after the END marker: `decisions.md:15-28` is a curated
pre-2026-09-10 group closed by the literal line `:30` "Patterns that paid for themselves. Each entry is at most
three sentences.", and `mistakes.md:15` is the file's standing preamble "Root causes, not symptoms. Record only
mistakes that caused a real problem." Putting new entries above those boundaries breaks the group semantics that
the projection banner was explicitly carved out to preserve.

Hard constraints: never touch `decisions.md:3-13` / `mistakes.md:3-13`; keep exactly one marker pair per file;
end the file with a single newline (the `git-diff-check` gate rejects blank-line-at-EOF — see the recorded
mistake at `decisions.md`-sibling `mistakes.md:916-922`).

### 2.3 What is actually undelivered (smaller than briefed)

Source: `/home/pall/grok-projects/adaptive-grok-build-pro` @ `ed76d88` (branch
`fix/path-aware-shell-policy-circuit-breaker`, **not** a descendant of `7b14736`), uncommitted hunks
`decisions.md @@ -157 +157,17 @@` and `mistakes.md @@ -69,3 +69,23 @@`. Presence-checked on main by literal grep:

| Pending entry | On main? |
|---|---|
| decisions `2026-09-14 — Check installed L5 state separately from shipped defaults` | **yes** `decisions.md:604` |
| decisions `2026-09-14 — Close PR82 with installed service and authenticated artifact evidence` | **yes** `:616` |
| decisions `2026-09-14 — Preserve the current public landing…` | **yes** `:621` |
| decisions `2026-09-15 Grok alongside primary Qwen` | **no — port this** |
| mistakes `2026-09-14 — A local clone omitted the newly merged remote-only commit` | yes |
| mistakes `2026-09-14 — Check the grant scope/action mapping…` | yes |
| mistakes `2026-09-14 — Confused an operation not performed with a site not deployed` | yes |
| mistakes `2026-09-15 Grok merged-release preparation` | **no — port this** |
| mistakes `2026-09-15 Public current-state drift after live activation` | **no — port this** (it is the mistake that authorizes §3-§5 of this report) |

**Exactly three entries**, not five/six. Also normalize their headings from `## 2026-09-15 Grok alongside primary
Qwen` to main's `## 2026-09-15 — Grok alongside primary Qwen` (em-dash form; universal in both files, not
test-pinned). Keep each decision ≤3 sentences per `decisions.md:30`.

## 3. `architecture/system.yaml` + generated diagrams

### 3.1 The file's real contract

`architecture/system.yaml` is **canonical sorted JSON** despite the extension —
`architecture.py:482-500` `_require_canonical_source` fails with
`"authority document is not canonical sorted two-space JSON with one newline"` (`code="canonical"`) unless
`data == json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"`. Top-level keys
therefore sit alphabetically (`contracts:` `:3`, `edges:` `:425`, `nodes:` `:1360`) but **array element order is
cosmetic**: `_normalize` (`:459-471`) sorts any list of dicts-with-`id`, so digests are order-independent
(`test_architecture_model.py:1155`) and diagrams sort by `id` anyway. Main's current counts: **38 nodes /
41 contracts / 40 edges**. This is precisely the trap recorded at `mistakes.md:17-21` (a 3-entry addition
produced a 1889-line rewrite): append in place, re-serialize with the file's own canonical form, and check that
diff size ≈ intended size (~185 lines here).

### 3.2 Invariants that break if added wrongly (verbatim)

`tests/test_architecture_model.py:1316-1332` — the only live-model assertions a node/contract addition can break:

```python
        self.assertTrue(
            all(node["runtime"]["evidence"] == "source_described" for node in snapshot.system["nodes"])
        )
        self.assertEqual(ARCH.validate_repository_drift(ROOT, snapshot), ())
        records = ARCH.contract_inventory(ROOT, snapshot)
        declared_ids = {str(contract["id"]) for contract in snapshot.system["contracts"]}
        declared_paths = {str(contract["path"]) for contract in snapshot.system["contracts"]}
        self.assertEqual({record.id for record in records}, declared_ids)
        self.assertEqual({record.path for record in records}, declared_paths)
        self.assertEqual(
            len(records), len(declared_ids),
            "duplicate contract ids in system.yaml would corrupt contract_inventory_digest",
        )
        self.assertGreaterEqual(
            len(records), 41,
            "seed-completeness floor; a PR may add contracts but never retire one silently",
        )
```

Node-id assertions at `:1243-1262` are `issubset`/`assertIn`/`assertNotIn` — additive-safe. `:1330` is a
**floor**: 41→44 needs no edit; **do not change it**. Prefix-grouped inventories at `:1336-1420` filter on
`"SEMANTIC" in record.id` / `"LANDING" in record.id` — `CONTRACT-WORKFLOW-*` cannot collide.
`tests/test_architecture_fitness.py` (5201 lines) never pins the live node set, the contract inventory or
diagram bytes; it builds synthetic models in temp repos (its four live-tree reads are `:125-132` code-budget ids,
`:4074-4086` landing-contract prefix filter, `:4056/:4121` explicit path lists, `:5044-5145` subprocess on temp
repos). Byte-exact diagrams are enforced by the **gate**, not a test: `verification.py:106-110, 148-158, 177`
(`compare_generated` → `generated-diagram-drift` → architecture check `fail`).

Semantic hard failures to avoid (`architecture.py:361-428`): one shared id namespace across
trust_domains/data_classifications/secret_classes/signals/contracts/nodes/edges; every node reference must resolve;
`repository path ownership tie` (`:405-413`) if two nodes list the *same normalized string* — so **never**
re-declare the bare literals `.grok-stack/adaptive_grok`, `scripts` or `tests` (already owned by
`NODE-LOCAL-ROUTE-POLICY` / `NODE-LOCAL-VERIFIER`); `duplicate capability edge` (`:419-426`); every
`repository_paths` entry and `contracts[].path` must exist on disk (`:604-637`), and every `.py` in the repo must
be prefix-owned (`:972-1032`). Schema closure: `schemas/architecture-system.schema.json` — id pattern
`:240-245` `^[A-Z][A-Z0-9_-]*$`, node `type` enum `:290-302`, node required `:305-315`, `runtime`
required `kind/lifecycle/network/evidence`; contract `kind` enum `:19-29` with the narrower runtime whitelist
`architecture.py:1061` `_SUPPORTED_CONTRACT_KINDS = {"event", "json_schema", "openapi", "signed_payload"}`.

### 3.3 Minimal correct addition shape (2 nodes + 3 contracts + 5 edges; `rules.yaml` unchanged)

1. **3 contracts** at `system.yaml:331/332` (append after `CONTRACT-ADAPTIVE-DEMO-OPENAPI`, before the `],`).
   Keep `kind:"json_schema"`, `version:"1"`, `path` = the three new `schemas/workflow-*.schema.json`.
   **Change `role`/`compatibility` from the epic's `bidirectional`/`bidirectional` to
   `producer`/`producer_accepted_by_old`.** Rationale: `architecture_fitness.py:865-869` skips brand-new
   contracts (`elif old is None: continue`), so `bidirectional` passes today and fails the first time a schema is
   edited, because both `json_schema` `contract_policies` (`FIT-CONSUMER-CONTRACTS` =
   `consumer_accepts_old`, `FIT-GOVERNANCE-HANDOFF-COMPATIBILITY` = `producer_accepted_by_old`) then apply; main's
   convention is 19 `producer_accepted_by_old` + 11 `consumer_accepts_old`, **zero** `bidirectional`.
2. **2 nodes** after `NODE-GOVERNANCE-REGISTRIES` closes (`:1665-1667`, the epic's exact context,
   `"trust_domain": "TD-REPOSITORY", "type": "repository" },`) and before `NODE-TRUST-CI-API` (`:1668`).
   Reuse only existing registries: `TD-REPOSITORY` / `TD-LOCAL-PREFLIGHT`, `DATA-REPOSITORY-SOURCE` /
   `DATA-CHANGE-EVIDENCE`, and `runtime.evidence = "source_described"` (forced by `:1317`).
   * `NODE-WORKFLOW-ARTIFACT-COMPILER.repository_paths`: keep the epic's 5 exact strings
     (`.grok-stack/adaptive_grok/workflow_artifacts.py`, `scripts/grok_artifacts.py`, 3 schemas). Optionally list
     the three new `tests/test_workflow_artifacts*.py` individually — they are otherwise covered by
     `NODE-LOCAL-VERIFIER`'s `tests`.
   * `NODE-WORKFLOW-ARTIFACT-SOURCES.repository_paths` — **`.specify` is a blocker.** It exists nowhere in main,
     and is untracked even in the source tree; `validate_repository_drift`/`validate_architecture` would report
     `missing_repository_path`, failing `test_architecture_model.py:1319`, while committing it fails
     `test_structure.py:36-37` (`.specify ∉ ROOT_ENTRIES`, a two-way exact check). Pick one:
     **(b, recommended)** declare `"repository_paths": [".superpowers"]` — already tracked, already in
     `ROOT_ENTRIES`, already whitelisted as non-authoritative at `architecture.py:706`
     `_NON_AUTHORITATIVE_REPOSITORY_DIRECTORIES`, contains only `.md` so it cannot trip `undeclared_source`;
     or **(a)** drop the node, repoint `CONTRACT-WORKFLOW-SOURCE-V1` onto the compiler node and delete
     `EDGE-WORKFLOW-SOURCES-COMPILER` (4 edges, 1 node).
3. **5 edges** at `:838/840` (right after `EDGE-GOVERNANCE-VALIDATOR-LOCAL-VERIFIER`, id at `:818`; before
   `EDGE-GITHUB-TRUST-CI-API` at `:840-841`) — the epic's semantic slot, verified identical context. Keep
   `protocol:"filesystem"` (inside `FIT-DECLARED-NETWORK-ONLY.allowed_protocols`), `network_policy:"no_network"`,
   `authentication:"local_os"`, `mode:"fail_closed"`, `observable_signal:"SIG-LOCAL-VALIDATION-FAILURE"` — all
   five endpoints and data ids still exist in main. The `CHANGE-EVIDENCE ⇄ COMPILER` pair is legal because `type`
   differs (`data_flow` vs `publication`) → not a duplicate capability edge.
4. **Tests:** insert the epic's new assertion block into `test_architecture_model.py` after `:1332` (before
   `evidence_records`) — nothing else; discard its `len(records) == 5 → 8` hunk. `test_structure.py:217`
   (`required` tuple, anchor `"schemas/governance-handoff-v1.schema.json", "scripts/grok_governance.py",`
   now at `:216-217`) — append the 5 new paths. `test_structure.py:15-27` `ROOT_ENTRIES` — only if a new
   root dir is committed.
5. **Delivery trio:** `scripts/install_into.py` `MANAGED_FILES` (add `scripts/grok_artifacts.py` after the
   `grok_spec.py` entry at `:42`, and the 3 schemas after `schemas/governance-handoff-v1.schema.json` at `:73`),
   `.grok-stack/config/managed.json` `scripts` list (`:52-64`; its only consumer is
   `.grok-stack/adaptive_grok/doctor.py:45`, list is **not** sorted on main — main also lacks `grok_spec.py`, so
   adding both entries is a genuine main-side fix), and `tests/test_installer.py:157-183` `expected` tuple.
   Payload ordering is safe: `build_payload` output must be byte-sorted (`test_installer.py:149-152`) and is
   computed, so tuple insertion position is free; the only whole-set equality is
   `test_installer.py:184-196`, scoped to `factory/tests/` — do not extend it.
6. **Diagrams:** regenerate, do not merge. `architecture_diagrams.py:33-45` re-sorts nodes and edges by `id`,
   `:36` drops `runtime.kind == "none"` from `deployment.mmd`, `:80-84` filters `data-flow.mmd`;
   `scripts/grok_architecture.py diagram` is **stdout-only by design** (README:157 — "projections are never
   authority"). Run `python3 scripts/grok_architecture.py diagram --json`, write each `artifacts[name]` verbatim
   to `architecture/generated/<name>.mmd` (exactly what `test_architecture_fitness.py:5098-5099` does), then
   `diagram --check --json` must return `"ok": true`. Expected delta for this addition: **+20 lines, 0
   removals** — `context.mmd` +1, `container.mmd` +7, `trust-boundary.mmd` +7, `data-flow.mmd` +6,
   `deployment.mmd` +3.
7. **Expect, don't fight:** adding edges/contracts trips `FIT-ARCHITECTURE-EXPANSION-RISK`
   (`architecture_fitness.py:2170-2195, 2290-2295`) → `risk_post: "red"` with `new_edge`/`new_contract`/
   `new_trust_crossing` triggers. That is a human-gate scope escalation, not a fitness failure;
   `fitness_status`, `drift_status`, `diagram_status` must all read `pass`. `FIT-BOUNDED-ARCHITECTURE-CHANGE`
   (10 820 changed lines over `.grok-stack/adaptive_grok, architecture, schemas, scripts, …`) is not threatened
   (~185 model + ~2 660 product/test lines).

## 4. `PROJECT_STATE.json` reconciliation

1 349 lines, `schema_version: 2`. **No JSON-schema and no top-level required-key test exists** — the only shape
pins are `test_project_state.py:74` (`schema_version == 2`), `:79`/`:81` (`milestones` keys == M0..M9 and each
milestone's keys == the 5 axes). A **new top-level key is free**. Zero runtime consumers exist: the only
executable readers are `tests/test_project_state.py:70` and `tests/test_manifest_package.py:1419`; everything
else (AGENTS.md:10-11, README, START_HERE, GROK_BUILD_HANDOFF) is human/agent prose.

### 4.1 Current-state fields a post-merge refresh must move, and their pins

| Field (anchor) | Must move? | Pin that fails |
|---|---|---|
| `observed_at` `:5` = `2026-09-15T09:54:21Z` | only the time-of-day, this PR | `test_project_state.py:78` `assertRegex(..., r"^2026-09-15T\d{2}:\d{2}:\d{2}Z$")` — **any other calendar day fails**; nested `work_inventory.observed_at:1171`, `runtime_observations.observed_at:1287`, `operational_qualification.observed_at:1339` are **not** compared to it |
| `observed_main_sha` `:6` = `61a05da…` | **no (keep)** | `:16` `OBSERVED_MAIN_SHA` (defined once), used once at `:77`; also `:407` (`current_unreleased_change.source_base == observed_main_sha`), `:633` (must appear verbatim in README `## Current state` **and** START_HERE `## Current project state`), `:645` (`== runtime_observations.evidence` file's `source_base`), `:676` (`!= published_release.merge_commit`) |
| `current_unreleased_change` `:145-168` | **no (keep empty-form)** | `:405-410` + `:411-415` (see §4.2) |
| `active_delivery` `:442-582` (`next_action`, `status`, `repository_delivery`, `package_handoff`, `local_source_gate`) | only after merge | `:405-406` lockstep on `route_id/branch/change_package/next_action`, `:411` `status == "source_delivered_operational_qualification_incomplete"`, `:412-415` bound to `published_release`; `schedule` and `m4_dimensions` are whole-object historical pins (`:493-531`, `:424-460`) |
| `work_inventory.open_pull_requests` `:1006-1051` | only when a PR opens **and** is meant to be listed | `:729` `== {13, 15, 33, 64}`, `:730` `assertNotIn(12, …)` |
| `work_inventory.active` `:1005` `[]` | no | `:733` `assertEqual(inventory["active"], [])` |
| `work_inventory.retained_unresolved` `:1052-1068` | after merge | `:767-774` **whole-list equality**, whose 2nd element is literally `{"branch": "feature/workflow-artifact-adapters", "local_head": "dccaeec2a6b7…", "purpose": "Local-only work requiring comparison before cleanup."}` — the epic is *already* recorded here; changing/removing it costs an edit to that literal |
| `delivered_non_milestone_work` `:420-441` | **only post-merge** | `:735` `assertEqual(len(delivered), 2)` + positional `delivered[0]`/`delivered[1]` field pins `:736-766` |
| `l5_production_preparation` `:1225-1285` | no | `:665` `selected_profile == runtime primary service`; `:676`; historical literals |
| `runtime_observations` `:1286-1337` | no | `:643-664` cross-checked against the **tracked** evidence file `engineering/changes/20260915-documentation-align-readme-roadmap-and-bootstrap-d7264b/evidence/observed-state.json` (`source_base = 61a05da…`, per-service `installed_sha`, `artifact_digest`, `state == "artifact_ready"`) |
| `operational_qualification` `:1338-1349` | no | `:671-674` six `assertFalse` |
| identity six-pack (`product_version:7`, `latest_published_release:8`, `published_release:36`, `prior_published_releases:66`, `local_candidate:381`) | **no — this PR must not bump VERSION** | `:75-76`, `:321-352` (`:350 assertEqual(len(prior), 3)`), `:353-399`, `test_manifest_package.py:1422-1455` (frozen v2.0.16 zip bytes), `test_structure.py:270-289` |
| `milestones` `:583-1003`, `delivered_change_history` `:169-380`, `historical_integrations` `:1102-1168`, `superseded` `:1069-1101`, `intentionally_untracked` `:1216` | **no — deliberately historical** | `:83-100`, `:109-230`, `:248-319`, `:775-807`, `:808-837`, plus adversarial meta-pins `:839-877` |

### 4.2 Why "record itself as `current_unreleased_change` with `status: local_pr_candidate`" does **not** fit as-is

Reading the tests settles it: `:408` `assertEqual(current["status"], "no_new_release_candidate")`,
`:409` `assertIsNone(current["identity"])`, `:410` `assertIsNone(current["route_id"])`,
`:407` `assertEqual(current["source_base"], self.state["observed_main_sha"])`, and `:405-406` forcing
`active_delivery.{route_id,branch,change_package,next_action}` to equal the same four values, plus `:411-415`
pinning `active_delivery.status` and its three sub-deliveries to the **published v2.0.16** record. Turning
`current_unreleased_change` into a live candidate therefore drags `active_delivery` with it — that is the
1900-line rewrite in disguise, and it would also falsify `:411`'s truthful
`source_delivered_operational_qualification_incomplete`.

### 4.3 Recommended minimal coherent state model

Keep every pinned slot honest, and record the new fact in an **unpinned additive key**:

1. `observed_main_sha` **stays `61a05da2…`** — merge has not happened, `:645` binds it to a tracked observation
   file, `:676` binds it to "not the published merge".
2. `observed_at` refreshes to a new `2026-09-15T…Z` timestamp (zero test churn). If the delivery slips to
   2026-09-16+, `test_project_state.py:78` is the one-line edit, and README/START_HERE must still carry
   `observed_main_sha` verbatim (`:633`).
3. `current_unreleased_change` keeps `status: no_new_release_candidate`, `identity: null`, `route_id: null`,
   `source_base: 61a05da…`; `record_scope` gains one clause naming this change package as local, unreleased,
   non-release-candidate work. `scope: []` may be filled (unpinned) if you want the epic named.
4. Add **one new top-level key** — e.g. `"pending_local_pr_candidates"` (sibling of `local_candidate`) recording
   `{change_id, route_id, branch, change_package, status: "local_pr_candidate", source_base, next_action,
   record_scope}`. No test enumerates top-level keys (§4 opening), so this is the cheapest truthful slot, and it
   is exactly the shape the repo already uses elsewhere (`retained_unresolved`, `delivered_since_historical_inventory`).
5. `work_inventory.active` stays `[]` (`:733`) and `open_pull_requests` stays `{13,15,33,64}` (`:729`) until the
   PR number is known; **post-merge** (or in the follow-up docs PR) update `retained_unresolved` `:771` (the
   epic stops being unresolved) and append `delivered_non_milestone_work` `:735-766` — both of which require the
   paired literal edits listed above. Doing those in the same commit as the merge-shaped docs is the recorded
   convention (`287b27a`, `02ac8c3` touched roadmap + PROJECT_STATE + README + START_HERE + test constants in one
   commit).
6. `README.md`/`START_HERE.md` `## Current state` / `## Current project state` may gain a sentence, but must keep
   `adaptive-trust-ci/verified@06ecf1c875bc`, `4694114`, `61a05da2bd0c9fb09db5307f53ebc99e4e94040d`, and must not
   contain `adaptive-trust-ci/verified@6737355947c2` (`:631-634`); START_HERE must keep `PR #19` + `delivered`
   without `open PRs … #19` (`:637-639`).
7. Prose landmines for any new sentence in README/START_HERE/QUICKSTART/roadmap/PROJECT_STATE (all
   `test_project_state.py:467-489` / `:536-544` and `test_structure.py:754-845`): the 7 "stale package/artifact"
   claims, `hard deadline is **2026-09-08`, `scripts/install_into.py --materialize-new …` must appear exactly
   **once** per file, and the installer-vocabulary set (`Linux`, `descriptor-relative`,
   `renameat2(RENAME_EXCHANGE`/`RENAME_NOREPLACE`, `fails closed`, `no fallback`, `--plan`,
   `` `--force` is rejected ``, `existing repositories are read-only`, `dependency advice`,
   `architecture/adoption.json`) must survive in README **and** QUICKSTART.
8. **Do not add a `## Unreleased` CHANGELOG heading** — `test_structure.py:278`
   `assertTrue(changelog.startswith("# Changelog\n\n## 2.0.16 — 2026-09-13\n"))`. Release-notes prose for an
   unreleased PR belongs in the change package (`release.md`) until a version bump PR, which must move VERSION,
   `adaptive_grok.__version__`, README H1/Identity, CHANGELOG head, roadmap `:41` and
   `test_structure.py:275-287` **together**.
9. New `.py` files need no packaging edit anywhere else: `manifest.is_included_relative_path` is denylist-based
   and **no test asserts an exact complete set of `schemas/` or `scripts/`**;
   `test_manifest_package.py:264-277` is subset-only (`assertEqual(required - rels, set())`).
10. Two gate-hygiene items the epic already satisfies: the 3 new schemas must be valid JSON (they become
    `_contracts` targets, `verification.py:614-624`) and none of the new files may match `secret-scan`'s
    `generic-secret` pattern (`:601-606`) — verified clean for all 8 new/ported files (relevant because
    `mistakes.md:932-937` records a fixture credential tripping exactly this).

## 5. Dark Factory Roadmap — what this PR should do

Premise correction: the roadmap has **62 unchecked** and **53 checked** boxes (1312 lines; all checkboxes are
top-level), not 113 unchecked. Only **four** sites in `test_structure.py` read it, and **no test counts
checkboxes**:

* `:16-29` + `:31-37` `ROOT_ENTRIES` two-way exact equality against `git ls-tree HEAD` (existence only; also
  forbids any new root-level path).
* `:92-100` one sentence plus a negative pin: `assertIn("Require independent review and explicit human approval
  before promotion to \`active\`.", roadmap)` and `assertNotIn("…review **or** explicit…")` — satisfied at
  `DARK_FACTORY_ROADMAP.md:551` (already `- [x]`).
* `:274-288` identity, incl. `assertIn("product version: 2.0.16 (latest published release: v2.0.16; published
  2026-09-13T22:04:08Z)", roadmap)` → `DARK_FACTORY_ROADMAP.md:41`.
* `:756` + `:839` `assertIn("bounded abstract interpreter", roadmap.lower())`.

The one structural roadmap parser is elsewhere: `test_project_state.py:678-725`
(`^# M4 —.*?\n(.*?)(?=^---\n\n# M5 —)`, exactly **two** ```text fences in `## Factory task state machine`, 10
ordered primary + 5 exceptional `TaskStatus` values, and
`assertNotRegex(checked_items, r"GitHub|open factory PR|PR age")` over `## Work items`). Consequence:
checking `- [ ]` → `- [x]` is allowed **everywhere except `DARK_FACTORY_ROADMAP.md:667` and `:675`** (both contain
`GitHub`), and `:666`/`:669`/`:551` must not be unchecked.

Repo convention says boxes are not the status channel: the three most recent roadmap commits
(`02ac8c3`, `6d8f6ab`, `287b27a`) changed **zero** checkboxes; they moved the `## 2` baseline block, the
`### 3.4 Dated delivery history` bullets, `## 4` gap-analysis rows and per-milestone `Current status:` lines.
`## 13. Roadmap governance` (`:1281-1294`) states "Do not rewrite history to make the roadmap appear correct.
Preserve the evidence and update the plan", and `:680` defines a checked box as *locally implemented behavior
only*, explicitly disclaiming review/Trust CI/delivery/activation. M5/M6/M7/M9 are fully implemented on `main`
and still 100 % unchecked — the drift is pre-existing, deliberate, and orthogonal to this epic.

Grep result for this epic's vocabulary inside milestone items: **nothing to check off.** Matches are
`:456` (M2 fitness line), `:555` (M3 "canonical examples for HTTP adapters"), `:697` (M5 status prose),
`:1216-1217` (§11 instructions mentioning `docs/superpowers/…`), plus `:98` PR-inventory prose. There is no
`backlog`/`future`/`out of scope` section and no milestone covering external-workflow ingestion.

**Bounded recommendation for THIS PR** (and nothing more): add one dated bullet under
`### 3.4 Dated delivery history — through 2026-09-15` (`:100-113`) recording the adapters as an opt-in,
non-authoritative compiler with its change-package id and gate binding, and optionally one `## 4` gap-analysis
row (`:114-141`). Zero box toggles, zero heading edits, `:41`/`:551`/"bounded abstract interpreter" untouched,
M4 block untouched, no new root entry. **Leave the M0-M9 box reconciliation to a dedicated docs PR** — fixing it
requires deciding what a checkbox means relative to `:680` and `## 13`, i.e. a roadmap-governance change of
exactly the kind §13 says needs security + architecture review; bundling it here would put a 60-line semantic
governance rewrite inside a compiler PR's review window.

## 6. Rollout / rollback shape and ordering

### 6.1 File groups

* **A. Core authority (protected paths)** — `.grok-stack/adaptive_grok/workflow_artifacts.py` (new, 1 703 lines),
  `.grok-stack/adaptive_grok/verification.py` (5 touch points, ~85 lines),
  `.grok-stack/adaptive_grok/receipts.py` (2 hunks, ~120 lines).
* **B. Contracts + CLI (unprotected paths)** — 3× `schemas/workflow-*.schema.json`, `scripts/grok_artifacts.py`
  (158 lines).
* **C. Model + projections (unprotected)** — `architecture/system.yaml` (+~185 lines), 5×
  `architecture/generated/*.mmd` (+20 lines).
* **D. Distribution** — `scripts/install_into.py`, `.grok-stack/config/managed.json`,
  `tests/test_installer.py`.
* **E. Tests** — 3× new `tests/test_workflow_artifacts*.py` (1 637 lines), `tests/test_verification_doctor.py`,
  `tests/test_architecture_model.py`, `tests/test_structure.py`.
* **F. Governance + current state** — `decisions.md`, `mistakes.md` (3 entries, §2.3), `README.md`,
  `QUICKSTART.md`, `DARK_FACTORY_ROADMAP.md` (prose only, §5), `PROJECT_STATE.json` (§4.3),
  `docs/superpowers/{specs,plans}/2026-08-30-workflow-artifact-adapters*.md`,
  `engineering/changes/20260915-…-1b0c02/**` (currently **untracked** — `git status: ?? …`; must be added or
  `active-spec-missing` fails at `verification.py:660-661`).

Groups A/D/E touch protected paths (`.grok-stack/**`, `scripts/grok_*.py`, `tests/test_*.py`, `decisions.md`,
`mistakes.md`, `README.md`) → route-selected protected-write grants are required; B/C/F(roadmap) are not protected.

### 6.2 Commit splitting: one PR, several commits — not stacked

Single coherent PR. The three-way split (compiler / model / docs-state) is commit-level only:
`A+B` (contracts+core, tests green together), `C+D+E` (model, packaging, verification wiring), `F` (governance +
current state). Do **not** stack into sequential PRs: every slice appends to the same shared files
(`decisions.md`, `mistakes.md`, `MANAGED_FILES`, `managed.json`, `system.yaml`, `test_structure.py:required`), and
`decisions.md:596-600` records that this exact shape destroyed a stacked chain's commit identities and forced an
all-or-nothing union landing; `DARK_FACTORY_ROADMAP.md:1216-1222` (§11 steps 6-8) prescribes many commits with
"one coherent purpose per commit" inside one PR, not one PR per task. Also a stacked slice cannot be merged
independently anyway: A without C leaves orphan source files unowned (`undeclared_source`,
`architecture.py:972-1032`) and C without A references contracts whose files are missing (`:1323-1324`).

### 6.3 Ordering constraints from receipt fingerprints (hard)

`tree_fingerprint = f(HEAD, changed tracked files)`; `write_receipt` recomputes before/after and raises
`'repository, spec, architecture, or governance changed while receipt was written'` (`:540-550`), and
`validate_evidence` flags `'{kind}: stale after repository changes'` (`:575-576`) plus spec/architecture/governance
binding staleness (`:577-604`). Receipts are gitignored (`.gitignore:2`), reports are tracked. Therefore:

1. **Every tracked write first, all of it** — A→F, including the change-package `change-spec.yaml` and every
   `evidence/*.md` (each is a tracked write). `python3 -m unittest discover -s tests` and
   `diagram --check` must already be green at this point.
2. **Commit**, so HEAD is the tested tree (receipts bind HEAD + dirty files; an uncommitted product file makes the
   receipt stale immediately, and the App-owned gate needs the exact PR head SHA anyway).
3. `git diff --check <base>` and `git diff --cached --check` clean before step 4 — `git-diff-check`
   (`verification.py:505-561`) is the first check and now also carries the range-selection findings
   (`:520-533`), so a malformed `route.base_commit` (must be exact 40-hex, `:292-300`) fails the whole run.
   Current route `base_commit = 7b147366a1f9…` is well-formed.
4. `GROK_VERIFY_CAPABILITY=repository-sandbox python3 scripts/grok_verify.py --mode pr` (the recorded runner-capability
   decision, `decisions.md:18-20`) → writes the `verification` receipt **only if** `source_stable` and
   governance passed (`:1035-1042`).
5. Dispatch the three route-selected reviewers (AFTER implementation+verification; read-only; never the
   implementer), then **write their report files as tracked writes**. Because that is a tracked write, re-run
   step 4 so the `verification` receipt binds the final tree, then record the three review receipts:
   `python3 scripts/grok_review.py code_review --status pass --report engineering/changes/<id>/evidence/code-review.md`
   (and `test_review`, `security_review`). `grok_review.py:20-24` requires the report path to exist and stores
   only the path string — it does not write into the tree, so it does not invalidate the other receipts.
6. Nothing tracked may change after step 5 (including amending a report). Push the branch, open the PR, then wait
   for the App-owned `adaptive-trust-ci/verified@<policy-sha12>` check on the exact head SHA. Local receipts and any
   delegated grant are evidence only, never merge authority (AGENTS.md).
7. **Rollback:** remove/rename `workflow/manifest.json` → the check returns `skip` and
   `{"configured": false, "status": "not_configured"}` with historical packages unaffected; full rollback is a
   plain revert of the PR merge commit — no migration, no runtime state, no cache key, and native
   `change-spec.yaml`/architecture/governance/route/Trust CI artifacts are untouched by construction. Forward
   recovery for a partially applied revert: `architecture/generated/*.mmd` are regenerable
   (`grok_architecture.py diagram --json`) and `MANIFEST.sha256`/`dist/` are gitignored, so no manual cleanup
   is ever required.

### 6.4 Open items for the write owner

1. `.specify` vs `.superpowers` for `NODE-WORKFLOW-ARTIFACT-SOURCES` (§3.3.2) — decision needed before the model
   commit; it determines whether `ROOT_ENTRIES` is touched.
2. Whether to port `SRC:tests/test_workflow_artifacts_adversarial.py`'s CAS/race cases unchanged: they exercise
   `renameat2(RENAME_EXCHANGE)` paths that this host may or may not expose; keep them capability-guarded as the
   existing `factory-postgres-exit` skip does (`verification.py:900-910`).
3. Whether `QUICKSTART.md` gains the `grok_artifacts.py` command — if so it must not duplicate the
   `--materialize-new` invocation (`test_structure.py:754-845`).
