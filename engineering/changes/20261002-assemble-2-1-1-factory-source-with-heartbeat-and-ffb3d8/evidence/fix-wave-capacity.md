# Bounded repair-wave startup capacity

2026-10-03T01:36:52Z, measured before repository/route inspection. lscpu:14physical cores (one socket,2threads/core),28online logical CPUs0-27. nproc--all28; processnproc22; processaffinity0,1,8-27. Actual cgroupv2 membership0::/user.slice/user-1000.slice/session-2050.scope; mount/sys/fs/cgroup with root/ as reported by mountinfo. Effective inherited root/user.slice cpuset0-27; child cpuset files absent/inherited. cpu.max at exposed user.slice,user-1000.slice,session-2050.scope=max100000; no finite applicable quota observed, root quota file absent.

One bounded child-only affinity probe over validated online/effective IDs0-27 succeeded: nproc28, childaffinity0-27, same membership and inheritedcpuset0-27, exposed ancestor quotas max100000. Controller affinity unchanged. Verified effective capacity28; assigned worker CPUs16-19/max4, no PostgreSQL/full verifier/review/subagents in this bounded repair wave.

Commands: date-u,lscpu,nproc--all,nproc,taskset-pc,procselfcgroup,findmnt-cgroup2,actualmembership ancestor cpuset/cpu.max reads,one taskset-c0-27 child probe and procselfmountinfo.
