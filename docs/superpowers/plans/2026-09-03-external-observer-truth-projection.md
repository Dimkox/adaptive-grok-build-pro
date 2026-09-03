# External Observer / Truth Projection v1 implementation plan

This plan implements the [approved design](../specs/2026-09-03-external-observer-truth-projection-design.md) as a separate operator-owned read-only service/domain, not a controller, Factory or Trust CI component. Goal/requirements/design/plan/schedule are frozen before code; local implementation follows; SHA-bound evidence is written only after a frozen implementation commit.

## Hourly critical path (UTC+3)

| Window | Work | Exit |
| --- | --- | --- |
| Sep 3 16:45-18:00 | Freeze EO-001..EO-010, architecture, contracts, adversarial matrix, rollout/rollback | docs-only commit; no implementation claim |
| Sep 3 18:00-19:00 | RED contract/config/claim/output canonicalization tests | deterministic failures for absent module/contracts |
| Sep 3 19:00-20:00 | GREEN local claims, typed projection, canonical JSON/text renderer | no network; closed bounds and stage separation |
| Sep 3 20:00-21:00 | GREEN fixed fake GitHub transport, PR/check/release/tag/compare coherence, runtime stale recovery | no external test traffic or writes |
| Sep 3 21:00-22:00 | Architecture/CLI/inert service integration and focused/full tests | exact implementation commit |
| Sep 3 22:00-23:00 | Exact-head verifier plus code/test/security reviews | fingerprint-bound local evidence only |
| Sep 3 23:00-Sep 4 01:00 | Bounded review remediation, refreeze and rerun | Observer source/review candidate; external acceptance still separate |
| Sep 4 01:00-05:00 | M4 final descendant/external gate; M5 source may prepare only provisionally | accepted M4 required before accepted M5 restack |
| Sep 4 05:00-09:00 | M5 target start after Observer and accepted M4 | isolation/verification/review gates, or named blocker |
| Sep 4 09:00-12:00 | M6 target start after accepted M5 | semantic validation/repair evidence |
| Sep 4 12:00-15:00 | M7 target start after accepted M6 | immutable shadow bundle/durable outcomes |
| Sep 4 15:00-19:00 | M8 target start after accepted M7 | at least 30 eligible real human outcomes; cannot be synthesized |
| Sep 4 19:00-22:00 | M9 target start after accepted M8 | signed artifact, preview/canary/recovery, human production authority |
| Sep 4 22:00-23:59 | Exact-state reserve | report accepted state/blockers; never waive gates |

The deadline is `2026-09-04 23:59 UTC+3`. These are start/working targets, not completion promises or authorization for external writes.

## Future implementation tasks

1. Add RED tests and closed schemas for placeholder-only `engineering/external-observer/external-observer.example.json`, operator-provided config and canonical `PUBLIC_STATUS.v1`; reject unknown fields, invalid SHA/IDs, oversized values and cross-swapped config.
2. Add `.grok-stack/adaptive_grok/external_observer.py` with frozen records, canonical digest/rendering, closed PROJECT_STATE/typed-manifest/receipt claim adapters and independent implemented/reviewed/delivered/released projections. Do not parse free-form README authority; replace mutable README/START_HERE facts with observer links/run instructions and label PROJECT_STATE as historical claim/snapshot.
3. Add fake-only GitHub adapter tests for exact configured PR, expected Check Run name/App ID, direct/annotated newest release, release-to-main and merge-to-main compare proof, opening/closing identity rereads and stale-state recovery.
4. Implement fixed GET-only transport with URL/method/header/redirect/proxy/body/cardinality/strict-JSON/per-request/aggregate-deadline bounds. Tests monkeypatch transport and prohibit DNS/socket use.
5. Add `scripts/grok_observer.py` commands `observe`, `status`, `render` and `verify-state`; errors are fixed/redacted and commands perform no remote mutation.
6. Declare the distinct architecture node, owned config/contracts/runtime paths and its only public GitHub read edge. If an operator service example is added, keep it source-only/inert, nonprivileged and without credentials or install/enable hooks.
7. Run focused tests, contract checks, architecture validate/drift/diagrams, full baseline and `python3 scripts/grok_verify.py --mode pr`; freeze the implementation SHA before writing final evidence.
8. Run independent code/test/security reviews on the same fingerprint. Do not push, open/update a PR, merge, publish, deploy or call production without separate authority.

## Explicit non-goals

No GitHub Actions, webhook, polling of arbitrary repositories/PRs, GraphQL, git clone/fetch, token/cookie/proxy credential, remote mutation, source/pin update, PR creation/update/merge, release publication, Trust CI/human approval/attestation generation, Factory dispatch, M5 behavior, production write or historical milestone reclassification. Optional discovery lists cannot establish absence or delivery.
