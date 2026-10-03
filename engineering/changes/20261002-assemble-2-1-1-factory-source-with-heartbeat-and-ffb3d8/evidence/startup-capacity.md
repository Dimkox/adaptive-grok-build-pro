# Startup resource discovery — continuation

Resource discovery preceded handoff, route inspection, skills, dispatch and heavy work. Commands: date,lscpu -p,nproc --all,nproc,taskset -pc,process allowed-list/cgroup/mount reads, actual cgroup ancestor cpu.max/cpuset walk, one child-only widening probe.

```text
2026-10-02T23:20:51Z
# The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting usually from zero.
# CPU,Core,Socket,Online
0,0,0,Y
1,1,0,Y
2,2,0,Y
3,3,0,Y
4,4,0,Y
5,5,0,Y
6,6,0,Y
7,7,0,Y
8,8,0,Y
9,9,0,Y
10,10,0,Y
11,11,0,Y
12,12,0,Y
13,13,0,Y
14,0,0,Y
15,1,0,Y
16,2,0,Y
17,3,0,Y
18,4,0,Y
19,5,0,Y
20,6,0,Y
21,7,0,Y
22,8,0,Y
23,9,0,Y
24,10,0,Y
25,11,0,Y
26,12,0,Y
27,13,0,Y
28
22
pid 1285763's current affinity list: 0,1,8-27
Cpus_allowed_list:	0-1,8-27
0::/user.slice/user-1000.slice/session-2050.scope
35 25 0:30 / /sys/fs/cgroup rw,nosuid,nodev,noexec,relatime shared:10 - cgroup2 cgroup2 rw,nsdelegate,memory_recursiveprot
cgroup=/sys/fs/cgroup/user.slice/user-1000.slice/session-2050.scope
cpu.max=max 100000
cpuset.cpus.effective=absent
cgroup=/sys/fs/cgroup/user.slice/user-1000.slice
cpu.max=max 100000
cpuset.cpus.effective=absent
cgroup=/sys/fs/cgroup/user.slice
cpu.max=max 100000
cpuset.cpus.effective=0-27
cgroup=/sys/fs/cgroup
cpu.max=absent
cpuset.cpus.effective=0-27
online=0-27
child-only candidate=0-27
28
pid 1285812's current affinity list: 0-27
0::/user.slice/user-1000.slice/session-2050.scope
```

Verified host topology:14 physical cores /28 online logical CPUs. Existing affinity22CPUs; nearest effective cpuset0-27, visible ancestor quotas unlimited. Bounded child-only probe succeeds with28CPUs and same membership; controller affinity unchanged. Chosen effective capacity28. Existing verifier/reviewer process allocations are retained; no running work is restarted. Agent slots and route cap are separate limits.
