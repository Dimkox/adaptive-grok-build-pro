# Requirements — stable workflow synthesis

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

- AC-001 closed v1 config has exactly three official pins, tag-object/peeled SHAs, URLs and MIT attribution.
- AC-002 typed deterministic lineage, DAG/transitions/findings, bounded convergence, atomic repair, snapshots and resumable digest journal.
- AC-003 exact 604800-second UTC schedule; not-due/contention no I/O, attempts advance due, rollback clock waits.
- AC-004 fixed GET-only GitHub source/path/method/timeout/run/body/JSON/call bounds; no credentials, redirect, retry, proxy, arbitrary URL, subprocess or write.
- AC-005 newest stable release resolves direct/annotated tags to terminal 40-hex commit; cycles/non-commit rejected and cached releases still recheck tag.
- AC-006 every sweep reports all post-pin count plus bounded sanitized head/compare candidates and explicit truncation/partial status.
- AC-007 atomic ignored state distinguishes unknown/stale/review_required/degraded/unavailable/converged; corruption fails closed.
- AC-008 explicit CLI and inert units cannot install/enable or mutate Git/source/PR/Trust/Factory/production.
- AC-009 architecture has a distinct local monitor and only allowlisted read-only GitHub/local-runtime edges.
- AC-010 router uses bounded terms, avoiding `documentation` feature masking and `ui` inside words.
- AC-011 fake-only tests preserve the baseline suite.

Invariants: active route/one writer/Trust CI remain authoritative; external strings are untrusted data; pins require reviewed tracked changes/tests/exact-SHA evidence; VERSION stays 2.0.13.
