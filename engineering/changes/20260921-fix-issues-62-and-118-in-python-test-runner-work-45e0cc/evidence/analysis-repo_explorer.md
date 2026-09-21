# Runner capacity and platform source map

Route: `45e0cc3b5da0`; selected analysis role: `repo_explorer`.
Inspected source: `839d3aa26bc90417424d814ee48d8b5cd3be367e`.
Retained comparison: PR135 source `7a7851af5d11e8ce5c3af23ab46214ae7ae4cdc8`.
Method: static file, Git-history, and diff inspection only; no tests, compilation,
lint, Docker, host-capacity probes, or external operations were performed.
Read AGENTS, START_HERE, relevant PROJECT_STATE handoffs, active route, brief,
prior capacity research, selected role, and route workflow skills.

## Present execution path

- `.grok-stack/adaptive_grok/python_test_runner.py:41`: `selected_workers()`
  validates the closed schema-1 config, then applies `GROK_TEST_WORKERS`.
  Integers remain 0–64. Invalid config still fails before an environment override.
- Lines 67–74 preserve no opt-in as `None`, opted-in children as `0`, and explicit
  counts unchanged. `auto` currently sees only affinity/CPU count, clamps to
  1–28 on POSIX, and returns 0 elsewhere. There is no cgroup-capacity reader.
- `.grok-stack/adaptive_grok/verification.py:943` calls the runner only when
  selection is non-None. Otherwise the existing unittest/coverage path remains.
  Its ordinary pytest-project branch at line 933 precedes this opt-in runner.
- `python_test_runner.py:201`: `select_engine()` degrades positive workers only
  when required imports are unavailable. It does not check cleanup capability.
- `run_core_tests()` (224) and `run_trust_tests()` (272) select the engine before
  pinning and launching. Thus the selector is the single useful platform seam.
- `_pytest_command()` (216) rejects non-POSIX. With positive explicit workers
  and importable extras, current selection reaches this refusal. This is a
  source-established gap, not a newly executed failure reproduction.
- Core stores effective workers and engine; verifier details retain requested
  workers. Trust CLI (288) prints requested/effective workers and actual engine.
- Cleanup, environment scrubbing, isolated coverage, test discovery, and exit
  propagation are separate downstream mechanisms; neither fix needs to edit them.

## Smallest coherent correction

1. Keep product changes in `python_test_runner.py` and
   `tests/test_python_test_runner.py`; no verifier/config/dependency change is
   necessary for the stated scope.
2. Put Linux quota parsing/discovery behind a small helper used only by `auto`.
   Bound effective workers by known affinity, quota capacity, and existing 28
   ceiling, with a minimum of one for a valid positive fractional quota.
   Preserve explicit integers, `None`, child `0`, non-POSIX auto `0`, and the
   current schema/environment precedence without consulting quota on those paths.
3. Specify rounding and unavailable/malformed-data fallback in the design.
   A floor with minimum one avoids rounding a 1.5-CPU quota upward to two.
   Distinguish unlimited from unreadable/invalid rather than conflating them.
4. Discovery must describe its supported cgroup layout. A root-only `cpu.max`
   read can miss a process's nested quota; a leaf-only read can miss a tighter
   visible ancestor. Use the process membership/mount mapping if promising
   actual Linux process capacity, and test that mapping without reading the host.
5. Retain PR135's `_parallel_process_cleanup_supported()` and selector guard.
   Its exact source diff is additive and directly applicable to current main.
   Keep `_pytest_command()`'s defensive POSIX refusal and strict POSIX pins.

## Precise regression gaps

- Current auto test (129) patches only affinity and asserts 22/28. It will become
  host-quota-dependent unless quota discovery is independently fixed by fixtures.
- Add deterministic auto cases: affinity 22/quota 2 => 2; smaller affinity wins;
  positive fractional quota => 1; non-integral quota documents rounding;
  unlimited uses affinity; >28 remains capped; missing/invalid/unreadable data
  follows the chosen fallback; affinity unavailable/error has a defined fallback.
- Exercise v2 `cpu.max` and supported v1 quota/period parsing, whitespace,
  unlimited markers, zero period, zero/invalid quota, malformed token counts,
  and mapping/nested-parent limits if discovery supports them.
- Assert explicit config/environment counts (including 64) are not clamped by
  quota; environment `auto` overrides an integer; no opt-in, zero, and child
  paths do not invoke capacity discovery. Assert non-Linux avoids Linux reads.
- Import PR135's three tests: emulated non-POSIX Core+Trust+CLI degradation,
  POSIX xdist selection, and measured Core coverage with coverage-only pinning.
  Emulate the capability seam rather than globally patching `os.name`.
- Retain existing missing-import degradation (136), strict pin failures (147),
  test-once/discovery/import isolation (68, 104, 187, 349), failure propagation
  (239), cleanup (201, 251, 257, 271), and coverage integrity (283, 308, 333, 385).
  A platform-specific pin test should force cleanup capability true explicitly.
- Native Windows suite qualification is broader than this emulated regression:
  current tests use `os.sched_getaffinity`, `os.mkfifo`, and Linux procfs checks.
  Do not describe the retained capability-emulation evidence as a Windows run.

## History and handoff

PR113 (`35cbbe0f`) already delivered import-capability fallback for PR33's old
failure. Existing history/tests support that distinction; no old failure output
is current RED evidence. Fresh RED should target quota/platform gaps only.
Retained PR135 review/verification documents are historical inputs, not receipts
for this route. The root owns verification, external delivery, and shared-memory
updates; only this analysis report was written by this agent.
