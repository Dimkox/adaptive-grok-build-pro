# Issue 165 integration analysis

Route `2dfd5804553e`; role `integration_architect`; source branch `fix/issue-165-interruption-status`; observed HEAD `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`. This is read-only source analysis, not test, review, or merge evidence. No test, lint, compilation, Docker, commit, receipt, or external operation was run. Only this assigned report was written.

## Recommendation

Add a bounded package inspector and an explicitly observational Git snapshot to the existing status response. Reuse the same inspection result for concise Stop warnings and the review CLI's preflight. Keep package completeness, current receipt validity, and external merge eligibility separate: none of the new fields can authorize publication or change the receipt schema.

Keep all checkpoint writes in `start_change()` and the existing `transition()` mutation path. Status must never write a checkpoint, repair a package, create runtime directories, invalidate receipts, transition a route, fetch refs, or run verification. A same-worktree observation cannot prove a crash or find uncommitted work on another host.

## Established interfaces and gaps

| Surface | Actual implementation | Integration implication |
| --- | --- | --- |
| `scripts/grok_status.py:15` | Prints `route`, `change`, `agents`, `evidence_gaps`; the last field delegates to `validate_evidence`. | Preserve all four fields and their meanings. Add fields rather than folding package findings into receipt gaps. No strict status JSON consumer/schema was found in source; Makefile, README and delivery skills invoke the CLI. |
| `.grok-stack/adaptive_grok/state.py:93` and `:309` | State getter paths call `runtime_dir()`. | Reads are not completely side-effect-free today: `util.py:43` calls `mkdir`. A fresh-clone nonmutation test must remove the runtime directory entirely, not merely compare tracked files. |
| `.grok-stack/adaptive_grok/change.py:32` | Creates generated v2 spec, renders template tokens, writes draft state, active pointer, and route; the existing-package path returns early. | Capture initial branch/HEAD and declared evidence obligations only when creating a new package. Repeated start must preserve previous rows and must not rewrite existing package content. |
| `.grok-stack/adaptive_grok/change.py:89` | Validates transition against `TRANSITIONS`, appends state history, writes state, then updates the route. | Append the first implementation checkpoint here, after validating the transition. Preserve valid/invalid transitions and do not use a status read as a mutation trigger. |
| `.grok-stack/adaptive_grok/spec.py:746` | Gate mode rejects unknown target/metric and empty acceptance criteria; generated drafts deliberately contain these values (`:803`). | Draft incompleteness is expected. Use typed checks with stage-aware severity instead of making every draft invalid or calling all gate checks indiscriminately. The path API accepts `gate=False`; the in-memory adapter instead uses `schema_only`. |
| `.grok-stack/templates/change/evidence/README.md` | Only explains that reports are local and machine receipts are fingerprint-bound. | Extend the new-package template with ID, route, branch/HEAD, observation time, draft/implementation-not-started state, and explicit obligations. Keep the locality notice. |
| `scripts/grok_review.py:20` | Checks only report existence, then calls `write_receipt`. | Inspect before writing a passing review receipt when the package stage requires completeness. A failing review must remain recordable. Do not require every review receipt to exist before recording the first one. |
| `.grok/hooks/stop_gate.py:32` | Returns early without route/required evidence; otherwise warns on gaps, or marks the route completed. | Add package/work-state findings without making Stop blocking. Inspect an active package even if the route's receipt list is empty. Preserve existing evidence-gap text and receipt validation. |
| `.grok-stack/adaptive_grok/receipts.py:502` / `:643` | Binds and validates route, full tree, spec/criteria, architecture, and governance; rereads before receipt write. | Retain this canonical implementation and all staleness/binding checks. The inspector cannot replace it with a shorter status predicate. |

`tests/test_change_receipts.py:705` currently demonstrates that a generated draft plus fast verification and review receipts can have zero `evidence_gaps`. That does not imply a gate-complete package. This is exactly why additive package findings must remain visible alongside existing receipt results.

## Proposed additive status contract

The controller can choose final names, but freeze the following meanings before implementation:

