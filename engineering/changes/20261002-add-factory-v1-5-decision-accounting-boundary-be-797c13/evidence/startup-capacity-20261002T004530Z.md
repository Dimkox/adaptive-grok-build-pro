# Startup capacity snapshot — 2026-10-02T00:45:30Z

- Host: 14 physical cores, 28 online logical CPUs (`0-27`).
- Controller: 22 CPUs visible by default; affinity `0,1,8-27`.
- Cgroup v2 effective cpuset: `0-27`; `cpu.max` is `max 100000` through applicable ancestors, so no finite quota was found.
- Bounded child probe `taskset -c 0-27`: success; 28 CPUs visible and affinity `0-27`.
- Chosen capacity: 28 logical CPUs. Route analysis cap (4 selected agents), platform slots, and test worker totals are managed separately.
