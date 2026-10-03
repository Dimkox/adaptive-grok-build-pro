# Output-close repair startup capacity

Observed 2026-10-02T23:44:09Z, before route/review inspection. Commands: UTC date; lscpu topology; nproc --all and nproc; taskset -pc $$; /proc/self/cgroup and mountinfo; effective cpuset and cpu.max at the actual cgroup and ancestors; bounded child-only taskset probe. Snapshot was recorded first at /tmp/v211-a-close-repair-capacity.md, then attached here.

Host topology:14 physical cores,28 online logical CPUs0-27. nproc --all=28; initial nproc=22; initial affinity=0,1,8-27. Actual cgroup v2 membership=/user.slice/user-1000.slice/session-2050.scope; mount=/sys/fs/cgroup. Effective inherited cpuset=0-27. Session, user-1000.slice and user.slice cpu.max values=max100000; no finite quota found, root cpu.max absent.

Controller assigned CPUs4,5, maximum2 workers. `taskset -c 4,5 sh -c 'nproc; taskset -pc $$; cat /proc/self/cgroup'` succeeded: nproc=2, affinity=4,5, unchanged cgroup membership. Verified effective repair allocation=2 CPUs, maximum2 workers; no controller/system affinity change. No subagents or full-suite work was dispatched.
