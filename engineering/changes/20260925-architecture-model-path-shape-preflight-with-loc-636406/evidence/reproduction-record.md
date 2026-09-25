# Reproduction record — issue #50 cascade before and after (scratch, offline)

Scratch copies live outside the reviewed worktree under a trusted non-sticky parent
(`~/.cache/issuewave-50`, mode `0700`); the worktree's own `architecture/system.yaml` was never
mutated. Source identity for both arms: branch `fix/issue-50-architecture-model-gaps`, HEAD
`cb9af4073ba6c3d515145164d771c75ebdfa3224` (`origin/main`, tag `v2.0.19`).

## Injected defect (identical in both arms)

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('architecture/system.yaml')
s = p.read_text(encoding='utf-8')
s = s.replace('"factory/src/adaptive_factory/landing_live_executors.py",',
              '"factory/src/adaptive_factory/landing_live_executors.py",\n        "factory/runtime/",', 1)
p.write_text(s, encoding='utf-8')
PY
```

The added entry lands at `architecture/system.yaml:2263` in this tree (the issue's occurrence was
line 1913 on PR #49's head — a different revision of the same document).

## BEFORE — `.grok-stack` at `cb9af407` without the contour change

```bash
python3 -m unittest discover -s tests -v
```

```
Ran 924 tests in 453.136s
FAILED (failures=1, errors=40)
```

40 errors in eight modules (`test_architecture_model` 11, `test_governance` 9,
`test_architecture_fitness` 8, `test_change_receipts` 5,
`test_landing_architecture_boundaries` 3, `test_verification_doctor` 2, `test_structure` 1,
`test_demo` 1) plus one `test_demo_http` failure — nine modules in total, none of which is about
path shapes. Every copy carried the same unlocated text:

```
adaptive_grok.architecture.ArchitectureError: node NODE-FACTORY-LANDING-LIVE-EXECUTORS repository path:
unsafe repository-relative path 'factory/runtime/'
```

and two consumers buried it further:

```
RuntimeError: governance validation failed: node NODE-... repository path: unsafe repository-relative path 'factory/runtime/'
KeyError: 'head_kind'
```

No filename, no line, no reason. Time-to-diagnosis: 453 s of suite runtime.

## AFTER — same mutation, with the contour change applied

```bash
python3 -m unittest discover -s tests -v
```

```
Ran 939 tests in 437.455s
FAILED (failures=6, errors=40)
```

The cascade count is deliberately unchanged: an invalid model must stay fail-closed for every
consumer. What changed is that each of the 40 copies is now self-diagnosing:

```
adaptive_grok.architecture.ArchitectureError: node NODE-FACTORY-LANDING-LIVE-EXECUTORS repository path:
unsafe repository-relative path 'factory/runtime/' (has a trailing separator) at architecture/system.yaml:2263
```

and the pre-existing harness gate `tests.test_verification_doctor.DoctorTests.test_project_doctor_has_no_failures`
flips to FAIL on the mutated tree, because `scripts/grok_doctor.py` now carries the `architecture-model`
item. On the clean tree that same suite is green (85 tests OK).

Attribution of the six AFTER failures, so the count is not misread as a regression:

| Failure | Why it is red in this arm |
| --- | --- |
| `test_verification_doctor.DoctorTests.test_project_doctor_has_no_failures` | pre-existing gate, now catches the bad model early — the wanted behaviour |
| `test_architecture_model_preflight.PreflightRobustnessTests.test_live_project_model_preflights_clean` | asserts the shipped model is clean; this copy's shipped model is the injected one |
| `test_architecture_model_preflight.PreflightRobustnessTests.test_live_project_declares_no_badly_shaped_path` | same reason (inventory guard over the mutated copy) |
| `test_architecture_model_preflight.DoctorPreflightGateTests.test_doctor_passes_the_shipped_model` | same reason |
| `test_architecture_model_preflight.DoctorPreflightGateTests.test_doctor_reports_one_located_failure_for_a_bad_trailing_slash` | the test injects a second bad entry into an already-bad copy, so the reported first location is not the line it expects |
| `test_demo_http.DemoHttpTests.test_health_snapshot_and_preview_endpoints_have_closed_shapes` | identical to the single BEFORE failure (`'degraded' != 'ready'`) |

All 15 of this contour's tests pass on the clean worktree (`Ran 15 tests in 1.730s / OK`).

## One-shot early report (the point of the contour)

```bash
python3 - <<'PY'
import sys, time
from pathlib import Path
sys.path.insert(0, '.grok-stack')
from adaptive_grok.architecture import preflight_architecture
t = time.perf_counter()
findings = preflight_architecture(Path('.').resolve())
print('PREFLIGHT_SECONDS %.3f findings=%d' % (time.perf_counter() - t, len(findings)))
PY
python3 scripts/grok_doctor.py; echo "exit=$?"
```

```
PREFLIGHT_SECONDS 0.038 findings=1
FAIL architecture-model: node NODE-FACTORY-LANDING-LIVE-EXECUTORS repository path: unsafe repository-relative path 'factory/runtime/' (has a trailing separator) at architecture/system.yaml:2263
exit=1
```

Whole-doctor wall time on the mutated copy: 2.78 s. Time-to-diagnosis therefore went from 453 s of
suite runtime to 0.038 s (preflight) / 2.78 s (doctor), and from "40 unlocated copies you must read
through three layers" to one line naming document, line, owning node, offending entry and reason.

## Reversal control

The check is not vacuously red. `tests/test_architecture_model_preflight.py` pins both directions —
`test_valid_model_preflights_clean_and_loads` (identical fixture without the slash → zero findings)
and `test_trailing_separator_is_rejected_not_silently_normalized` (with the slash → still raises
`code="path"`). Expected line numbers come from an independent oracle in the test (anchor on the
owning id line, then the first line holding the literal) rather than from the implementation scanner.
The whole module runs in ~1.7 s.

## Caveats that bound these numbers

- Both scratch arms are `cp -a` copies, so `.git` is the linked-worktree `gitdir:` pointer:
  git-dependent assertions (`test_structure::test_repository_root_holds_only_canonical_entries`,
  history-based fitness arms) see this branch's index. The comparison between the two arms is valid
  because both share the condition; the absolute totals are this worktree's, not a clean clone's.
- The AFTER arm additionally contains this contour's 15 new tests (924 → 939), of which 5 go red on
  the mutated tree by design (they assert the shipped model is clean) and 1 is the pre-existing
  doctor gate.
