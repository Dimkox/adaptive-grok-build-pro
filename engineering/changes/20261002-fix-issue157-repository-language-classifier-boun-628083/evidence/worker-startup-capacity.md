# Selected C writer startup capacity

Recorded locally before route/backlog/code inspection at 2026-10-02T22:36:44Z in ignored `.grok-stack/runtime/c-classifier-startup-capacity.json`; attached here after reading the route.

Commands: `lscpu`, `nproc --all`, `nproc`, `taskset -pc $$`, `/proc/self/cgroup` and `/proc/self/mountinfo` reads, ancestor `cpuset.cpus.effective`/`cpu.max` reads and one child-only `taskset -c 0-27` probe followed by the same affinity/cgroup checks.

Observed 14 physical cores, 28 online logical CPUs 0–27, default nproc 22 and affinity 0,1,8–27. Cgroup v2 mount `/sys/fs/cgroup`, membership `/user.slice/user-1000.slice/session-2050.scope`; session/user cgroups lack a cpuset file and inherit enclosing user.slice/root 0–27. All applicable non-root CPU quotas read `max 100000`; root has no cpu.max and no finite ancestor quota exists. No capacity bound remains unresolved.

Child probe succeeded: nproc 28, affinity 0–27, unchanged cgroup and quotas. Verified effective capacity is 28. Controller/system affinity was not modified. Parent subsequently allocated C CPUs 6,7 and at most two focused workers; focused unittest runs are one process constrained to those CPUs. Controller owns heavy/full verification allocation. Agent slots and route permissions are separate limits; this writer spawned no subagents.
