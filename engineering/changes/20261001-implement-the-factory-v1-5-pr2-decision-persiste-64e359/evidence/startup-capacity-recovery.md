# Recovery capacity snapshot

- Observed: `2026-10-01T21:23:04Z` after daemon restart.
- Host: 14 physical cores, 28 online logical CPUs (`0-27`).
- Controller: `nproc=22`, affinity `0,1,8-27`.
- Cgroup v2 scope: `/user.slice/user-1000.slice/session-2050.scope`; inherited effective cpuset `0-27`; `cpu.max=max 100000` at scope and inspected ancestors.
- Bounded child probe: `taskset -c 0-27`, `nproc=28`, affinity `0-27`, no finite quota.
- Chosen capacity remains 28 logical CPUs.
- Recovery evidence: no `grok_verify.py`, coverage, or unittest process remained and no new verification receipt existed; the interrupted baseline must be rerun.
