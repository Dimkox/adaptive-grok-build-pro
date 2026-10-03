# Controller startup and execution allocation

Observed 2026-10-03T01:14:56Z. Commands: `lscpu -p=CPU,CORE,SOCKET,ONLINE`, `nproc --all`, `nproc`, `taskset -pc $$`, `/proc/self/cgroup`, cgroup2 mountinfo, ancestor cpuset/quota reads, online CPU read, bounded child-only `taskset -c 0-27 bash ...`.

14 physical cores / 28 online logical CPUs, one socket, online 0–27. Default `nproc --all=28`, `nproc=22`, affinity 0,1,8–27. Cgroup2 mount /sys/fs/cgroup with mount root /; actual membership /user.slice/user-1000.slice/session-2050.scope. Leaf and user-1000 cpuset files are absent; inherited effective cpuset from user.slice and mount root is 0–27. Leaf, user-1000 and user.slice cpu.max each report `max 100000`; no root cpu.max or finite mounted-ancestor quota is exposed. Bounds outside this mount remain unknown.

An initial script read the absent leaf cpuset and produced an empty taskset argument; no child probe or affinity change occurred. The corrected bounded child probe over the observed inherited online set reports `nproc=28`, affinity 0–27 (PID 1997829), the same cgroup and ancestor limits. Controller affinity is unchanged. Verified effective capacity: 28, not inferred from host topology alone.

Separate limits: platform controller plus 12 child-agent slots; route analysis cap 10; verifier workers initially four on CPUs 0,1,8,9. Existing six selected analyses are complete and are not repeated. Application writer stopped after clean c50e083cc7980c3bb049af0f9382721a0f957417; no parallel writer or database fixture is scheduled during this full verifier. Five selected independent reviewers follow the verifier, and each owns a separate private read-only-source scratch contour. Persist all reports together, then run final verification before PR-only external delivery.

Previous goal turn made progress by refreshing the exact AC-008 local scope and migration-plan gates. Those records are local workflow evidence, not external signed approvals. Required F, separate G, exact-source artifact, publication and downloaded ZIP/sidecar readback remain pending under the unchanged release-wide ledger.
