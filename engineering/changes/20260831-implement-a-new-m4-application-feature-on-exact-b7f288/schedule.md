# M4 Delivery Schedule — Superseded Calendar, Current Recovery Gate

All times are UTC+3. The original M4 implementation window ending `2026-09-02 18:00` is missed and retained only as historical planning. At the `2026-09-03 11:03` observation, about 109 hours remain to the hard deadline **2026-09-08 00:00 UTC+3**; normal work still freezes at `2026-09-07 20:00` for exact-state gates.

PR #21 is OPEN/BLOCKED at `571cad7877431ac5ab5779b53fe9f7effd6859ce`. Its App-owned check failed `root-unittest` because package Git helpers scrubbed configured `safe.directory` under the differently owned UID-10001 runner checkout; GitGuardian also reports FAILURE, whose finding content is not inspected or inferred. Local source repair `3b1f9a54a964d91f34cee2628374b17e7a42edeb` and rebuilt package candidate `9727bc30c82bb44a86db0ef5b62e507b5527207a` were committed at `2026-09-03 03:15-03:16`, with root 537/537 plus focused different-owner/package checks green. Candidate `9727bc3` is not pushed or externally rechecked. Current docs/package parity may create a later candidate SHA; nothing here promises `9727bc3` as the PR target.

| Current recovery step | Target | Gate |
| --- | ---: | --- |
| M4 docs/package parity | immediate | rebuild package if source inventory changes; exact archive/sidecar/source agreement |
| M4 local refreeze | after parity | final exact-head verifier and five refreshed route reviews |
| PR #21 update | separately authorized | push only the final verified candidate; no direct protected-branch write |
| External recheck/merge | after PR update | fresh `adaptive-trust-ci/verified@06ecf1c875bc` success on exact up-to-date head plus required signed scopes |
| M5-M9 continuation | dependency ordered | restack from final accepted predecessor; do not carry stale SHAs or receipts |

The broader compressed M5-M9 windows live in the [active M5 schedule](../20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f/schedule.md). The pending M4 external rerun, M5 trusted rootless broker/live OS isolation, and M8 cohort of at least 30 eligible real human outcomes are deadline-critical blockers. Calendar pressure never waives the App-owned check, signed scopes, immediate-predecessor fitness, database/restart evidence, cohort, or production authority. If a gate misses its window, report it rather than claiming completion.

Cross-links: [root current state](../../../README.md), [roadmap](../../../DARK_FACTORY_ROADMAP.md), [release](release.md), [rollback](rollback.md), [factory package](../../../factory/README.md).
