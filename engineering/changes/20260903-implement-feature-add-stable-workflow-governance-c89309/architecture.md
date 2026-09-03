# Architecture — stable workflow synthesis

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

This additive layer uses pure typed lenses to produce deterministic findings and one complete repair plan or a bounded terminal result. Content-addressed snapshots and append-only journal entries bind controller version, exact HEAD/tree and canonical prior/input/output digests. Ignored runtime state reuses repository lock and atomic fsync/replace patterns.

`NODE-STABLE-SYNTHESIS-MONITOR` in `TD-LOCAL-PREFLIGHT` owns module/CLI/config/unit paths and has one fixed GET-only HTTPS edge to `NODE-GITHUB` plus local runtime state. There is no Factory, Trust CI, production, secret, or repository-mutation edge. Release/tag/head/compare URLs derive solely from closed config; incomplete observations become degraded/unknown/stale, never no-update.

Rollback disables manual scheduling and forward-fixes/reverts the additive reader while retaining runtime evidence. Existing adaptive delivery, change-spec v2, pins, Trust CI, Factory and production stay unchanged.
