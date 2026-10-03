# G after F — PREPARATION ONLY

Original G `feat/v211-current-authority` remains at `3423e7d5d6f8bef96e54cbeb698c49462cb01583`. Its feature `7902c6b0`, main synchronization merge `49330e1a` and binding repair `3423e7d5` are preserved. Predecessor F is exactly `bbfaa714e64fefd1acd8c8d7491268903563ee62`; new preparation branch is `feat/v211-g-after-f`. The final preparation identity is the commit containing this report, resolved by `git log -1 feat/v211-g-after-f` and its `HEAD^{tree}`; immutable resolved identities are returned to the controller.

Restack applied only actual `63799f876..3423e7d5` G delta onto F, excluding the main artifact synchronization. Only append-only `decisions.md`/`mistakes.md` overlaps required resolution; both histories were retained. Runtime, contract and ownership bytes match original G delta; worker/webhook/publication implementation, deployed material and the five focused-selector binding files were unchanged. No architecture guard changes were needed: the frozen predecessor already repairs metadata separation and permits additive OpenAPI components.

Preparation plan: preserve original branch, apply bounded G delta on exact F, retain approved authenticated observation semantics and historical failures, run only bounded G tests/model/fitness, save fresh preparation evidence, commit and stop all writes. Existing G1–7 obligations remain source requirements; observation never conveys execution or merge authority. Route base remains untouched. Old failed fitness/full-verifier records remain historical, not current acceptance evidence.

Startup `2026-10-03T02:07:30Z`: lscpu reports14physical/28online logical CPUs, nproc--all28/nproc22, process affinity0,1,8-27. cgroup2 membership `/user.slice/user-1000.slice/session-2050.scope`, mounted `/sys/fs/cgroup`; root/user-slice effective cpuset0-27. Membership/user/ancestor `cpu.max` each reads `max100000`; root quota file absent, so no visible finite quota. Child taskset16-19 succeeds, nproc4/affinity16-19; assigned capacity4workers maximum. Independent focused/model commands used disjoint16-17/18-19; serial architecture checks used16-19.

Fresh scoped commands on the provisional candidate:

- `PYTHONPATH=trust-ci/tests taskset -c 16,17 python3 -m unittest test_authority test_api test_store -q`:62tests pass, including closed versioned snapshot schema and negative controls.
- `taskset -c 18,19 python3 -m unittest tests.test_architecture_model -q`:84tests pass.
- `taskset -c 16-19 python3 scripts/grok_architecture.py validate --json` and `drift --json`:ok=true, no findings.
- `taskset -c 16-19 python3 scripts/grok_architecture.py fitness --base bbfaa714e64fefd1acd8c8d7491268903563ee62 --worktree --pre-risk red --json`:fitness_status=pass, actual unchanged whole-file accounting against exact F. No historical blocker reproduced.
- `git diff --check`:pass.

Complete private outputs: `/tmp/v211-g-preparation-evidence/` (mode0700), `fitness.json`, `focused-tests.log`, `architecture-tests.log`, `validate.json`, `drift.json`; startup/plan recorded before restack in `/tmp/v211-g-preparation-capacity.txt` and `/tmp/v211-g-preparation-plan.md`.

Unexecuted: full PR verifier, PostgreSQL fixtures, independent reviews, exact-head external Trust CI and approvals. Those remain controller obligations. F/Core acceptance is not claimed. No push, merge, tag, publication, deployment or external write performed. Source rollback is an isolated PR revert; no database or deployed state was changed. Current cross-source observation cannot create a transaction across mounts, so mutation rechecks and earliest validity cutoff remain its bounded fail-closed safeguards.
