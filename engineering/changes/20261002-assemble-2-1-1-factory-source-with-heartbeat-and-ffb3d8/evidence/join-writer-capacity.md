# Joined-source worker capacity startup — 2026-10-03 01:03 UTC

Remeasured before inspecting the frozen precursor. lscpu reports14physical cores/28online logical CPUs, IDs0-27. nproc--all28; nproc22; controller/process affinity0,1,8-27. Actual cgroup0::/user.slice/user-1000.slice/session-2050.scope, cgroup2 mount/sys/fs/cgroup root/. Root/user.slice effectivecpuset0-27; descendant controller files absent/inherited. All applicable exposed ancestors cpu.max=max100000; no finite quota. Child-only taskset0-27 probe reports28, childaffinity0-27, samecgroup, unlimitedquota and inheritedeffectivecpuset0-27. Controlleraffinity unchanged.

Verified hostcapacity28; assignedworker IDs16-19/max4 testworkers. Root owns full gate and PostgreSQL allocation; this join uses CPU-only checks and no full gate/PG/reviews. Commands: lscpu,nproc--all,nproc,taskset-pc,$/proc/self/cgroup,/proc/self/mountinfo,ancestorcpuset/cpu.max reads and child-only probe.
