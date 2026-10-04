# Source-root hook cleanup implementation and timing

Evidence kind: implementer-owned targeted observations; not independent review, final full verification, a local verification receipt, merge authority or deployment.

Route `5bf1112b5ccc`; change `20261004-task-5bf111`; sole selected writer `general_implementer`. Base `ee3911869419204154e02900e58bf31492ee744c`. Frozen source branch `refactor/remove-source-root-hook-shims`; commit `24e5db19e2a971e0b8bf8f303082ad858fba9426`; Git tree `7ff3cfcf21a51fb4aeaf03775f0fdf5a042601b3`; candidate tree fingerprint `16ab53620ebba26ad3e17adb66286d1feec50e885939abd58cb98ca134fa0605`.

The source was committed at 2026-10-04T22:09:50+00:00 and remained clean/fingerprint-identical at 2026-10-04T22:12:19Z after all targeted controls. This report is prepared outside the candidate; persisting it later changes that candidate's identity and requires the coordinator's final gate on the resulting frozen tree.

## Scope implemented

Deleted exactly nine identical eight-line source-root wrappers: `session_start.py`, `user_prompt_submit.py`, `pre_tool_use.py`, `post_tool_use.py`, `pre_compact.py`, `subagent_start.py`, `subagent_stop.py`, `stop_gate.py`, `session_end.py`. They remain recoverable from the base commit; no history rewrite or broad cleanup occurred.

`tests/test_structure.py` removes only those nine expected entries and retains its committed-HEAD comparison. `tests/test_installer.py` now exercises real generated/materialized aliases for generic and Bitrix profiles: literal complete names, inventoried template bytes/modes in payload and target, canonical stdin delegation and missing-canonical JSON fallback. The minimal-source template-snapshot regression remains byte-identical.

`architecture/system.yaml` removes only those nine `NODE-LOCAL-ROUTE-POLICY.repository_paths`; generated architecture views were not rewritten. `.grok/hooks/README.md` clarifies canonical source hooks and installed generated aliases; one README inventory bullet links the shared template. `decisions.md` records virtual managed inventory reasoning, and `mistakes.md` records the corrected source-existence inference, each within three sentences.

The typed spec and brief/requirements/architecture/test-plan/tasks/release/rollback were completed before deletion. Package transitions draft -> scoped -> approved -> implementing succeeded; no route human gate exists. The package retains outstanding independent reviews and final verification.

Installer runtime, `MANAGED_FILES`, `ROOT_HOOK_SHIMS`, shared shim template, canonical hook runtime, hook configurations, VERSION, packages, historical evidence and generated views remain unchanged against the exact base. Source product diff has 16 paths: nine deletions, two tests, architecture, two hook/inventory documents and the two shared-memory facts; the active change package adds 13 workflow files.

## Startup and scheduling

CPU measurement was recorded privately first at 2026-10-04T21:59:32Z, then attached as `evidence/worker-capacity.md`: 14 physical cores, 28 online logical CPUs (0-27), default affinity 0,1,8-27 and nproc 22. Actual scope/ancestor quotas are unlimited; effective cpuset is 0-27. Bounded child-only `taskset -c 0-27` probe returned nproc 28 and affinity 0-27. Verified capacity 28, this writer allocated at most 8 workers and spawned no agents.

`timeout 180s git fetch --all --prune` exited 0. Active route and all five completed analyses were read. Adaptive-delivery, legacy-modernization and api-event-change established the preserved contract; tests were added before production deletion. Targeted independent checks ran concurrently where safe, with no shared database heavy verification.

## Commands and observed results

All Python test/check commands used `GIT_OPTIONAL_LOCKS=0 timeout 180s taskset -c 0-27`; maximum observed concurrent single-process controls stayed below the allocated eight workers. Git read-only observations used `GIT_OPTIONAL_LOCKS=0`.

