# Documentation analysis — automatic Qwen → Grok failover

Route `24b49d0529c8`; source baseline `7b147366a1f9b7e4b59f17e10283cc8ad67ba0c8`.
Design evidence only. The named `scope_and_design_approval` gate remains pending; no implementation, model call, credential access or runtime mutation occurred.

## Scope wording

Proposed outcome: one durable operator CLI submits eligible text/safe-DOCX landing requests to the existing Qwen primary, then at most once to the existing Grok secondary when the primary was demonstrably not submitted or records an eligible terminal provider failure. No additional daemon is required. Unknown outcomes after submission require read-only reconciliation; unresolved uncertainty stops automatic dispatch.

Explicitly distinguish three facts: existing separate hosts already generate artifacts; automatic cross-host routing is proposed; operational installation and use of the shared CLI are not established by source delivery. Direct backend socket callers retain their existing single-provider behavior.

## Documentation changes after approved implementation

- `engineering/runbooks/l5-production-runtime.md:37`: qualify the blanket no-fallback statement as the direct backend/executor contract; describe the shared CLI's ordered, policy-controlled cross-host selection separately. Preserve exact model matching and unsupported-media rejection.
- `engineering/runbooks/l5-production-runtime.md:41`: retain transport no-retry and per-profile ceilings; document the caller's additional total attempt/time ceiling without implying that two provider attempts cost the same as one.
- `engineering/runbooks/l5-production-runtime.md:45`: retain no automatic replay on Grok usage rejection. Document that missing failed-attempt usage is unknown, not zero; a completed Grok rejection cannot start a third attempt.
- `factory/README.md:51`: distinguish pinned direct profiles from the new shared entrypoint; remove a future contradiction with the present global “Region or model failures do not cause automatic fallback” wording only after implementation.
- `factory/README.md:57,76` and runbook `:51,55`: retain backend-specific configuration, credentials, sockets and default-off installation semantics. Add the shared CLI's own closed config/journal/spool documentation and scoped service-token requirements; the CLI needs no provider API keys.
- `factory/runtime/landing-host.example.json:12–13`: keep the independent default-off Qwen Omni template. Do not silently make it the fallback configuration; the initial shared route explicitly pins `qwen-intl`/`qwen-plus` followed by `grok-vision`/`grok-4.6` and accepts only their approved text/DOCX scope.
- `engineering/runbooks/l5-runtime-observation-2026-09-15.md:9–19`: preserve this dated observation unchanged. Its two successful jobs prove independent hosts, not failover; add a separately dated record only after an authorized installed failover test.
- Add CLI submit/status/resume examples after command names and schema are finalized. Explain stable request keys, different-input conflicts, private spool retention, safe reason codes, winner artifact lookup, and rollback to direct entrypoints while preserving unresolved journal records.

## No-retry invariant

`landing_live_executors.py:150` promises one bounded request to one pinned provider, and `landing_http.py:61` includes `no-retry` in the policy identity. This remains valid for each backend attempt. Document fallback as a separate ordered attempt through the caller, never an executor retry or silent provider/profile relabeling. Changes to evidence/error semantics must receive their own reviewed identities rather than changing descriptions alone.

## Acceptance wording for the design package

- Qwen success selects its artifact and performs no Grok submission; proven pre-submit connection refusal permits one Grok attempt.
- Only enumerated, durably terminal provider failures permit fallback. Caller authorization, tenant/source mismatch, policy/media rejection, local rendering/evaluation/storage failure, or an existing artifact do not.
- Lost POST responses, timeouts after dispatch, caller crashes, and an inconclusive status lookup never alone authorize another provider call. Resume checks the same child identity; terminal replay returns the selected result.
- Concurrent/repeated logical requests cannot multiply submissions. Record at most one attempt per provider, exact winner evidence, known usage plus explicit unknown exposure, and bounded elapsed time.
- Preserve existing backend v1 response shapes and retained v1/v2 evidence; add versioned attempt-status/storage contracts. Both-provider failure remains explicit, with no automatic publication and `live_url=null`.
- Verify the decision table and crash boundaries offline first. Source verification does not claim an installed runtime test, public-site publication, general coding fallback, Omni international support, M8 activation or M9 qualification.

## Design-gate clarification

Present the CLI entrypoint and conservative ambiguous-outcome behavior as concrete design choices for approval. Avoid “switch whenever Qwen dies,” “exactly-once billing,” or “all provider errors retry on Grok”: these exceed the proposed guarantees.
