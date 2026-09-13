# Test-perspective review — release-sync 55364a4 (range 1a8c891..)

**Verdict: PASS**

## 1. Execution (worktree HEAD 55364a4, clean tree)
`python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package -q`
→ `Ran 89 tests in 8.213s` / `OK` (only stray stdout: a /tmp publish fixture path + sha).

## 2. Mutation probes (git archive copies under /tmp only; repo untouched)
- (a) `/tmp/shadow_a` — `latest_published_release` reverted to `v2.0.14`, `tests.test_project_state`:
  **FAILS as required** — `test_project_state_has_..._truthful_facts`: `AssertionError: 'v2.0.14' != 'v2.0.15'`
  (line 96). Lock bites.
- (b) `/tmp/shadow_b` — added empty `packages/adaptive-grok-build-pro-v2.0.16.zip`,
  `PackageTests.test_published_zip_matches_immutable_release_record_and_embedded_manifest`:
  **FAILS as required** — line 1437 `assertEqual(tuple(p for p in candidate_pair if p.exists()), ())`
  → `(PosixPath('/tmp/shadow_b/packages/...v2.0.16.zip'),) != ()`. Pending candidate cannot claim bytes.
- (c) extra hardening probe `/tmp/shadow_c` — empty zip **plus** `local_candidate.published: true`
  (attempt to satisfy the new `if published:` branch): still **FAILS twice** — manifest test
  `AssertionError: 1 != 2` (sidecar still absent) and `test_project_state`
  `AssertionError: True is not false` (line 378 `assertFalse(local["published"])`).
  The conditional branch is not a bypass: the published flag is independently locked.

## 3. Coverage sanity
`.coveragerc`: `source = .grok-stack/adaptive_grok, scripts`; `omit = tests/*`, `*/__pycache__/*`,
`.grok-stack/runtime/*`, `engineering/*`. Only Python product file changed is
`.grok-stack/adaptive_grok/__init__.py` (`__version__ = "2.0.16"`) — **not omitted**, and asserted:
`test_structure.py:266 assertEqual(adaptive_grok.__version__, version)` against `VERSION`. No `.py`
added under `engineering/` in this range, so the `engineering/*` omit hides no new code. Docs/JSON are
not coverage subjects. Nothing newly untested.

Removed vs added assert lines in `tests/`: `^-.*assert` = **22**, `^+.*assert` = **44** (net +22).
All 22 removals were repointed, none dropped: v2.0.15-candidate → v2.0.16 (`candidate_version`,
`version`, `Identity: **2.0.16**`, changelog header, roadmap line), v2.0.14-published → v2.0.15,
`len(prior)` 1 → 2 with prior[0]=v2.0.14 and prior[1]=v2.0.13 both fully asserted, `observed_at`
regex 2026-09-04 → 2026-09-13, `observed_main_sha` moved to new constant `OBSERVED_MAIN_SHA =
1a8c8917…` (line 17, = pre-merge main tip, truthful for an unmerged head).

## 4. Test counts before/after
- `tests/test_project_state.py`: 851 lines at `origin/main`/1a8c891 → **848** now (**−3**);
  `assertEqual` occurrences 148 → **160** (**+12**). Fewer lines, more assertions (block
  recompaction, not assertion loss).
- 3-module suite: baseline shadow at 1a8c891 `Ran 89 tests … OK` vs HEAD `Ran 89 tests … OK` → parity,
  no test deleted or silently skipped.

## Notes (non-blocking)
- The pending-candidate bytes lock lives only in `test_manifest_package`; `test_project_state` guards
  it via `assertIsNone(local["artifact_child"]["zip_sha256"])` + delta_paths naming. Adequate, but a
  `exists()` guard inside `test_project_state` would make the lock independent of one module.
- `if state['local_candidate']['published']:` in the release-sync test is currently a one-sided branch
  (only the `else` fires in-tree); it is inside omitted test code, so no coverage signal exists for it —
  probe (c) shows behavior is still caught, so this is informational only.
