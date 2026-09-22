# Integration analysis — issues #35 #36 #39 #48 #73 #121 #122 #167

## Scope and recommendation

These issues are related by verification trust and delivery ergonomics, but they are not one safe implementation seam. Use one successor PR only if the write owner keeps changes in four bounded slices with independent tests and no production/deployment side effects; otherwise split into two PRs (verifier/guard correctness and documentation/evidence policy). The external Trust CI check remains the merge authority for the final exact head.

Recommended order:

1. **Shell/evidence correctness (#35, #36, #48):** add or update a single reusable shell-command recording/validation helper where the existing verifier scripts own these behaviors. Every multi-file `bash -n` call must iterate operands; command status must be captured with `cmd || code=$?`; captured output must be non-empty before equality assertions; environment discovery must distinguish not-found from malformed. Add tests with deliberately broken second operands, command-not-found, SIGPIPE/`pipefail`, empty discovery, and assignment-before-control-builtin fixtures.
2. **Lint scope (#39):** locate the actual JS lint entry point before editing. Scope interactive lint to tracked/changed files and exclude generated coverage, worktrees, release scratch, and nested repositories; retain whole-tree lint only for deep verification. Add a fixture proving an out-of-tree file is excluded and report the processed-file count. Do not make this a broad workspace cleanup.
3. **Evidence naming and policy wording (#73, #122):** treat committed SHA digests as non-secrets by using neutral field names such as `grant_binding_digest`, and clearly label `trust-ci/config/policy.example.json` as illustrative rather than deployed policy. Add tests/docs that bind the wording to the deployed policy epoch without claiming repository files can change server policy. Do not add allow-list rules that could suppress real findings globally.
4. **Runtime evidence (#121):** choose the low-risk option 2 unless the write owner finds an existing durable observation API: downgrade provider-probe leaves to explicitly attested/non-re-derivable, separate them from the durable pilot job, and preserve job IDs/usage fields without implying a re-derivable database row. A durable probe row is a data/behavior change requiring schema migration and separate approval; do not invent one in this bugfix batch.
5. **Static side-project verification (#167):** the repository already contains the requested focused-scope wording in `AGENTS.md` lines 178–181. Verify whether this is merged/current and add only missing runner dispatch logic/tests. The focused test command should run first for diffs confined to `side-projects/seo-landings/**` and its focused tests; full `grok_verify --mode pr` remains required when runtime, contracts, Trust CI, packages, architecture, or workflow files change. This must not weaken the external App-owned merge gate.

## Dependency and conflict map

| Issue | Product seam | Depends on | Conflict risk | Acceptance evidence |
|---|---|---|---|---|
| #35 | Shell syntax-check dispatch | existing verifier command runner | medium: command construction tests may encode old string | each operand parsed; broken later file fails; zero-file input fails |
| #36 | Shell status recorder | #35 helper if shared | high: changing recorder can affect all gate result JSON | failing command preserves nonzero code, startup failure is nonzero, elapsed/output evidence present |
| #39 | JS lint file selection | verifier/lint config entry point | medium: generated/worktree fixtures | tracked/changed-file count bounded; generated and sibling worktree files excluded |
| #48 | environment guard scripts | #35/#36 only if shared shell helper | high: user-level kit may not be in this repository | only implement repository-owned equivalent; otherwise record external boundary and add characterization docs/tests |
| #73 | evidence key naming/triage docs | #122 terminology | low to medium: historical JSON/tests may assert keys | no secret-like key for 64-hex digest; GitGuardian false-positive class documented without suppressing real secrets |
| #121 | runtime observation dossier | none; production/provider boundary | high: schema/API/credential/live-call scope | wording distinguishes durable pilot row from attested provider probe; no authenticated call in tests |
| #122 | policy example/runbook | #73 naming/docs only | medium: policy example structure tests | example explicitly illustrative; deployed epoch source and non-authority are clear |
| #167 | route-selected static verification | existing `grok_verify` and AGENTS contract | high: must not alter full gate semantics | focused landing contract passes; runtime-touching diff still selects full PR verifier |

## Integration procedure

* Start from the route base `130ce4a42d9f9bbd1b56772d40b19ae530283205`; fetch before final rebase.
* One `general_implementer` owns source changes. Analysis/review agents remain read-only.
* Before implementation, capture RED tests or characterization tests for each changed behavior. Run focused tests in parallel only when they do not share mutable worktrees or external services.
* Keep all generated reports, receipts, and review artifacts out of the product diff until the source/test tree is frozen; otherwise `source-stability` can invalidate the gate.
* Run `git diff --check`, compile/static checks, then the route-required `python3 scripts/grok_verify.py --mode pr` exactly once on the frozen candidate. If it fails, repair the named owner and rerun only after the repair.
* Run independent code and test reviews after verification, record both under this package, and bind the receipts to the final tree fingerprint.
* Publish one PR only after the local evidence is current. Wait for `adaptive-trust-ci/verified@06ecf1c875bc` on the exact PR head before merge or issue closure.

## Explicit boundaries

#48 may describe an external user-level kit and #121 may describe an externally observed runtime. If no repository-owned implementation seam exists, the correct result is a durable finding/characterization test or documentation update that states the boundary; a fabricated core fix would not close the issue. #73 and #122 concern evidence semantics and deployed-policy interpretation, so local example changes cannot establish or alter Trust CI authority. #167 changes local preflight selection only and cannot bypass protected branch checks.

## Validation matrix

- #35/#36/#48: shell fixture tests plus affected verifier tests; assert nonzero propagation and evidence presence.
- #39: lint discovery/scoping tests and one bounded command against a fixture worktree.
- #73/#122: JSON/schema/documentation tests; inspect GitGuardian only as informational.
- #121: dossier consistency tests proving pilot and probe IDs/usage are distinct and wording is downgraded.
- #167: focused side-project contract tests first; then route verifier selection tests; full PR verifier for any wider diff.
- Final: `python3 scripts/grok_verify.py --mode pr`, code review, test review, exact-head App-owned check.
