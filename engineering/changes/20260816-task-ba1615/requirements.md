# Requirements

- [x] Root `decisions.md` exists and contains the previous `engineering/decisions.md` entries.
- [x] Root `mistakes.md` exists and contains the previous `engineering/mistakes.md` entries.
- [x] `AGENTS.md` first `##` section says `log it in decisions.md` and `record it in mistakes.md` (no `engineering/` prefix).
- [x] Structure test fails if either root file is missing or if `AGENTS.md` still names `engineering/decisions.md` / `engineering/mistakes.md` as the live sinks.
- [x] `engineering/decisions.md` and `engineering/mistakes.md` are pointers, not a second log.
