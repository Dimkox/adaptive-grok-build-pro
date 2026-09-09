# Evidence

Store human-readable review reports here. Machine receipts live under `.grok-stack/runtime/receipts/` and are bound to the current repository fingerprint.

## Scope inputs

- `analysis-repo_explorer.md`: exact lineage, add-only inventory, overlap map, and focused checks.
- `analysis-data_architect.md`: migration-018 byte identity, role boundary, transactional upgrade, and critical database evidence.
- `analysis-ai_architect.md`: deterministic semantic/repair behavior and no-application-write boundary.

Canonical M6 `2d2360cd6f2a19ad3328d468073a52927691b112` is source material only. All evidence must be regenerated on a descendant of exact M5 `85cd4343143915ce9342634e7fe81886b6394871`. This phase authorizes repository-local source and disposable local PostgreSQL 17 only; no receipt, external, delivery, or production authority transfers.

## Bounded source evidence

- Gate commit: `a52b9bb767b0dddfd091a9d0adb4a17a96ce5d9a`.
- Deterministic semantic core commit: `3434fcf211bcf9d0fa0439d88ee0d110b7aa86e6`; TDD RED was four missing-module import errors, followed by 35/35 pure semantic tests passing.
- Runtime and migration commit: `6527bd46d655a270435e4c3f51ef12d6b8ef7832`; 21/21 persistence, store, service/API, and repair-lifecycle tests passed.
- The original control-contract checkpoint `6620ac040ab2f712a657f0df2cf469ed86c203c2` incorrectly placed six semantic route-method pairs in the frozen M4 document. The corrected predecessor retains the exact 17-operation M4 bytes and declares the six M6 route-method pairs in `factory-semantic.v1.json`; M5 execution v1/v2 remain separate.
- Architecture/test checkpoint: `c393b75573512ed1548a4a68a1e2339b59413264`; architecture validate and drift reported zero findings, diagram parity passed, and the resulting model contains 23 nodes, 24 edges, and 19 contracts.
- Final M5 compatibility repair commit: `50b8c5351d7347fbba0ce63586250836f7f06999`; the three selected PostgreSQL semantic methods pass on disposable PostgreSQL 17. One passed on the first run; two canonical expectations were adapted to final M5 semantic-identity and exact-command replay, after which only those two failed methods were rerun and passed.
- Migration `018_semantic_validation_bridge.sql` is 2,154 lines with SHA-256 `33053563dce7c34edfa9301130272adb34651d44dd1f2bc305ba3eec01382c70`; migrations 001-017 and both execution OpenAPI contracts remain unchanged from exact M5.
- Focused non-database evidence: 4/4 server semantic-composition tests and 6/6 architecture/OpenAPI structure tests passed. The one failing migration-inventory method exposed two sequential stale M5 count assertions; only that method was rerun after each correction and it passed, yielding 4/4 selected migration tests.

## Deferred gates

The full exact-head PR verifier, route-selected independent reviews, receipt recording, schema-17 populated upgrade fault injection, restart probe, full factory suite, packaging, pull request, release, deployment, provider calls, and every external or production action were not run in this bounded source phase. They remain separate gates and require the applicable route phase and authorization.