- Preserve `route`, `change`, `agents`, `evidence_gaps` byte-for-byte in shape and semantic role.
- Add `package_completeness` with a bounded status such as `complete`, `draft`, `incomplete`, or `unknown`, package identity, current durable stage, and structured findings.
- Add the issue-requested `package_incomplete` list as the findings list, or choose one canonical list and document it. Do not maintain independent computations under two names.
- Each finding should include a stable `code`, repository-relative `path`, optional field/line, short message, and severity. Consumers should use codes, not parse prose. Never include entire document content or raw subprocess stderr.
- Add one `work_state` snapshot: `observed_at`, Git availability, branch/detached status, exact HEAD, route base, diagnostic base and source, `commits_ahead` (integer or null), dirty product paths, and a tri-state zero-ahead dirty observation. A failed/unknown count is null, never zero.
- Distinguish `no_active_package`, missing pointed-to package, malformed state/spec, and inaccessible/unsafe file. None is a successful completeness result. A no-route/fresh-clone response remains valid JSON and does not fabricate runtime state.
- The top-level response is an observation, not `merge_ready`. `complete` describes the bounded package fields inspected, not test success, current external checks, or persistence on a remote host.

Use the durable package's `state.json` for stage, not the runtime route's `status`: Stop currently writes runtime `completed`, which is not a `change.py` transition state. Compare change IDs/route IDs and diagnose mismatch rather than silently selecting another package.

The current worktree is stacked: route base is `90078959ff816068af374ad42f4bb80fdbaec866`, while observed starting HEAD is `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`. Preserve the route base for its existing authority/binding purpose. A newly recorded initial checkpoint HEAD may serve as a separately named diagnostic base (`base_source=initial_checkpoint`), with both values exposed. For an existing package without that checkpoint, use an available validated route base with `base_source=route`; if it is absent/unavailable, report unknown. Never choose the current HEAD as a fallback that manufactures a zero-ahead result.

Dirty paths must mean working-tree/index/untracked product changes, not all commits since the route base and not package paperwork. Prefer a documented conservative rule excluding runtime noise and `engineering/changes/**`; do not exclude product documentation/configuration simply because it is Markdown or JSON. Keep this diagnostic classification independent of receipt fingerprints, which must still include every non-runtime package write. Count/depth/output limits must produce an explicit partial/unknown finding rather than silently claiming there are no other paths.

## Completeness and mandatory evidence

Check the actual typed objective fields and acceptance-criteria collection. Treat the generated draft's unknown objective/empty criteria as expected draft work; they become actionable once the durable stage requires scope. Do not extend this issue into new red-risk policy or make cancelled/historical packages pass new delivery gates retroactively.

Limit text checks to known template syntax in current normative package files. An exact unchecked `Given ..., when ..., then ...` row, unexpanded template tokens, or a bare `<!--RUNTABLE-->` in current evidence are useful signals. Plain prose mentioning `TODO` or `TBD` is not. Exclude quoted/fenced historical examples before matching; a historical failure or quoted marker must not contaminate an otherwise current report.

There is currently no typed domain-run obligation model. `route.required_evidence` enumerates receipt kinds only; it does not declare the four PostgreSQL runs from the historical incident. Do not infer every obligation from an arbitrary heading or treat any table row as proof of a run.

A small additive local checkpoint/obligation structure, rendered into the evidence README, is safer than broad prose heuristics. Route-selected receipt kinds can be initialized as `not_run` with the reason `implementation not started`; any extra domain run must be explicitly declared. If such a structure is introduced, freeze a bounded vocabulary and require identity plus either a measured run/report reference or `not_run` plus a nonblank reason. Merely naming an existing document is not a measured run row. Preserve the distinction between a recorded failed run and a passing one.

The explicit `not_run` record satisfies accounting: a handoff can see what remains. It never satisfies `validate_evidence`, a verifier pass, an external approval, or a review's claim that execution succeeded. Do not automatically copy effective receipt status back into tracked checkpoint metadata after receipt creation: that write would immediately stale the receipt. Existing packages without new metadata should remain inspectable using their current spec and exact known placeholders; do not silently rewrite them.

