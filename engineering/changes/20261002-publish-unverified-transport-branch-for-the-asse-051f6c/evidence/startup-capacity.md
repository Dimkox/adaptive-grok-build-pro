# Startup capacity — 2026-10-02T13:10:47Z

- Host topology: 14 physical cores, 28 online logical CPUs.
- Controller `nproc`: 22; initial affinity: `0,1,8-27`.
- cgroup v2 effective cpuset: `0-27`; `cpu.max`: `max 100000` (no finite quota).
- Bounded child-only probe on verified IDs `0-27`: 28 CPUs, affinity `0-27`.
- Chosen capacity: 28 logical CPUs; agent slots and test-worker limits remain separately bounded.
