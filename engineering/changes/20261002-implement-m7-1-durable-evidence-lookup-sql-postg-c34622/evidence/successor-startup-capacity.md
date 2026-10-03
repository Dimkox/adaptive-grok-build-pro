# F preparation startup capacity

Observed 2026-10-03 UTC before task/route inspection. Commands: `lscpu`, `nproc --all`, `nproc`, `taskset -pc $$`, `/proc/self/cgroup`, `/proc/self/mountinfo`, effective cpuset and ancestor `cpu.max` reads, and child-only `taskset -c 16-19 bash ...` probe.

Host: 14 physical cores, 28 online logical CPUs (0-27). Default process affinity: 0,1,8-27; nproc=22. Cgroup v2 membership: /user.slice/user-1000.slice/session-2050.scope; mount /sys/fs/cgroup. Root effective cpuset 0-27. Root cpu.max absent; ancestor results recorded in tool output and follow-up snapshot. Child probe succeeded on CPUs16-19, affinity16-19, nproc=4. Task allocation: CPUs16-19, maximum4 workers; use one focused-check worker conservatively until ancestor quota resolved. No controller affinity changed.

Follow-up at2026-10-03T01:22:42Z: session, user1000 and user.slice cpu.max each `max 100000`; root has no cpu controller limit file. Effective user.slice/root cpuset0-27. No finite ancestor quota found. Verified allocation capacity4; focused tests used one worker pinned16-19, at most two independent bounded diagnostics in parallel. Agent slots were already assigned by controller; no additional agents spawned.
