# Sole writer resource snapshot

Docs-only restart observed2026-10-04T20:50:15Z before inspection:14physical/28online CPUs0–27; defaultnproc22/affinity0,1,8–27; actual unified-cgroup ancestors inheritedcpuset0–27 and no finite observed quota. Child-only widening0–27 again succeeded withnproc28 and unchanged membership/quota. Private snapshot recorded outside candidate first; docs writer limit2, no nested agents/full suite. Scope/base/head/dirty inventory remain required; final scope admission belongs to the single final PR gate after reviews and report-containing freeze.

Observed 2026-10-04T20:06:53Z, before package/route/code inspection. Local private snapshot was recorded outside the candidate first.

`lscpu`: 14 physical cores, 28 logical CPUs online 0–27. `nproc --all`: 28; default `nproc`: 22; `taskset -pc <child-shell-pid>`: 0,1,8–27. Actual unified cgroup membership and mount were resolved from proc. Root/user effective cpuset was 0–27, inherited by lower ancestors; observed applicable ancestor/leaf cpu.max values were unlimited (`max 100000`), and root had no cpu.max file.

Bounded child-only `taskset -c 0-27` probe succeeded: child nproc28, affinity0–27, unchanged cgroup membership and unlimited leaf quota. Verified effective capacity28; no controller/system affinity mutation. Writer allocation was at most8 test workers, with no nested agents and no controller full verifier in this lane. Committed covering controls use two coordinating xdist workers and file-level distribution to leave capacity for the runner fixtures' existing bounded subprocess workers. Host observations are dated, not future capacity guarantees.
