# Installer keep list for consumer-owned policy files (#110)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

`MANAGED_*` says what the stack owns; nothing said what the target overrode, so refresh silently re-collapses consumer policy (coverage scope, security skips, host-sized routing cap) — a real consumer sync already misreported itself because of it. This wave adds `.grok-stack/AGBP_SYNC.json` `kept_local`: the plan reports `KEEP <path> (declared by target)`, delivery skips it, drift fails the plan by name. No record — the previous behavior, byte for byte.
