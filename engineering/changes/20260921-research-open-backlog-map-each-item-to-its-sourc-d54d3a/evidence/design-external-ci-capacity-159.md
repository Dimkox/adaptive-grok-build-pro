# #159 — operator-owned Trust CI throughput qualification

Research route `d54d3afd1c92`; execution packet for source preparation and operator decision. This packet authorizes no live mutation and supplies no signed human approval. Source checks, local grants and PR artifacts remain separate from deployed merge authority.

## Required outcome and bounded choice

Measure the real queue and reduce waiting while preserving exact head/base checks, policy epoch, holdout binding, image identity, source-mutation detection, scoped human approvals and fail/abort classification. September 20’s 14 stale PRs and 21-minute runs are historical observations; refresh them before choosing capacity.

Recommended first candidate is a second isolated worker with unique identity and resource budgets. It is a proposal, not a requirement already approved by the issue. PostgreSQL claim already uses `FOR UPDATE SKIP LOCKED`, but that alone does not prove safe shared workspaces or container cleanup. A merge train and input-based check reuse are optional architectural alternatives; do not start them in the concurrency slice or relax exact-SHA evidence.

## Preparation sequence and acceptance

1. Collect read-only safe facts: worker count, host CPU/memory/PID/storage limits, timestamped queue depth, exact job start/end/aborted times, PostgreSQL tier concurrency and per-run temporary/container/workspace identity. No keys, secrets, dumps or deployed policy modifications. Publish the observed scope and expected queue model, with date and caveats, in `trust-ci/README.md` or an operator runbook.
2. Review prerequisite candidates against current main: #59 remains local-only and cannot be assumed shipped; #128/PR143 cleanup, #158 adopted-orphan reaping, #155/PR170 timing determinism, and #132 cancellation classification. Resolve overlapping ownership before qualification. Do not require unrelated backlog to finish.
3. Add bounded source-only tests/fixtures proving two workers cannot claim the same active lease, reclaimed work is fenced from old owner effects, job checkout/container/tmp paths cannot collide, cancellation cleanup cannot remove another worker's resources, and aggregate limits cap actual database tiers. Start with synthetic stores/paths, then route-selected disposable integration evidence in an authorized environment.
4. Produce a concrete external rollout proposal: exact image/source digests, worker IDs, host paths, per-worker and aggregate limits, desired worker count, canary duration expressed as measured completed jobs, stop criteria and revert command/resource list. Any policy epoch/holdout/image/base change requires fresh checks and required approvals; no old green result carries forward by fiat.
5. After separately authorized operator rollout, observe multiple concurrent jobs and cancellation/recovery, report queue/run latency versus baseline and verify exact-head checks/attestations. Demonstrate no shared state collision and no zombie/resource growth. Automated PR rebasing/merging is a separate feature and requires its own exact write authority; increasing workers alone does not satisfy “no manual babysitting.”

Likely source files: `trust-ci/src/adaptive_trust_ci/{worker,store,workspace,sandbox,lease,runner}.py`, SQL lease functions only if a proven fencing defect demands them, corresponding Trust CI tests, and docs/runbook. Do not edit all these files speculatively. Deployed compose/worker configuration is outside the PR trust domain even if a similarly named repository example exists.

## Exact external gate and recovery

Before live change, the operator must explicitly authorize the exact host/service/config/image resources and operation; required human security scopes must be signed on a human-controlled machine and verified by the external service. Agent must never read/request/create/sign with an approval key or change deployed trust stores, GitHub App configuration, branch protection, holdout or policy through a source PR. If the proposed operation is outside current delegated authority, stop only its external execution and hand over the prepared proposal; source preparation can finish.

Stop criteria: any duplicate lease execution, cross-job cleanup, unexpected attestation identity, unexplained verdict change, resource exhaustion or growing queue under equal load. Recovery drains/stops the added worker with exact operator authority, preserves durable jobs/evidence, lets leases recover under existing semantics, and returns to the previous known image/count. Never delete PostgreSQL rows or reuse a revoked/stale attestation to drain the queue.

Optional alternatives must be separately designed: a merge train needs combined-tree exact identity and failing-member blocking; selective attestation reuse changes what is trusted and needs an explicit deployed-policy decision. Neither is a low-risk substitute for measuring capacity.
