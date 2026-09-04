# Requirements — M9 staged delivery on corrected exact M8 a937ac8

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Closed immutable records bind exact repository, artifact, authority, policy, holdout, runner, environment, exposure, time, reason, and digest-chain identities and reject malformed, nonfinite, stale, duplicate, contradictory, or reordered input.
- [ ] The M8 seam imports real autonomy producer types and recomputes tuple, cohort, profile, and recommendation bodies/digests; caller overrides and duplicate M8/M7 authority are rejected, while durable acceptance/currentness remain false.
- [ ] Evaluation can advance exactly one authorized step from preview to staging to bounded canary; final canary and production always return `needs_human`, and production is unreachable to the adapter.
- [ ] The controller accepts only the exact sealed in-memory adapter, serializes concurrent identical calls at most once, rechecks expiry before recording, and appends a complete immutable digest chain bounded to 128 entries.
- [ ] Recovery can only halt, lower to the immediately prior authorized exposure, or restore the exact prior signed artifact; it cannot widen exposure, reverse stage, synthesize an artifact, or act on stale authority.
- [ ] No operational adapter, I/O, persistence, migration, network, subprocess, credential, provider, production action, or external effect is present.

## Failure and edge cases

- Empty prior evidence is the only locally trusted starting point; nonempty prior evidence requires a future trusted witness and is rejected here.
- Observation and evidence sequences must be materialized, bounded, consistently ordered, non-replayed, and linked to the exact preceding digest.
- Recovery reasons must be compatible with the selected narrowing action; contradictory or mixed reasons fail closed.
- M8 blocked bundles and unavailable durable acceptance/currentness keep staged advancement denied in this source-only integration.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: existing closed-contract, deterministic-evidence, least-authority, human-production-boundary, and local-isolation rules.
- Canonical-example deviations and evidence: canonical duplicate `m8_boundary.py` producer models are replaced by a thin bridge over actual integrated M8 types.
- Intentional debt created, repaid, or accepted: durable M8 acceptance/currentness, trusted prior-chain witness, operational adapter, signed real inputs, and environment/recovery proof remain explicit later gates.

## Non-functional requirements

- Security: no caller authority override, no secret material, strict signed-resource bindings, human production boundary, and least-authority recovery only.
- Reliability: immutable closed records, exact canonical digests/times, deterministic reason ordering, expiry/freshness checks, replay rejection, and locked at-most-once recording.
- Performance: every input sequence and evidence chain is bounded to 128; no I/O or unbounded traversal exists.
- Observability: every dry-run step returns a closed decision/recovery/evidence record with exact input, observation-set, prior-link, effect, and state digests.
