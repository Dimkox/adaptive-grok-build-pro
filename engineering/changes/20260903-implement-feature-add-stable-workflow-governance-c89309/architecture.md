# Architecture — stable workflow synthesis

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

This additive layer uses pure typed lenses to produce deterministic findings and one complete repair plan or a bounded terminal result. Content-addressed snapshots and append-only journal entries bind component/config/intent/snapshot/prior digests; the journal is authoritative and repairs an absent or stale state projection after a crash. Ignored runtime state uses one monitor-specific descriptor-opened `flock` domain and descriptor-relative fsync/replace, while exact Git SHA remains a Trust CI concern and runtime never invokes Git.

`NODE-STABLE-SYNTHESIS-MONITOR` in `TD-LOCAL-PREFLIGHT` owns module/CLI/config/unit paths and has one fixed GET-only HTTPS edge to `NODE-GITHUB` plus local runtime state. There is no Factory, Trust CI, production, secret, or repository-mutation edge. Release/tag/head/compare URLs derive solely from closed config; compare remains anchored to the frozen peeled pin, validates GitHub topology, and makes divergence/inconsistency degraded or review-required rather than converged.

Rollback disables manual scheduling and forward-fixes/reverts the additive reader while retaining runtime evidence. Existing adaptive delivery, change-spec v2, pins, Trust CI, Factory and production stay unchanged.
