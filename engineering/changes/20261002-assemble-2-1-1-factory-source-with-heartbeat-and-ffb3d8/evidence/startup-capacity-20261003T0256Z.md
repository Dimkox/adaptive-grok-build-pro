# Startup capacity, 2026-10-03 02:56:28 UTC

Before route/backlog inspection or dispatch: date/lscpu -p=CPU,CORE,SOCKET,ONLINE/nproc --all/nproc/taskset -pc $$, /proc/self/cgroup and mountinfo observed.14 physical cores,28 online logical IDs0-27; default nproc22 and affinity0,1,8-27. Actual cgroup v2 /user.slice/user-1000.slice/session-2050.scope at mount /sys/fs/cgroup, mount root /.

Explicit leaf/user-1000/user.slice/root cpu.max and cpuset effective/declared bounds read. No visible finite quota; leaf and user1000 inherit effective0-27 from user.slice/root. Some leaf cpuset files and root cpu.max unavailable; unexposed outer limits remain unknown. Child-only taskset -c0-27 probe succeeded: nproc28, affinity0-27, same cgroup, unchanged visible unlimited ancestor quotas. Controller/system affinity unchanged. Verified visible effective capacity28 logical workers, conservative test allocation not28 physical cores.

Latest user says missed deadlines. Status inspection only now; no long local checks authorized (owner max180seconds persists). Exactly one application writer at a time; all previous writers stopped. Platform13slots/controller+12, route analysiscap10, process-worker limits independent. No new analysis/review wave for unchanged product. Read saved handoff and exact GitHub PR238 next; existing external App check is expected running state, not a blocker by itself.
