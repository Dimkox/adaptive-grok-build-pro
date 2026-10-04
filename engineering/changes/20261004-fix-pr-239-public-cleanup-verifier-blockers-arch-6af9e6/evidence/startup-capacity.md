# Startup snapshot

2026-10-04T12:07:23Z. Commands: lscpu topology, nproc --all/nproc, taskset affinity, /proc/self/cgroup, findmnt, inherited cpuset/cpu.max, bounded child-only taskset probe.

14 physical cores;28 online logical. Controller affinity0,1,8-27 (22). Cgroup v2 inherited cpuset0-27; session/user ancestors report unlimited quotas. Child probe taskset0-27 succeeds, nproc28, same membership/limits. Chosen child capacity28. Platform13 agent slots, selected4 analyses, route cap10; independent test workers avoid oversubscription.

Startup grok_verify.py --mode pr used base97a7581238022356b2de8d193a9bd8363fc92dc3 and HEAD032c0dc03922d9f1cfc09ac5c0be1dc4a58bf33f plus generated active package. Full-pr-suite selected, evidence_kind verification:full-pr-suite, no skips; executable changes/deletions present. Report changed_paths_digest: 505fe1c243456a4a04dd95177177996149a81c93a133c0aeeedb25fbad614a60. Dirty inventory was this newly generated package (route/spec/state, brief/requirements/architecture/tasks/test-plan/rollback/release and evidence README); all other changes were committed against the base. Cancelled after static blocker reproduction before implementation; cancellation is not pass. The report was emitted to the tool transcript; refused architecture inputs prevented a current receipt.
