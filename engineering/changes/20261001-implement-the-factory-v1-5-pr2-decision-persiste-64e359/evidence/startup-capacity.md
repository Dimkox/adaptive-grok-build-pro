# Startup capacity snapshot

- Observed: `2026-10-01T21:15:02Z`
- Host: 14 physical cores, 28 online logical CPUs (`0-27`)
- Controller: `nproc=22`, affinity `0,1,8-27`
- Cgroup v2: `/user.slice/user-1000.slice/session-2050.scope`
- Effective cpuset: inherited `0-27` from `/sys/fs/cgroup/user.slice`
- CPU quota: unlimited (`max 100000`) at the scope and inspected ancestors
- Child-only probe: `taskset -c 0-27`; `nproc=28`, affinity `0-27`, quota unchanged
- Verified execution capacity: 28 logical CPUs
- Agent capacity: one controller plus 12 child slots; route analysis cap 10
- Scheduling: five route-selected analyses in one wave; one integration writer after synthesis; code/test reviews in parallel after verification. Remaining slots are unused because the route selects no additional roles and writer/reviews have dependency edges.

Commands observed: `date -u`, `lscpu`, `nproc --all`, `nproc`, `taskset -pc $$`, `/proc/self/cgroup`, `findmnt`, applicable ancestor `cpuset.cpus.effective`/`cpu.max`, and a bounded child affinity probe.
