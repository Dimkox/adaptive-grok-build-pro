# Stable workflow synthesis design

## Purpose

Extend adaptive delivery with a deterministic evidence-bound synthesis lens and weekly read-only intake of official stable releases plus bounded post-pin change/bugfix candidates. This is not another controller: active route, one writer, change-spec v2, reviews, and Trust CI retain authority.

## Model and boundary

Closed versioned upstream records feed immutable typed provenance. Pure finite lenses produce stable findings and either a complete atomic repair plan or terminal `ready|blocked|needs_human|iteration_limit`. Content-addressed snapshots and append-only CAS journal entries bind canonical component/config/intent/snapshot/prior digests under one descriptor-opened `flock` domain; the monitor never shells out to Git, and exact-SHA authority remains exclusively with Trust CI.

The distinct local-preflight monitor accepts only three fixed repositories and GET-only `api.github.com` release/ref/tag/head/compare URLs. It has no credentials, redirects, retries, arbitrary URLs, raw-body persistence, execution/install, remote/repository mutation, or Factory/Trust/production edge. Every completed attempt advances due by exactly 604800 seconds; failures become unknown/stale/degraded, never no-update. New releases and bounded candidates form a sanitized local review queue only; branch heads are observations and reviewed porting/tests/exact-SHA evidence precede pin changes.

CLI use is explicit. Systemd units are inert source examples without `WantedBy` or installer hooks. VERSION remains 2.0.13 because this is a local candidate, not an exact-SHA release.