## Transition, review, and Stop integration

1. At new-package creation, record an initial observation and render it in `evidence/README.md`. For no Git/unborn/detached cases record explicit unknown/detached state rather than failing scaffolding or inventing a branch.
2. At the first valid transition to `implementing`, append a WIP observation containing change/route identity, time, branch/HEAD, and dirty-product state. Preserve the initial snapshot. A later `blocked -> implementing` or `reviewing -> implementing` should not overwrite history or duplicate the initial-start record accidentally; select and test the intended append policy.
3. Keep failure semantics honest: a checkpoint write failure must be surfaced, not swallowed while reporting a successful durable transition. Avoid claiming multi-file atomicity unless it exists. Make a retry safe if state and README differ after an interrupted write.
4. Review preflight may reject `--status pass` for required-stage package/mandatory-evidence completeness errors before any receipt file is created or replaced. `--status fail` remains recordable. The zero-ahead dirty observation is a warning, since ordinary precommit implementation can legitimately have that shape.
5. Do not call `validate_evidence` over all required receipt kinds as a prerequisite to recording any one review: that would deadlock the first review on itself and subsequent reviews. If enforcing a prerequisite verification receipt, validate that specific existing prerequisite without changing canonical receipt semantics.
6. Stop must always remain a nonblocking warning surface: exit 0 and no `decision=block`. A current-package completeness error must not be hidden by current local receipts or a missing `required_evidence` list. A diagnostic must never automatically transition the durable package, publish WIP, or grant production authority.
7. Finish all checkpoint/README/state writes before the final verification and receipt wave. `decisions.md:214` and `mistakes.md:223` record that the full-tree fingerprint includes package state and reports; no exclusion should be added to avoid that established rule.

## Nonmutation and bounded I/O

The mutation inventory must cover more than calls named `write`:

- State readers currently create runtime directories. Add a pure read path or make path construction pure while keeping directory creation in actual writers. Do not use the approval validator, which can prune expired approvals, as a status helper.
- Python imports can create `__pycache__`. For a strict CLI no-write claim, set `sys.dont_write_bytecode` before adaptive imports, or use an equivalent always-on CLI guarantee. Tests must not rely only on an environment flag supplied by the test harness.
- Ordinary Git status may refresh `.git/index`. Use optional locks disabled and a bounded, sanitized Git reader; `architecture_diff.py:159` already sets `GIT_OPTIONAL_LOCKS=0` and disables fsmonitor/hooks, and `:211` caps output/time. Never fetch inside status.
- Use NUL-delimited Git output; `util.changed_files()` uses line splitting and stripping and therefore is not a lossless parser for whitespace/newline paths or rename records.
- Do not recurse through sibling worktrees or arbitrary package path values. Validate the active path under `engineering/changes`, reject traversal and symlink ancestors/leaves, and inspect only bounded regular files. Use descriptor-based bounded readers rather than `Path.rglob()` plus follow-symlink reads.
- `spec.load_spec()` protects the leaf, but its path-only reader is not sufficient to prohibit an ancestor symlink. The descriptor-relative pattern in `architecture._read_regular_bytes()` and `receipts.get_receipt()` shows the repository's existing boundary.
- Oversized, nonregular, malformed, permission-denied, raced, and unsupported-read inputs become bounded diagnostic codes, not silent omission or a traceback. Do not read secrets, arbitrary raw logs, or the bytes of changed product files merely to list their paths.

## Exact fixture coverage to add

These fixtures belong in focused status/inspector tests plus the existing transition/hook tests. They are proposed coverage, not executed evidence.

