# Selector-driven startup follow-up — 2026-09-26

Sole writer: general_implementer; route bd1cb67aa011. The existing resource-policy commit was rebased without conflict onto exact merged main `33a4d3ecb73d81dbdd48195c2681813105159b5a` before this docs-only follow-up. The actual route comparison base is refreshed to that SHA; the original checkpoint remains historical, not current verification.

## Resource snapshot

Before heavy work: `nproc --all` = 28; `nproc` = 22; `taskset -pc $$` = `0,1,8-27`; `lscpu -e=CPU,CORE,SOCKET,ONLINE` showed 28 online logical CPUs on 14 physical cores/one socket. `/proc/self/cgroup` resolved to cgroup v2 `/user.slice/user-1000.slice/session-2050.scope`; root `cpuset.cpus.effective` = `0-27`, inherited by the session. Session, user-1000.slice and user.slice `cpu.max` each returned `max 100000`; no finite ancestor quota was observed. The bounded child probe `taskset -c 0-27 nproc` returned 28, yielding 28 verified logical CPUs for affinity-widened children at this observation. The chosen verifier worker budget is 8 to share the host with other isolated work; platform controller + 12 child slots and route cap 10 are separate limits.

## Scope and evidence boundary

The source implementation is inherited unchanged from #205 / PR #207. Local verification uses `taskset -c 0-27 env GROK_TEST_WORKERS=8 PYTHONDONTWRITEBYTECODE=1 python3 scripts/grok_verify.py --mode pr`, not a caller-selected fake inventory or manual PostgreSQL skip. Historical 629 s serial Core coverage / approximately 14 s for five focused modules comes from the merged #205 test-plan and is not a total-run promise.

Skipped checks must be recorded separately from passes. No prior component result is reused for this candidate. Current local receipt/report identities must be rechecked after each commit or persisted review; PR-only exact-head external Trust CI and approvals remain mandatory. This writer will not push, create a PR or merge.

## Preliminary local result (before evidence persistence/commit)

At `2026-09-26T01:25:20+00:00`, the command above exited 0: `RESULT: PASS | mode=pr scope=docs-state-focused evidence=verification:docs-state-focused reason=eligible | profiles=base,contracts | changed=16 checked=16`. HEAD was `5681d0c8da7cf3f6dc0b8612b80aa026e1a7eb3c` plus the dirty documentation candidate; route and PR-target bases both resolved to `33a4d3ecb73d81dbdd48195c2681813105159b5a`. The checked fingerprint was `4b3ea22535882966956529445fba07da65130e35090b5c1f42ced80e89d25ab5`, changed-path digest `46d3c47d08269d5ca79bffde854ad334b26b6812afbeeb28c0bfc22760c7fb01`.

The five focused modules ran **133 tests in 14.401 s, OK**; pilot ran **44 tests in 1.478 s, OK (skipped=1: explicit pinned local Codex sandbox required)**; factory-unit ran **60 tests in 0.148 s, OK**. Diff/range checks (4/4), change-spec, architecture, governance, secret scan, contract structure, SQL safety, Ruff, Bandit and source stability passed. Selector-disclosed skips: `python-unittest`, `coverage`, `factory-postgres-exit`; workflow-artifacts also reported its existing not-configured skip. No full-suite pass is claimed. `git diff --check` passed with no output; typed spec gate passed with all five criteria mapped.

Persisting this result changes the tree, so it is preliminary evidence, not the final candidate receipt. After local commit, rerun the same command without further source edits; the runtime receipt `.grok-stack/runtime/receipts/bd1cb67aa011/verification.json` and coordinator handoff must name that exact HEAD/fingerprint. Independent code review remains pending and may require another final rerun after reports are persisted.
