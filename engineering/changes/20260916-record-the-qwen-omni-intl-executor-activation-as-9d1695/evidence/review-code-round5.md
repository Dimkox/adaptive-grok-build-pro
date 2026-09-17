PASS

> Verdict line restored by the author from the reviewer's final message: the report the
> reviewer wrote to disk began with its heading, while the required first line was delivered only in the
> message. Everything below is the reviewer's file, unedited.

# Round-5 delta code review — 6633e32

Object: `git diff 35d44e6..6633e32` = 3 files, +8/-2 (route.json 1 line, tests/test_project_state.py +6, review-response.md 1 line). Worktree clean (`git status --porcelain | wc -l` = 0).

## Checks
a. **PASS.** `git merge-base HEAD origin/main` = `2f66ba6ef82d0f6a0bb3a4389e7f03b393c99217`; package `route.json:19` and `.grok-stack/runtime/active-route.json:19` both hold that same SHA. Caveat: the runtime copy is untracked — `git ls-files --error-unmatch .grok-stack/runtime/active-route.json` → "Did you forget to 'git add'?".

b. **Claim exact.** `git diff --name-only 2f66ba6...HEAD | wc -l` = **22**. From the stale base `05b69c7...HEAD` = **40**, and `grep -c "architecture_diff.py|test_architecture_fitness.py"` on that list = 2. The 22 contain no production file: no `architecture_diff.py`, `architecture.py`, `rules.yaml`, `factory/src/.../contracts`; the only near-hit is the package doc `…/architecture.md`. Rest is the package (17 files) + `PROJECT_STATE.json`, `README.md`, `START_HERE.md`, `tests/test_project_state.py`.

c. **Honest.** `.grok-stack/adaptive_grok/router.py:428-429` — `base_fingerprint = (\n        tree_fingerprint(root)` (routing-time tree hash, override only via `demo.py`); `grep -rn base_fingerprint .grok-stack/adaptive_grok/` returns zero hits in `verification.py`/`governance.py` — the only other mentions are `router.py:438` (`route_seed`), `workflow_artifacts.py:51` (field-name list) and `demo.py`. So keeping `4912927a…` after re-pointing the commit is correct, not sloppy.

d. **Guard fires.** `landing_failover_contracts.py:7` — `TERMINAL_STATES = frozenset({"artifact_ready", "provider_unavailable", "rejected", "needs_human", "cancelled"})` (contains `artifact_ready`, not `normalized`; `normalized` only in `STATES` on line 8). /tmp copy, both `PROJECT_STATE.runtime_observations.services.omni.acceptance.state` and dossier `omni.activation.state` set to `artifact_ready`: `AssertionError: 'artifact_ready' unexpectedly found in frozenset({'rejected', 'cancelled', 'artifact_ready', 'provider_unavailable', 'needs_human'})` (tests/test_project_state.py:826), `Ran 15 tests … FAILED (failures=1)`.

e. **Legitimate terminal state unaffected.** Same module on the unmutated copy is `Ran 15 tests … OK` while `PROJECT_STATE.json:1677` and `:1700` already record `"state": "artifact_ready"` under other services' `acceptance` — the assert is scoped to `omni["acceptance"]["state"]`, so it forbids promotion of the omni activation only, not the vocabulary.

f. **Row is substantially true, with two overstatements.** Verifiable parts all check out: `verification.py:472` `raw_route_base = route.get('base_commit')` and `:557/:563` `source='route.base_commit'` (the PR-mode basis claim), 40→22 with `architecture_diff.py` attributed to another wave, `base_fingerprint` = `tree_fingerprint(root)` not commit-derived, `sha256` illustration consistent with the frozen `4912927a…`. Overstatements in Finding 2/3 below.

g. **Claim remains wrong; spec does not repeat it.** Commit `3c379ca` message: "NRestarts is explained as structural rather than probative in all three surfaces plus SIG-001/AC-003." AC-003 today (`change-spec.yaml:41`) has no such caveat — it only lists the field as captured content: "the three-unit systemctl capture (Id/ActiveState/UnitFileState/MainPID/NRestarts/Result/…)". The caveat exists in SIG-001 (`change-spec.yaml:100`: "NRestarts=0 is carried because the capture is verbatim, not as a stability signal") and in `README.md`/`START_HERE.md`/`evidence/README.md` (the only "probative" hits). Disclosure gap in an immutable commit message, not a code defect.

## Findings
1. **Medium (test correctness) — the new assert only resolves by test-order accident.** The function-local `from adaptive_factory.landing_failover_contracts import TERMINAL_STATES` (line 825) depends on `sys.path.insert(0, ROOT/"factory"/"src")` performed inside a *different* method (`tests/test_project_state.py:849-851`, `test_m4_roadmap_…`, which merely sorts earlier): `python3 -m unittest tests.test_project_state.ProjectStateTests.test_runtime_observations_are_source_bound_without_promoting_qualification` → `ModuleNotFoundError: No module named 'adaptive_factory'`. Fix: reuse that bootstrap at module scope (or hoist `factory_src` to a module-level `sys.path` insert) so the guard survives `-k`/isolated reruns.
2. **Low (evidence) — F5 marked CLOSED includes the timestamp half, which is only half-done.** `state.json:30` still carries `implementing→reviewing at 2026-09-17T02:20:00+00:00` written by `3c379ca` (author date `02:16:44+00:00`), i.e. still +3m16s future-dated and untouched by the delta; the row's "The state.json transition now carries a real commit time" is true only of the new `reviewing→verifying at 04:09:07` added by `35d44e6` (ad `04:10:17`). Fix: narrow that sentence to the new transition and disclose the `02:20:00` stamp as disclosed-not-corrected.
3. **Low (evidence wording) — "it only seeds `route_id`"** understates: `base_fingerprint` is also persisted as a route record field (`router.py:463`) and appears in `workflow_artifacts.py:51`'s field list. The load-bearing half (nothing recomputes or validates it) is correct; fix by saying "no verifier recomputes it; it seeds `route_id` and is recorded as a route field".
4. **Low (effective scope of the fix) — the re-point lives in an untracked runtime file.** `verification.py` reads the runtime `active-route.json`, which agrees on this host but is not versioned, so nothing in the tree pins `base_commit=2f66ba6` for a fresh routing state. Fix: say so in the F5 row (or re-route on merge) so the CLOSED label is not read as machine-enforced elsewhere.

No finding on the `base_fingerprint`-kept decision (c) or the 22-file scope (b): both are as described.

Limits: read-only to the worktree; all mutation in `/tmp/rec-r5` (restored with `git checkout -- .`); ran only `tests.test_project_state` (15 tests, ~0.17s), no `grok_verify.py`, no suite runs, no GitHub, no secrets or service access.
