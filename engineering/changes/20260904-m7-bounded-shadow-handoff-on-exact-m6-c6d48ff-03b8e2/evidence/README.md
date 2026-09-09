# Evidence

Store human-readable review reports here. Machine receipts live under `.grok-stack/runtime/receipts/` and are bound to the current repository fingerprint.

Canonical final M7 `4df2516b` (true comparison base `9fe779a`) is semantic source material only. This change must remain a descendant of exact M6 `c6d48ffd8594b3baab1a575021452ea5dfa2a98b` and import only six schemas, two pure modules, and two focused tests from that source.

This phase permits repository-local edits and synthetic pure tests only. PostgreSQL, provider calls, network access, durable outcome claims, full verification, reviews, receipts, packaging, push, pull request, merge, tag, release, deployment, and every external or production action are deferred.

## Bounded source evidence

- Gate commit: `4b4b15c8266d1f039f8cba3949a04ef3e256f8e0`.
- TDD RED: the two canonical test modules produced exactly two loader errors because `adaptive_factory.shadow_contracts` and `adaptive_factory.shadow_evaluation` did not exist.
- Product commit: `dc5e68b0bda235e7a145252ea10715df59fd6cfe`; all ten product paths are byte-identical to canonical final M7 `4df2516b`, and the focused shadow group passed 30/30 in 0.194 seconds without rerun.
- Architecture commit: `77ae83357d3f9ad947f15e961c2e98d9280563bd`; architecture validation and repository drift reported zero findings, and generated diagram parity passed.
- Architecture after the additive M7 enrollment contains 24 nodes, 24 edges, 25 contracts, and 33 rules. Architecture digest: `6316db0a10ad60e8dbcb519e87b7f1132b4417d62bccc43237f6b310f941cc69`; contract inventory digest: `585f05b0ded1e388ffaf6cc73e6e3755fac882ec6369850bed8633849f71f0b0`.
- Diagram digests: container `d7c4fd7536eb3f881fb4e3fab7202fd66292c0ca4fac77cd1c92e26d5a3de73a`, deployment `87dd6f5afcc70c12d8cc77313375f9c3e92b7a029d252af2d2bd36f5d02791ed`, trust boundary `7ca835d331c754bfdfbd674f97d46ae09b82dc3b8c8aef2ae7c556b333f2a3a7`; unchanged context and data-flow digests remain `0e1db984bf9de1f8f1f752d43ffc71cb954d102ed024af7792e98f1d5e7d4626` and `099d6e46889cc899b5c1a53c58407ee3722a542c975e0fc96c164b101f85cdcd`.

## Deferred gates

The full exact-head verifier, independent code/test/security reviews, fingerprint-bound receipts, runtime or PostgreSQL integration, real human-outcome acquisition, durable lookup, packaging, delivery, and all external or production actions were not run. Synthetic fixtures do not constitute an earned-autonomy cohort or M8 evidence.
