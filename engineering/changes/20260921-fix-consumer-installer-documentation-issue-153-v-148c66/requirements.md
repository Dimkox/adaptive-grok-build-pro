# Acceptance and invariants

[change-spec.yaml](change-spec.yaml) is typed authority.

- **AC-001:** Installed factory/README.md remains managed; every relative link resolves in the materialized consumer and upstream-only documentation uses explicit HTTPS links.
- **AC-002:** Installed managed instructions require only shipped files and mark consumer-owned bootstrap/state/version/architecture/shared-memory files conditional; no factory deployment identity is copied.
- **AC-003:** managed_agents_text and build_payload render identical consumer content through the bounded reader; generic/Bitrix payloads are deterministic with correct rendered hashes.
- **AC-004:** Existing-target plans preserve user AGENTS prefix/suffix and old managed markers byte-for-byte; kept_local conflicts and materialize-new refusal for existing targets remain.
- **AC-005:** Consumer instructions retain one writer, independent review, PR-only delivery, exact action/resource consent, secret/private-key restrictions and external merge authority.

- **INV-001:** Descriptor-backed source safety and target ownership remain intact.
- **INV-002:** Factory-root AGENTS/README and Bitrix local/AGENTS behavior remain unchanged.

Forbidden outcomes:

- Copy factory PROJECT_STATE, deployed policy, private material or runtime observations into a consumer.
- Silently delete a formerly managed README, overwrite user instructions or add an updater.
- Claim hook registration, language coverage or live activation is fixed.
