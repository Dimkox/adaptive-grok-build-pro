# Startup capacity snapshot

- Timestamp: `2026-10-02T07:09:39Z`
- Host: 14 physical cores, 28 online logical CPUs (`0-27`)
- Controller: `nproc=22`, affinity `0,1,8-27`
- Cgroup v2 membership: `/user.slice/user-1000.slice/session-2050.scope`; inherited effective cpuset `0-27`
- Session/user/user.slice CPU quotas: `max 100000` (unlimited)
- Child-only `taskset -c 0-27` probe: 28 CPUs, affinity `0-27`
- Chosen capacity: 28 logical CPUs; route cap 10 and test worker counts remain separate
