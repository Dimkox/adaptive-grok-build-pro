# Core implementer CPU capacity — 2026-10-03 00:31:08 UTC

Measured before repository/route inspection in the assigned combined-source worktree.

- `lscpu`: 14 physical cores, 28 online logical CPUs, online IDs `0-27`.
- `nproc --all`: 28; `nproc`: 22; `taskset -pc $$`: process affinity `0,1,8-27`.
- `/proc/self/cgroup`: `0::/user.slice/user-1000.slice/session-2050.scope`; `/proc/self/mountinfo`: cgroup2 mounted at `/sys/fs/cgroup`, root `/`.
- Ancestors `/sys/fs/cgroup/user.slice`, `user-1000.slice`, and `session-2050.scope` each report `cpu.max = max 100000`; no finite quota observed. Root has no cpu.max file. Effective cpuset is `0-27` at root and user.slice; descendant cpuset controller files are absent, therefore inherited bound is `0-27`.
- Bounded child-only `taskset -c 0-27 sh ...` succeeded in widening child affinity: `nproc = 28`, child affinity `0-27`, same cgroup, `cpu.max = max 100000`. The final descendant cpuset read returned missing-file exit 2; inherited effective cpuset above remains the verified bound. Controller affinity unchanged.
- Assigned child `taskset -c 16-19 sh ...` reports four CPUs and child affinity `16-19`.
- Verified host effective capacity: 28 CPUs. Assigned implementer allocation: IDs `16-19`, maximum four test workers, coordinated with root total 28. No PostgreSQL allocation; no per-contour full verifier.

Commands: `lscpu`, `nproc --all`, `nproc`, `taskset -pc $$`, `sed /proc/self/cgroup`, `rg cgroup /proc/self/mountinfo`, ancestor `cpuset.cpus/cpuset.cpus.effective/cpu.max` reads, bounded child probes above.
