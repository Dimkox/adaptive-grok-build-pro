# Requirements and result

Typed criteria remain in [change-spec.yaml](change-spec.yaml).

- AC-001: both existing services accepted on target source — unmet; Grok passed, Qwen rolled back after rejection.
- AC-002: bounded stopped-writer snapshots and safe schema transition/recovery — passed; both snapshots and counts retained, Qwen full restore exercised.
- AC-003: exact-profile, same-job durable artifact acceptance — passed for Grok, failed for primary Qwen Omni.

Preserve existing data, original units/configs and separate Omni. Use one provider submission per service; no replay, public-site publication, release tag or Trust CI infrastructure mutation. A partial upgrade must remain visibly incomplete. User deployment delegation and exact local grants are operational permission, not external merge authority.
