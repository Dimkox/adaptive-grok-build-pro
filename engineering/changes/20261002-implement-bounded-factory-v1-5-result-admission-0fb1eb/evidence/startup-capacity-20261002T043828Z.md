# Startup capacity snapshot

- Timestamp: `2026-10-02T04:38:28Z`
- Host: 14 physical cores, 28 online logical CPUs (`0-27`)
- Controller: `nproc=22`, affinity `0,1,8-27`
- Cgroup v2: `/user.slice/user-1000.slice/session-2050.scope`; effective cpuset `0-27`
- Applicable ancestor CPU quotas: all `max 100000` (unlimited)
- Child-only `taskset -c 0-27` probe succeeded with 28 CPUs and affinity `0-27`
- Chosen capacity: 28 logical CPUs; route analysis cap 10; test process counts remain separate
- Commands: `lscpu`, `nproc --all`, `nproc`, `taskset -pc`, `/proc/self/cgroup`, `findmnt`, effective cpuset/ancestor `cpu.max`, bounded child probe
