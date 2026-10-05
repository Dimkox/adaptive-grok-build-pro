# Bounded implementation observations

Base: f97966c4173fff9a3954389498568038dc57776b. Route: 4e78915ad1ab; sole writer general_implementer; branch feat/m8-liqvera-accepted. These observations are not qualifying verifier receipts, external CI or merge authority.

## Startup capacity, 2026-10-04T23:17:54Z

Commands: `lscpu`, `nproc --all`, `nproc`, `taskset -pc $$`, `cat /proc/self/cgroup`, mountinfo cgroup query; inspect actual membership and ancestors for cpu.max/cpuset.cpus.effective; `taskset -c 0-27 bash -c 'nproc; taskset -pc $$; cat /proc/self/cgroup'`.

Observed: 14 physical cores, 28 online logical CPUs 0-27; nproc --all=28, process nproc=22 with affinity 0,1,8-27. Actual cgroup2 membership /user.slice/user-1000.slice/session-2050.scope on /sys/fs/cgroup. Membership, user-1000.slice and user.slice cpu.max each read max 100000; root has no finite cpu.max; effective ancestor cpuset 0-27. Child-only widening succeeded: nproc=28, child affinity 0-27 and unchanged actual membership/ancestor quota bounds. Verified effective capacity 28 logical CPUs; no controller affinity mutation. Focused work uses one process. Agent slots and route cap are independent; five analyses were already complete, reviews depend on the committed candidate.

## RED before state implementation

`python3 -m unittest tests.test_project_state.ProjectStateTests.test_m8_completed_liqvera_case_unblocks_only_accepted_product_dependencies`: 1 test, expected FAIL, missing completed_product_case in M8. A subsequent whole module run found the existing five-axis binding needed a narrow M8 extension for the separate case; historical axis assertions remain intact.

## Scope and dependency ruling

Focused GREEN: `taskset -c 0-27 python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package tests.test_workflow_sources tests.test_repo_router` passed 153 tests in 15.657s. This is a bounded observation, not a qualifying full verifier receipt.

Explicit owner-confirmed completed working factory product supplies accepted-product outcome and planning dependencies. It does not provide independent telemetry or a count of exact-profile qualifying tasks. Released source, observed main and factory pin retain distinct exact identities. No runtime, architecture, API/event contract, VERSION or external system change. Current handoff uses the case; obsolete landing pilot observations remain historical/superseded with false target acceptance intact.

## Pending qualification

Coordinator owns complete independent code/test reports, final report-containing commit/freeze, the single qualifying `python3 scripts/grok_verify.py --mode pr` and fresh receipts. Its selector determines scope from the actual comparison base and all inventory statuses. Required external App-owned exact-head Trust CI and approval scopes remain separate. A focused observation cannot establish source delivery, activation or external completion.
