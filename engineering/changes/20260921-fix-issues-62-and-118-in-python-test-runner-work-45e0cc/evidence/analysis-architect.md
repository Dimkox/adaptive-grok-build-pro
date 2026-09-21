# Architect analysis — runner CPU capacity and platform selection

Route: `45e0cc3b5da0`; analysis only, 2026-09-21.
Inspected the current runner/tests, active route/brief, prior capacity research,
and retained PR135 commit `7a7851af5d11e8ce5c3af23ab46214ae7ae4cdc8`.
No tests, host probes, application edits, or external writes were performed.

## Current boundary

- `selected_workers()` currently caps `auto` at 28 using affinity or CPU count;
  it never reads a quota, and an affinity syscall error currently escapes.
- Missing opt-in returns `None`; explicit `0` and `_GROK_TEST_CHILD=1` preserve
  sequential execution. Valid explicit counts are 0–64 and override config.
- Both core and Trust execution call `select_engine()` before version checks.
  Missing modules already select `unittest-degraded`; importable wrong pins fail.
- PR135 adds a POSIX cleanup-capability predicate to that existing decision;
  it does not require lifecycle, collection, coverage, or verifier refactoring.

## Recommended bounded implementation

1. Keep capacity discovery private to this runner, called only for `auto` on
   supported POSIX platforms. Keep the non-POSIX `auto -> 0` behavior and return
   explicit numeric requests unchanged before any capacity I/O.
2. Obtain positive affinity length, falling back on unavailable/failed affinity
   to positive `os.cpu_count()`, then 1. Preserve the existing maximum of 28.
   Query cgroups only on Linux; other POSIX hosts retain the existing CPU bound.
3. Isolate pure quota and proc-text parsers from small read helpers so fixtures
   can describe an entire hierarchy without depending on the test host.
4. Read `/proc/self/cgroup` and `/proc/self/mountinfo`; never assume the current
   process belongs at `/sys/fs/cgroup` or to a fixed `cpu` mount directory.
   Match v2 `0::path` to `cgroup2`; for v1 match exact `cpu` controller tokens in
   membership and cgroup mount super-options, including `cpu,cpuacct` mounts.
5. Parse mountinfo around its ` - ` separator, tolerate optional fields, decode
   mount path escapes, and map `membership.relative_to(mount_root)` underneath
   that mount point. Use path components, not string-prefix matching.
6. Inspect the matched group and every visible ancestor through the mount root,
   inclusive. Where multiple unambiguous mounts expose the same hierarchy,
   retain the wider visible ancestor range; never prefer a bind subtree merely
   because its path is more specific. Bound traversal by parsed path depth.
7. Reject ambiguous mappings and `..` components without normalizing them into
   guessed host paths. Ordinary namespace-root `/`, nonstandard mount points,
   and valid bind-subtree roots are in scope. Hidden ancestors and namespace
   roots outside the visible mount cannot be reconstructed by this feature.
8. Parse v2 `cpu.max` as exactly quota/max plus a positive period; v1 uses
   `cpu.cfs_quota_us` and `cpu.cfs_period_us` from the same group. Recognize
   `max` and the v1 `-1` unlimited sentinel; zero, unsupported negative values,
   invalid tokens, missing v1 pair members, and nonpositive periods are unknown.
9. For each positive quota use integer `max(1, quota // period)`; take the
   minimum with all visible finite quotas, affinity/count, and 28. Flooring is
   an explicit conservative choice: 0.5 and 1.5 CPU each select one worker;
   2.5 CPU selects two. Unlimited leaves never terminate ancestor inspection.
10. Distinguish known-unlimited, absent controller, and unknown evidence.
    Expected absent v2 quota files must not suppress a readable parent limit.
    Unreadable/malformed relevant data or unresolved membership selects one
    auto worker conservatively; document this fallback and disclose the reason
    through one concise diagnostic if runtime disclosure is required. Preserve
    current result schemas and normal worker/engine reporting.
11. Carry PR135's cleanup-capability predicate into `select_engine()` before
    launch/pin checks. Numeric requests on unsupported platforms select
    `(0, 'unittest-degraded')`; supported platforms retain requested counts.

## Evidence behind discovery decisions

Cgroup v2 control is hierarchical, `cpu.max` is a quota/period pair, and the
true root lacks that control file. Controller files can also disappear when a
parent does not enable the controller. Therefore an absent leaf must still
allow parent inspection. [Kernel cgroup v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html)

V1 uses the quota/period files above; a parent can throttle a child with its
own quota remaining. [Kernel CFS bandwidth documentation](https://docs.kernel.org/scheduler/sched-bwc.html)

The mount root and mount point have different meanings; optional fields are
variable. Namespace virtualization can expose a preexisting mount root as
`/..`, which this bounded design treats as unresolved. [Mountinfo format](https://man7.org/linux/man-pages/man5/proc_pid_mountinfo.5.html), [Cgroup namespaces](https://www.man7.org/linux/man-pages/man7/cgroup_namespaces.7.html)

## Acceptance gaps to close before implementation/review

- Replace the placeholder requirements/design/test plan with these decisions,
  especially rounding and unknown-evidence behavior; neither is yet specified.
- Fixture cases: affinity22/quota2 -> 2; affinity2/quota8 -> 2; fractional,
  unlimited, malformed, unreadable, missing, affinity failure, and cap28.
- Test actual path resolution: nested v2/v1, tighter parent, unlimited child,
  combined v1 controller mount, nonstandard/escaped mount point, mount root
  `/slice` with membership `/slice/job`, namespace `/`, unrelated mounts,
  component-prefix collision, and unresolved `/..` without outside reads.
- Test absent v2 leaf with finite parent; true root with no `cpu.max` must not
  be mistaken for corrupt data. Pure fixtures must hide the host's real quota.
- Preserve explicit0/2/64, environment precedence, missing opt-in, and child
  behavior; assert those paths do not consult Linux capacity discovery.
- Retain PR135 core/Trust/CLI and measured-coverage fallback checks. Tests that
  demand parallel workers or xdist pin rejection must explicitly model cleanup
  support; current PID expectations check importability alone. Capability-seam
  simulation does not establish native Windows execution qualification.
- Keep existing failure, coverage, collection, timeout, and cleanup regressions.
  No PID/memory-budget policy, dynamic quota monitor, new dependency, service,
  image, deployed Trust policy, or selective-verification feature belongs here.

Quota is shared bandwidth, not guaranteed idle CPU or process headroom. Sample
once per selection; rollback remains `GROK_TEST_WORKERS=0`. All findings above
are static design evidence and require the writer's fresh RED/GREEN evidence.
