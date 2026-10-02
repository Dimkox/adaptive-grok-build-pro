# Startup capacity snapshot — 2026-10-02T08:39:05Z

- Host: 14 physical cores / 28 online logical CPUs.
- Controller: 22 CPUs, affinity `0,1,8-27`.
- Effective cgroup-v2 cpuset: `0-27`; finite CPU quota: none (`cpu.max=max 100000`).
- Child-only probe on `0-27`: 28 CPUs, affinity `0-27`, unchanged cgroup.
- Chosen effective capacity: 28 logical CPUs; route analysis cap 10; child-agent cap 12.
