PASS

# Test review — record the qwen-omni-intl executor activation (9d1695)

Reviewed at HEAD `e7692fc0` (clean), base `05b69c7`. `tests/` is byte-identical to
base — this wave adds no test code; the omni role is covered only through
data-driven loops in `tests/test_project_state.py::test_runtime_observations_are_source_bound_without_promoting_qualification` (the suite has no `test_runtime_observations.py` file and the literal string "omni" appears nowhere under `tests/`). All mutations were run in a throwaway `/tmp` 0700 clone (deleted); the repository stayed byte-clean (verified `git status --porcelain` empty before and after).

## 1. Measured runs (exact)

`python3 -m unittest tests.test_project_state tests.test_structure tests.test_manifest_package tests.test_change_spec`
→ **Ran 120 tests … OK** (9.455s). Per module: test_project_state **15**, test_structure **19**,
test_manifest_package **56**, test_change_spec **30**. Matches the `tasks.md` claim "120 coupled tests OK".

## 2. Omni coverage map (mutation-probed, 16 kills/silents)

The test consumes the dossier at `runtime_observations.evidence` only via
`source_base`, `qwen_historical_acceptance`, `grok`, `service_observation`.
The `(primary, secondary)` tuple loop never reaches omni; the only omni-touching
check is `for service in runtime["services"].values(): HttpLandingProfile.for_provider(selected_profile).model_id == model`.

| Mutation (in clone) | Result |
|---|---|
| M1 `services.omni.model` → wrong | **KILLED** (values() loop) |
| M2 `omni.selected_profile` → unknown | **KILLED** (for_provider raises) |
| M4 `omni.selected_profile` → `grok-vision` | **KILLED** (model mismatch) |
| M10 evidence pointer → missing file | **KILLED** (dossier existence + parse pinned) |
| M18 dossier `service_observation` grok block removed | **KILLED** (primary/secondary raw binding real) |
| M19/M20 falsify primary `installed_sha` / secondary `artifact_digest` | **KILLED** (precedent binding works) |
| M3 `omni.selected_profile` → `qwen-omni` (mainland, same model_id) | **SILENT** — the intl-vs-mainland distinction that is the entire point of issue #86 is unpinned |
| M5 `omni.acceptance.profile_digest` → zeros | **SILENT** |
| M6 `omni.installed_sha` → 40×"0" | **SILENT** — the "which release runs omni" fact is reviewer-honesty only |
| M7 `omni.live_enabled` → false | **SILENT** |
| M8 acceptance http_status 503 / state / provider_requests | **SILENT** |
| M12 unit rename, active_state→inactive, activated_at→2020 | **SILENT** |
| M9 evidence pointer → old post-108 dossier (no omni block; same source_base) | **SILENT** — the record can un-claim its own dossier |
| M11 drop `services.omni` entirely | **SILENT** — nothing forces the omni record to exist |
| M13 delete dossier `omni` block | **SILENT** |
| M14/M16/M17 falsify dossier `omni.activation` or diverge dossier vs state | **SILENT** |

**Pinned by tests:** omni profile↔model consistency against `HTTP_PROFILES`, dossier
file existence/parseability, and (for primary/secondary only) state↔dossier source
binding and raw `service_observation` backing. **Reviewer-honesty only:** every
other omni field in PROJECT_STATE, the entire dossier `omni` block,
state↔dossier agreement for omni, and the existence of the omni record itself.

**Sufficiency judgment.** For a records wave this is a *pass with an explicit
asymmetry*: the precedent roles were added with full source binding — base
`05b69c7` (tests byte-unchanged since then) already contained the tuple loop
pinning `installed_sha`↔`merged_and_installed_sha`/`merged_commit` and
`acceptance.artifact_digest`↔`socket_acceptance`/`smoke`, so primary/secondary did
NOT have this gap. Omni deviates from the pattern it copies because its acceptance
shape differs (`normalized`/`profile_digest` vs `artifact_ready`/`artifact_digest`)
and it was left out of the loop. The externally-verified, cited-not-asserted model
is correct for live truth, but internal consistency (record↔dossier agreement for
omni) is a repo-checkable property that precedent tested and this wave does not.

## 3. Dossier↔record consistency

Nothing asserts `evidence["omni"]` equals `state…services.omni` (probes M16/M17
silent). Minimal follow-up (next wave or in-package note, not blocking):

```python
omni, act = runtime["services"]["omni"], evidence["omni"]["activation"]
for k in ("installed_sha", "selected_profile", "model", "live_enabled"):
    self.assertEqual(omni[k], evidence["omni"][k])
for k in ("job_id", "http_status", "profile_digest", "live_url"):
    self.assertEqual(omni["acceptance"][k], act[k])
self.assertEqual(omni["acceptance"]["state"], act["state"])
```

## 4. Spec/plan claims vs measured reality

- Reproduce: "120 coupled tests OK" ✓; test-plan "three-service loop incl. omni model
  equality" ✓ (values() loop is 3-service, M1 proves); "Activation truth … cited, not
  asserted by unit tests" ✓ honest; `source_base`==`observed_main_sha`==`e7d0f72b…` ✓;
  INV-002 byte-identity of primary/grok dossier blocks ✓ (old vs new dossier compare equal);
  shared-source-chown wording ✓ against `factory/runtime/install-claw.sh`
  (`source_root=/opt/adaptive-l5/sources/fde60e04…`, created once, reused by every release
  install — one chown covers all three units; live host state not repo-verifiable).
- **DOES NOT REPRODUCE (3):**
  1. **Dossier self-contradiction (stale carry-over):** `limits` still contains the
     post-108 line "The qwen-omni-intl profile … is source-only in this observation;
     no installed unit loads it and no new provider call was made" — false in this
     dossier, which records an installed omni unit and one real provider call.
  2. **AC-003/architecture.md overclaim:** they say the dossier records the incident
     ("failed first start … root-owned .git/index exposed by validate_source"); the
     dossier contains no such account — only an oblique `limits` mention ("stale-root-index
     hazard … appeared in this session's precheck"). The words incident/failed/validate_source
     appear nowhere in the dossier; the disclosure lives only in the package prose.
  3. **SIG-001 "NRestarts 0":** no NRestarts value exists in the dossier or anywhere in
     the record — unverifiable as cited.
- Related: `observation_provenance.method` claims "systemctl show for all three executor
  units", but `service_observation` is byte-identical to the old dossier and contains only
  the primary and grok blocks; omni active/enabled has no raw backing embedded.

None of these are test-detectable by design (they are dossier prose fields no test reads —
M13/M14/M15 silent). They are for the code reviewer / author to fix in-record.

## 5. Hermeticity

Confirmed: no test invokes `systemctl`/`curl`/network. Grep hits are fixture strings inside
policy/adversarial tests (example.invalid URLs, blocked-command payloads), a localhost test
listener, and `test_workflow_artifacts_adversarial.py` which *patches
`socket.create_connection` to raise* — the suite enforces the absence of network. The omni
tests check only internal consistency (state↔dossier↔HTTP_PROFILES); the record's live truth
(unit active, socket 200, provider normalized) is cited, never probed. Clone runs touched no
live host.

## Verdict

**PASS** — 120/120 green, plan claims reproduce (except the three record-content items
above, which belong to the author/code reviewer, not the test gate), suite is hermetic.
Limits stated once: for omni the tests guarantee only profile↔model consistency and dossier
existence; installed_sha, activation facts, live_enabled, the omni record's own existence,
the intl-vs-mainland profile choice (M3), and state↔dossier agreement are all reviewer-honesty,
weaker than the primary/secondary precedent — close with the §3 assert next wave.