- Before deletion: `python3 -m unittest tests.test_structure.StructureTests.test_repository_root_holds_only_canonical_entries -v`: expected RED, exit 1, one failure listing exactly all nine still-tracked wrappers, 0.008 s.
- Before deletion: `python3 -m unittest tests.test_installer.InstallerTests.test_installed_root_hook_aliases_delegate_and_preserve_fallback tests.test_installer.InstallerTests.test_hook_aliases_use_the_inventoried_template_snapshot -v`: exit 0, 2 tests, 4.063 s. This is compatibility characterization of unchanged runtime, not a claim that these controls initially failed.
- After deletion: `python3 -m unittest tests.test_installer -q`: exit 0, 38 tests, 26.810 s.
- After deletion: `python3 -m unittest tests.test_architecture_model -q`: exit 0, 83 tests, 2.345 s.
- After deletion: `python3 -m unittest tests.test_hooks tests.test_verification_doctor -q`: exit 0, 123 tests, 173.464 s; completed within the 180-second outer budget.
- After committing deletion candidate: `python3 -m unittest tests.test_structure -q`: exit 0, 23 tests, 0.447 s. This includes the unchanged HEAD-based root inventory control.
- `python3 scripts/grok_architecture.py validate --json`: exit 0, ok true, findings empty.
- `python3 scripts/grok_architecture.py drift --json`: exit 0, ok true, findings empty.
- `python3 scripts/grok_architecture.py diagram --check --json`: exit 0, checked true, ok true, mismatches empty; all five checked-in generated views matched.
- `python3 scripts/grok_spec.py validate --gate --json`: exit 0, ok true, errors empty, all 8 acceptance/invariant/forbidden IDs mapped; spec digest `1c97087af2fdaa359e90739442393375eb35ac9dc418cd92660d504158098869`.
- `timeout 180s ruff check tests/test_installer.py tests/test_structure.py`: exit 0, All checks passed.
- `git diff --check` before commit and `git diff --check ee3911869419204154e02900e58bf31492ee744c..HEAD` after commit: exit 0, empty output.
- `git diff --name-only ee3911869419204154e02900e58bf31492ee744c..HEAD -- scripts/install_into.py .grok-stack/templates/hook_root_shim.py .grok/hooks.json .grok/hooks/adaptive.json .grok/hooks/session_start.py .grok/hooks/user_prompt_submit.py .grok/hooks/pre_tool_use.py .grok/hooks/post_tool_use.py .grok/hooks/pre_compact.py .grok/hooks/subagent_start.py .grok/hooks/subagent_stop.py .grok/hooks/stop_gate.py .grok/hooks/session_end.py VERSION packages architecture/generated`: exit 0, empty output, proving these exact paths unchanged.
- `git add -- <the sixteen explicit product paths> engineering/changes/20261004-task-5bf111`, then `timeout 180s git commit -m 'refactor: remove redundant source-root hook wrappers'`: exit 0, 29 files, 509 insertions, 110 deletions, nine deleted wrapper files.
- Final `git status --short`: exit 0, empty output; `git show -s --format='%H%n%T%n%cI' HEAD` and `adaptive_grok.util.tree_fingerprint(Path.cwd())` returned the frozen identities above.

Targeted post-deletion modules observed 267 tests total across installer, architecture, hooks/doctor and structure, all passing. This sum excludes the two pre-deletion compatibility characterizations and intentionally excludes the expected RED probe. Reported durations are actual unittest outputs, not wall-time guarantees or full-verifier timing.

## Handoff and remaining work

The coordinator directed integration into PR #242 to avoid a second complete local/external verification cycle. Its designated writer may cherry-pick this frozen commit and resolve only shared-memory EOF conflicts while preserving both facts. No candidate writes occur after this freeze; no own review, full grok_verify, push, PR, merge, tag, release or deployed Trust CI mutation was performed by this writer.

Both selected independent reviewers must inspect the actual combined final candidate, perform relevant private-scratch mutation probes and return complete reports. Persist those reports and this implementation evidence, commit/freeze, then run ONE final full `python3 scripts/grok_verify.py --mode pr`, record the selected profile/exact inventory/skips and fresh fingerprint-bound receipts. These targeted observations authorize no extra verifier skip or fresh full completion claim. The external App-owned policy-epoch exact-head Check Run and required approvals remain necessary.

Intentional compatibility boundary: direct root wrapper paths disappear from this source checkout; consumer installer output retains all nine compatibility aliases. Broader suite regressions and combined-candidate effects are unqualified until final full verification and independent review. No new runtime behavior or migration is introduced.

Rollback is a revert PR restoring wrappers, path bindings and expectations, then targeted controls, independent review, full final verification and external exact-head Trust CI. Existing consumers need no destructive cleanup; immutable release artifacts and history remain preserved.
