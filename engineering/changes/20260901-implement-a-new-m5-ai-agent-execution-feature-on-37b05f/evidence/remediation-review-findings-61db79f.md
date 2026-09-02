# Exact-61db79f Independent Review Remediation Ledger

Review target: `61db79f07904ae5facb244c34b26c8383504dd88`. Both independent reviews concluded FAIL with no Critical findings; this file preserves their Important findings and does not record or imply a PASS receipt.

| Slice | Acceptance condition | Required regression evidence | Status |
| --- | --- | --- | --- |
| Architecture ownership | all eight M5 execution sources have explicit local owners, no undeclared drift, and no provider/DB/Git/scheduler/external authority | architecture validate/drift/diagram plus root architecture/structure tests | fixed by `542e494405ef20e6e44a4f5be1ad19e124ad3ce4` |
| Trusted selection and claim cleanup | caller eligibility/profile/policy/plan cannot create trust; current Codex/Grok conformances remain ineligible; reader write capabilities fail; failed packet persistence releases lease/capacity; submitted role must match durable role | adapter/service RED-GREEN plus disposable PostgreSQL forged-role test | implemented, awaiting this slice SHA |
| Proposal lifecycle and evidence | sequence is monotonic and bounded by `max_events`; exact replay precedes terminal rejection; no later effect follows terminal; structured secrets/reasoning are rejected or redacted; note/artifact paths bind packet policy; bridge artifact evidence requires trusted attestation | broker/protocol/service/PostgreSQL adversarial tests | open |
| Canonical persistence and terminal transition | SQL uses NULL-safe exact cross-field checks; runtime cannot persist noncanonical packet/manifest/result facts; terminal result alone derives the compatible M4 outcome without caller mismatch; failure class/reason survive | migration/store/PostgreSQL mutation, replay, rollback, and direct-capability tests | open |
| Result query integrity | requested digest, row PK/redundant columns, terminal proposal kind, packet, manifest, snapshot, and result all recompute and cross-bind; corruption fails closed | post-release/restart/cross-repo/corruption PostgreSQL tests | open |
| Recovery | cancellation/orphan reconciliation closes M5 stage/manifest state, releases capacity exactly once, and never fabricates a completed WorkspaceResult | recovery/restart PostgreSQL tests | open |
| Contract closure | nested schemas and event payload variants are closed; execution schemas and OpenAPI request/response contracts are inventoried | schema validation, OpenAPI, architecture inventory, structure tests | open |

Locally unavailable rootless OS isolation and a trusted live Git snapshot broker remain separate exit blockers; source-only fake evidence cannot satisfy them.
