# Sole-writer startup capacity

Measured 2026-10-02T22:36:09Z before route inspection and recorded locally at /tmp/v211-a-worker-capacity.md, then attached here. Commands: pwd; lscpu; nproc --all; nproc; taskset -pc $$; /proc/self/cgroup and mountinfo inspection; each ancestor cpuset.cpus.effective and cpu.max; taskset -c 0-27 sh -c 'nproc; taskset -pc $$; cat /proc/self/cgroup'.

Host: 14 physical cores, 28 online logical CPUs, IDs0-27. Default process: nproc22, affinity0,1,8-27. Cgroup v2 mount /sys/fs/cgroup, membership /user.slice/user-1000.slice/session-2050.scope. Session, user-1000.slice and user.slice cpu.max are max100000; root has no finite quota. Effective cpuset inherited from user.slice and root is0-27. The successfully widened child reported nproc28, affinity0-27, and the same cgroup membership and unlimited ancestor bounds.

Verified effective capacity28 CPUs; this writer's focused test allocation is two CPUs0-1. Test fixtures own worker selection up to two; the unittest harness unsets GROK_TEST_WORKERS to preserve controls for the legacy path. This process did not alter controller or system affinity. Controller separately owns platform slots, routing caps and aggregate scheduling. No child agents or additional writers were spawned.