| Fixture | Required assertion |
| --- | --- |
| Complete current v2 package with real scoped objective/criteria and declared recorded evidence | No package-incomplete findings; legacy four JSON fields remain available; local receipt gaps are independently preserved. |
| Fresh `start_change` draft | Label `draft`, expose expected unfinished fields without calling the package corrupt, record initial checkpoint/explicit `not_run` reasons, and keep receipt obligations unsatisfied. |
| Same scaffold after a scoped/approved/implementing transition | Unknown target/metric and empty criteria receive stable required-stage findings. |
| Known bare template marker and unchecked exact Given/when/then row | Findings identify the current relative file and marker/field. |
| Quoted/fenced marker or TODO/TBD discussion in historical evidence | No template finding; nearby real current marker still detected. |
| Mandatory evidence: absent record, empty table, bare marker, `not_run` without reason | Missing/invalid accounting finding; none is a measured pass. |
| Mandatory evidence: explicit `not_run` plus reason, recorded failed run, recorded passing run | Accounting is distinguished from success; failed/not-run cases cannot satisfy canonical passing receipt validity. |
| Missing state/spec/README, duplicate-key/malformed/oversized spec, invalid stage or mismatched ID | Valid bounded status JSON with the appropriate missing/invalid finding; no package rewrite. |
| Package path outside root, package/ancestor/evidence symlink, FIFO/nonregular file, mocked permission failure | No destination content read, no blocking FIFO read, no leak in output, and explicit unsafe/unavailable findings. |
| Exact base equals HEAD, with a tracked modification, staged modification, deletion, and untracked product file | `commits_ahead=0`, accurate product paths, candidate diagnostic true, no assertion of a crash. |
| Only active package reports/state are dirty | No dirty-product candidate; canonical full-tree receipt freshness still observes these writes. |
| One commit ahead plus a dirty product file | Dirty state remains visible but zero-ahead candidate is false. |
| Stacked branch with initial checkpoint newer than route base | Expose both bases; diagnostic count is zero from the named checkpoint while route base stays unchanged. |
| Missing/unavailable base, no Git, unborn HEAD, detached HEAD, Git timeout/malformed output | Unknown counts remain null; detached can retain a known exact HEAD; no fallback count of zero. |
| Filenames containing spaces, tabs/newlines, Unicode, and rename source/destination | NUL-safe path list without truncation, quoting ambiguity, or false product classification. |
| No runtime directory, existing populated runtime, and receipt-enabled status | Run the actual CLI twice; compare paths and bytes (including ignored runtime, `.git/index`, and bytecode paths) before/after; only stdout's observation time may vary. No tests/verifier/network subprocesses are launched. |
| Existing package `start_change` invoked twice | Existing README/checkpoints/history bytes are preserved and no duplicate creation observation is appended. |
| First valid implementation transition and reentry after blocked/reviewing | Correct single first-start checkpoint policy, preserved initial row, and appended/preserved transition history; invalid transitions mutate nothing. |
| Review pass with required-stage incomplete mandatory evidence | Nonzero refusal before receipt creation/overwrite. Review fail remains recordable; a complete package permits the existing receipt writer. |
| Stop with incomplete package and current receipts; Stop with no receipt obligations | Emits concise nonblocking diagnostic and never claims absence of findings from receipt freshness alone. |

Retain existing tests for `ChangeTests.test_valid_transitions`, `test_invalid_transition_is_rejected`, `ReceiptTests.test_receipt_stales_on_contract_route_base_and_git_head_changes`, unsafe receipt reads, `HookTests.test_stop_warns_without_evidence`, and `test_stop_allows_current_evidence`. Update only the intended expectation of fixtures that now opt into active-package completeness; receipt-only legacy consumers must keep their current compatibility.

## Delivery boundary and durable learning

No remote connector, service, schema migration, daemon, GitHub Action, or deployment-policy change is needed. Rollback is the source revert of the new inspector/wiring/template changes; old status consumers can ignore additive fields, and historical packages are left unchanged. Publication still requires exact delegated actions and external Trust CI on the exact PR SHA.

Suggested shared-memory fact for the controller/sole writer to record if the implementation validates it: read paths need their own no-write fixture because runtime directory constructors, Python bytecode, and Git index refresh can mutate a nominally observational CLI. Package completeness is local accounting and must remain independent of current receipt and external merge authority.
