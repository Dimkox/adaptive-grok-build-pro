# Runner capacity/platform integration analysis

Route `45e0cc3b5da0`; inspected source `839d3aa26bc90417424d814ee48d8b5cd3be367e`; retained PR135 source `7a7851af5d11e8ce5c3af23ab46214ae7ae4cdc8`.
Static analysis only: Git/source/history/configuration reads; no tests, compile, lint, Docker, capacity probes, external writes or deployed changes. This is design evidence, not verification or merge authority.

## Retained source and smallest successor

- Comparing PR135's runner and runner-test files against current main produces exactly the inverse of its original product patch: runner +9/-2 lines and tests +80 lines. No additional drift exists in those two files between the retained patch parent and inspected main.
- Carry only the product hunk and relevant tests, retaining the original source SHA as provenance. The historical change package and its passing receipts refer to another base/tree and cannot qualify this successor.
- The runner hunk adds `_parallel_process_cleanup_supported()`, returning `os.name == 'posix'`, and makes `select_engine()` degrade positive requests when dependencies or safe process-group cleanup are unavailable. Keep `_pytest_command()`'s POSIX refusal as a defensive guard.
- Three retained regressions cover emulated non-POSIX Core/Trust dispatch and CLI disclosure, POSIX selection, and measured Core fallback that consults only the coverage pin. This fixes selection before launch; it does not catch a failed run and rerun it serially.
- Their Windows condition is a patched capability seam on POSIX, not native Windows execution. Do not change global `os.name` during fixture construction; `pathlib` and subprocess behavior would also change.

## Consumers and frozen compatibility

| Boundary | Existing contract to preserve |
| --- | --- |
| `selected_workers(root)` | Returns `None` without opt-in, `0` for serial/opted-in child execution, or a selected positive count. Keep this API. |
| `.grok-test-runner.json` | Closed schema v1 with exactly `schema_version` and `workers`; workers is integer 0–64 or `auto`; duplicate/unknown keys, symlinks, nonregular/oversized files and malformed values fail. |
| `GROK_TEST_WORKERS` | Validated environment override wins; explicit supported-platform integers remain exact, independent of a low cgroup quota. Child recursion protection remains authoritative. |
| Linux `auto` | Change only capacity selection: intersect known affinity/CPU capacity with actual applicable cgroup limits, retain minimum one and existing ceiling 28, and document unreadable/malformed/unlimited behavior. |
| Other platforms | Preserve existing non-POSIX `auto` serial selection and POSIX support; explicit positive non-POSIX counts degrade through shared engine selection. Linux-specific quota discovery must not become a requirement elsewhere. |
| `verification._python()` | No opt-in retains the legacy sequential path. A project marker plus available pytest selects the separate existing consumer pytest path before the optional Core runner; do not broaden this task into consumer-runner routing. |
| `run_core_tests()` | Select engine before checking its dependencies; `worksteal` only for xdist. PR/release serial fallback still runs unittest under pinned coverage with `.coveragerc`. |
| `run_trust_tests()` / module CLI | Separate Trust imports/cwd; xdist `loadfile` keeps a file together. CLI uses the same selector and returns a failing exit on unsuccessful execution. |

The repository ships no root opt-in file. Do not add one, a root project marker, auto-installation, dependency upgrades, PID heuristics or a new default profile. Keep the current optional tool pins and source coverage floor unchanged.

## Reports, execution and trust

- `_python()` records `python-unittest` and `coverage` check names, command, actual workers, bounded output, duration, versions JSON and coverage metadata. `requested_workers` currently means the numeric result of `selected_workers()` before engine degradation; for `auto` it is already resolved, not the literal configuration string. Preserve that meaning.
- Core summaries label the effective backend using `core.workers`; the versions JSON discloses `engine=unittest-degraded`. Trust CLI prints both requested/effective counts and engine. Capacity limits must not cause a serial run to be reported as xdist.
- Preserve `CoreTestRun`, `ProcessResult`, schema v1 and report/receipt `pass|fail` status semantics. Do not introduce an `incomplete` status or let malformed capacity data suppress genuine configuration, pin, collection, test or coverage failures.
- Preserve unittest `test*.py` discovery, explicit plugin loading, cleared inherited pytest/coverage selection, `_GROK_TEST_CHILD`, fresh invocation-owned coverage and no retry after failed execution. Missing/corrupt/partial coverage, failed tests and lost worker data remain failures.
- Keep cancellation, timeout, output bounding and owned descendant cleanup unchanged. A CPU quota is not proof that the host can create a requested number of processes.
- `verify()` fingerprints before/after checks and records a receipt only for a stable source tree; the CLI derives exit status from the report. No change is needed in `verification.py`, `receipts.py` or `scripts/grok_verify.py` for this slice.
- The repository policy example has direct root/Trust unittest commands plus repository verification; this source repair does not change its command matrix, deployed image, policy or holdout. `JobRunner.process()` attaches checks to `job.head_sha` and rejects policy-digest mismatch: local success is never the App-owned exact-SHA result.

## Adjacent verifier work

| Pending issue | Integration boundary |
| --- | --- |
| #59 lock immutability | Its disposable harness/uv command selection must remain read-only and use locked dependencies. This worker-selector change neither resolves nor works around lock mutation; do not relax source-stability to accommodate it. |
| #51 discovery breadth | Full factory/delivery discovery and independent PostgreSQL evidence belong to verifier command selection. Core/Trust worker counts do not establish factory coverage, and database skips cannot become passes. |
| #169 applicability | Product inventory and required coverage-completeness belong to verifier/report details. Keep existing enums compatible; changing worker/engine choice is not proof that the changed product was checked. |
| #167 static landing profile | Its complete changed-file inventory, focused content checks and fail-toward-full eligibility are independent. Do not add skips, selection shortcuts or a local profile to this runner repair. |

These boundaries come from research route `d54d3afd1c92` packets `design-verifier-lock-and-discovery-59-51.md`, `design-consumer-coverage-157-169.md`, and the copied `prior-research-capacity.md`. Serialize later edits to `verification.py`; this slice can stay in `python_test_runner.py` and its tests.

## Fresh evidence and supersession sequence

1. Reproduce the remaining quota and platform defects on current source with deterministic inputs; historical PR33 failures are not current reproduction evidence.
2. Make auto tests independent of host state by patching the capacity-reading seam. Cover affinity 22/quota 2, positive fractional quota, unlimited/missing/malformed data, supported v1/v2 mappings, explicit integers unaffected, no opt-in and opted-in child serial behavior.
3. Port the retained platform cases and exercise both Core and Trust paths with importable extras. Verify measured fallback produces current coverage, only coverage pins are required there, and supported POSIX xdist keeps strict pins. Preserve nearby collection, failure, cleanup and coverage tests.
4. The writer/coordinator runs focused RED/GREEN and full `grok_verify --mode pr` under the exclusive CPU slot, then obtains all three route reviews on the stable candidate. Refresh receipts after any source or metadata changes that invalidate their fingerprint.
5. Deliver a successor PR naming issues62/118 and PR135 provenance. Obtain the required App-owned policy-epoch check and any signed scopes for its exact current head/base before merge; retained PR135 observations do not transfer.
6. Only after successor delivery, record the successor merge/check identities and close PR135 as superseded with a direct successor link. Preserve its branch/history and do not claim a deployed capacity or native Windows outcome from this source delivery.

Recovery remains the existing explicit serial setting (`GROK_TEST_WORKERS=0`) or a reviewed source revert. Neither requires changing deployed Trust CI state.
