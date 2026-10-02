# Sole-writer startup capacity

Observed at `2026-10-02T01:09:47Z`, before route/package inspection. Original local snapshot: `/tmp/pr2c-implementer-capacity-20261002.json`.

Commands: `lscpu`, `nproc --all`, `nproc`, `taskset -pc $$`, `/proc/self/cgroup`, cgroup mount from `/proc/self/mountinfo`, and `cpu.max` / `cpuset.cpus.effective` at every applicable ancestor.

- Topology: 14 physical cores, 28 online logical CPUs (`0-27`).
- Default process: `nproc=22`; affinity `0,1,8-27`.
- cgroup v2 mount: `/sys/fs/cgroup`, mounted from `/`; actual membership `/user.slice/user-1000.slice/session-2050.scope`.
- Effective cpuset: `0-27` at root and `user.slice`; lower effective-cpuset files absent, inherited bound.
- Root `cpu.max` absent; applicable `user.slice`, `user-1000.slice` and `session-2050.scope` each report `max 100000`. No finite ancestor CPU quota was found.
- Bounded child-only probe: `taskset -c 0-27 bash -c 'nproc; taskset -pc $$; cat /proc/self/cgroup; read child quota/cpuset'` reported 28 CPUs, affinity `0-27`, same membership and unlimited quota. The scope cpuset file was absent; inherited `0-27` remains the bound. Controller affinity was unchanged.
- Verified capacity: 28 logical CPU workers when using the successful child affinity; writer allocation: one sequential test worker.

Dependency order: read already-approved route/package and completed analyses → failing shared regression → sole-writer guard/case adaptation → focused checks → package/commit handoff → coordinator full verification → independent reviews → final frozen receipts. Route-selected analysis scheduling and aggregate allocation remain controller-owned. No child agents were spawned by the implementer, and no parallel write owner shares this contour.
