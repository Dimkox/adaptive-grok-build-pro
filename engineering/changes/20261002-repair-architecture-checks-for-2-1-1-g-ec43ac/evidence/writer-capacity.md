# Writer startup capacity

Local snapshot recorded before repository inspection at `/tmp/v211-h-writer-capacity-20261002.txt`, timestamp 2026-10-02T23:56:00Z.

Commands: `lscpu`, `nproc --all`, `nproc`, `taskset -pc $$`, `/proc/self/cgroup`, `findmnt -rn -t cgroup,cgroup2 -o TARGET,FSROOT,FSTYPE`; ancestor `cpuset.cpus.effective`/`cpu.max` reads; bounded `taskset -c 0-27` child probe reading capacity, affinity and membership; `taskset -c 24,25 nproc`.

Observed 14 physical cores / 28 online logical CPUs 0-27. Initial process affinity 0,1,8-27 exposes 22 CPUs. Cgroup2 mounted `/sys/fs/cgroup`, mount root `/`, membership `/user.slice/user-1000.slice/session-2050.scope`. Root and user.slice effective cpuset 0-27; lower cpuset files absent and inherited. Root cpu.max absent, all applicable user.slice/user-1000.slice/session ancestors show `max 100000`, no finite quota.

Child-only widening succeeded, affinity 0-27 and capacity 28 in the same cgroup with the same quota bounds; controller affinity unchanged. Verified capacity 28; writer allocation CPUs24/25, two-worker maximum. Controller completed selected analyses and initial PR selector before dispatch; this writer owns four product files only and performs focused checks, with aggregate full verification and independent reviews still required.
