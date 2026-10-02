# Startup capacity snapshot — 2026-10-02T02:29:25Z

- Host: 14 physical cores, 28 online logical CPUs (`0-27`).
- Default controller affinity exposes 22 CPUs (`0,1,8-27`).
- Effective cgroup cpuset is `0-27`; no finite CPU quota exists in applicable ancestors.
- Child-only `taskset -c 0-27` probe succeeded and exposed all 28 logical CPUs.
- Selected capacity: 28 logical CPUs. Four route analyses run in parallel; heavy verifier uses the probed affinity.
