# Implementer startup capacity — 2026-10-02T05:17:22Z

- Host topology: 1 socket, 14 physical cores, 2 threads/core, 28 online logical CPUs (`0-27`).
- Controller process: `nproc --all=28`, `nproc=22`, affinity `0,1,8-27`.
- Cgroup: v2 unified hierarchy, membership `/user.slice/user-1000.slice/session-2050.scope`.
- Effective cpuset: inherited from `/sys/fs/cgroup/user.slice/cpuset.cpus.effective` as `0-27`; narrower session and user-1000 files were absent/empty.
- CPU quota: `max 100000` at session, user, user.slice, and root inspected ancestors; no finite quota.
- Bounded child probe: `taskset -c 0-27 nproc` returned `28`; child affinity was `0-27`.
- Verified effective capacity: 28 logical CPUs (14 physical cores); CPU-heavy child checks may use the child-only `0-27` affinity. This writer does not dispatch other agents and will avoid overlapping full-suite verification with the controller.

Commands: `lscpu`; `nproc --all`; `nproc`; `taskset -pc $$`; `cat /proc/self/cgroup`; `findmnt -t cgroup2`; ancestor `cpuset.cpus.effective`/`cpu.max` reads; bounded `taskset -c 0-27 sh -c 'nproc; taskset -pc $$; cat /proc/self/cgroup'`.
