# Writer startup capacity

Snapshot recorded privately before repository/route inspection at 2026-10-04T21:59:32Z, then attached here after route selection.

Commands: `lscpu`, `nproc --all`, `nproc`, `taskset -pc $$`, reads of `/proc/self/cgroup` and cgroup mountinfo, effective cpuset and every applicable ancestor `cpu.max`; bounded child-only `taskset -c 0-27 sh -c 'nproc; taskset -pc $$; ...'` probe.

Observed 14 physical cores, 28 online logical CPUs (0-27), initial capacity 22 with affinity 0,1,8-27. Actual cgroup2 membership resolves to user.slice/user-1000.slice/session-2050.scope under the cgroup2 root mount. Effective cpuset inherits 0-27; leaf/user-1000.slice/user.slice quotas are unlimited (`max 100000`) and mount root has no cpu.max. The child probe succeeded with nproc 28 and affinity 0-27 in the same unlimited scope.

Verified effective capacity 28; this writer uses at most 8 test workers and a 180-second command budget. Controller/platform slots and route caps are independent; this writer spawns no agents and owns only its isolated candidate.
