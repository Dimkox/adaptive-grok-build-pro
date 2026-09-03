# Stable workflow synthesis

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

Change `20260903-implement-feature-add-stable-workflow-governance-c89309`, route `c893098ede04`.

## Outcome and scope

Add a deterministic local synthesis/readiness layer and an opt-in weekly read-only monitor for three pinned official upstreams. Every due sweep queues the newest qualifying stable release and bounded post-pin change/bugfix candidates for local review; it never executes upstream material or advances tracked pins.

In scope: typed DAG/convergence, digest-chained runtime evidence, snapshots, fixed GitHub GET adapter, CLI, inert systemd examples, architecture/docs, and bounded router matching. Out: credentials, arbitrary/remote writes, installs, copied upstream code, automatic source/pin/PR/push/merge/release/deploy, Factory/Trust/production coupling, or a second controller.

The user explicitly approved with `утверждаю stable-синтез` and clarified weekly latest-release plus post-pin changes/bugfix intake. Moving main is observation only; reviewed port, tests, and exact-SHA evidence precede a separately reviewed pin edit.

The superseding whole-program deadline is `2026-09-04 23:59 UTC+3`. Stable-synthesis closeout runs in parallel with M4 final-descendant preparation, but accepted integration remains M4 → M5 → M6 → M7 → M8 → M9; see [schedule](schedule.md). Source-complete is not externally accepted, and this package claims neither.
