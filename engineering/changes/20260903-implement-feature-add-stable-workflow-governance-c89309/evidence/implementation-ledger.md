# Implementation ledger

## Design gate and RED — 2026-09-03

- Five route-selected read-only analyses were frozen before implementation.
- Requirement ruling: safety constrains execution authority, not observation coverage; AC-006 explicitly covers both stable releases and post-pin head/compare change candidates.
- Approval: user said `утверждаю stable-синтез`; draft→scoped→approved→implementing transitions record that scope.
- Gate: `python3 scripts/grok_spec.py validate .../change-spec.yaml --gate` → PASS, 11/11 criteria mapped.
- RED: `python3 -m unittest tests.test_stable_synthesis tests.test_stable_monitor tests.test_stable_integration` → 3 tests, 3 errors: synthesis module and inert unit files do not exist. This is the expected pre-implementation failure, not an environmental error.

## Implementation and remediation — 2026-09-03

- Product checkpoint `47adcfef101757ab378dd3cd656c7147ce7e9311` implemented the additive controller lens, official-source config, fake-transport monitor, CLI/inert unit, architecture and bounded router matching.
- First full run: 571 tests, 1 failure and 16 errors. Root cause was placing architecture-enrolled contracts outside the canonical `engineering/contracts` tree copied by isolated architecture fixtures, plus leaving the exact complete-graph fixture at K22; moving the single SSOT into `engineering/contracts/schemas` and upgrading the exact K23/253 expectations repaired the fixture contract without weakening assertions. Regression slice: 155/155 PASS.
- Security RED reproduced exact-authority cross-swap acceptance, unbounded journal `read_text`, corrupt/symlink state treated absent, snapshot symlink acceptance, one-level-only tag peel, absent directory fsync, case-sensitive response headers, unconstrained release tags, systemd runtime-lock denial, raw successful release persistence, Unicode controls in subjects, and journal reserved-field override/open shape.
- GREEN: strict exact per-source authority binding; closed typed journal with bounded streaming replay; strict regular/no-follow state and snapshot checks; bounded visited-set tag peel; local directory fsync; case-insensitive bounded headers/ETags; bounded tag syntax; normalized three-field release cache; Unicode-control stripping; and runtime-root systemd write scope. Focused stable/router suite 51/51, Ruff PASS, Bandit PASS, architecture validate/drift/diagram parity PASS.
- Final full root suite: 578/578 PASS in 383.962 seconds. No test used GitHub; all monitor behavior used fake transport. Route base was corrected to exact predecessor `7748a8b795ad057295c988e00f627afdc50dbf80` while preserving the clean-predecessor fingerprint.
- Architecture fitness RED after the correct rebind: the pins instance and journal pseudo-metadata had been incorrectly enrolled as JSON Schema/event schemas, so their self-comparison had unsupported baseline semantics. GREEN moved the immutable pins instance to `engineering/stable-synthesis/`, introduced a real closed Draft 2020-12 config schema, replaced journal metadata with a real closed entry schema, retained Python cross-field/chain authority, and proved both enrolled contracts self-compatible; impacted architecture/installer/stable tests 101/101 and exact-base fitness PASS.
- Final post-schema focused stable/router suite: 52/52 PASS; Ruff and Bandit PASS. Strict JSON additionally rejects non-finite values, and journal timestamps are finite/nonnegative in both runtime validation and schema.
