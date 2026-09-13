# Independent code review — split B

Verdict: PASS for this bounded source-epoch and retained-layout slice. No blocking correctness or security finding identified in the actual diff and surrounding implementation.

## Reviewed identity

- Route: `0fd5ffd2100f`; change: `20260913-l5-split-b-sealed-source-epoch-and-retained-layo-0fd5ff`.
- Immutable source HEAD: `d4d070a2defd9d0f8921331e38fb746fc95f38fe`.
- Genuine route predecessor: `fb582c91cd80c042d26b7467679d27a295a2396b`. The actual PR stacks on A; subsequent A documentation corrections are merged ancestry, not a rewritten route base.
- Verified tree fingerprint: `455a0faf93a69d81645eb5d47e1bb64d8f8cb74dfc20415d2fc2db888de4288b`.
- Independent reviewer: `code_reviewer`; application write owner: `general_implementer`.

Read the active route, reviewer role, change requirements/architecture/test plan, actual diff from the genuine predecessor, all nine product/test changes below, surrounding renderer/source guards and evaluator, artifact packager and retained manifest/archive integrity validation. Inherited A documentation corrections were distinguished from this product delta.

## Findings and reasoning

The current sealed source is `fde60e040167c10975b00d11f578c4da6763069a` / tree `21817e70e079b772e1f3114a80dfc0320d1ada91`. Its deployment archive has **22** members: the existing 20 plus `analytics.js` and `analytics.css`. Source documentation is not included as deployment content. Renderer and evaluator identities/policy change with the approved source surface.

Historical retained layouts are selected by exact SHA/tree pairs: the previous `6990103` epoch has 20 members and the older `176efca` epoch has 19. Unknown and crossed pairs reject. Retention validates the recorded epoch rather than comparing every historical artifact to the new global member list. Manifest member count follows the selected list; exact sorted names, archive metadata, each member size/hash/provenance, artifact/evidence/evaluation bindings and private-file constraints remain checked. This avoids silently weakening integrity to accept arbitrary layouts.

Approved source analytics remains source owned: exact stylesheet/script/settings-anchor facts are preserved, only the existing two generated files may change, and all other candidate Git objects must equal the sealed source. Script inspection admits the required JSON-LD plus the exact approved analytics script and rejects additional script starts. Provider-generated content still passes through the closed spec and escaping renderer. The privacy text reflects the approved source analytics instead of making the old no-tracking assertion. This is a deliberate source epoch/policy update, not an added general script permission.

Source validation continues to bind exact Git HEAD and tree and now exposes a bounded dirty-source guard. Workspace creation, candidate identity, source snapshots and post-operation mutation checks remain in the existing execution path. No new provider/network edge, data migration, publication authority, or later split-unit runtime is assumed by this review.

## Verification examined

The completed `split-b-full-final.json` reports PASS for the exact HEAD, route and fingerprint above. All reported mandatory checks pass, including architecture/governance, secret/contracts/static checks, 653 core tests, coverage, factory tests, PostgreSQL verification with two actual restarts, and source stability. This review did not rerun that full suite.

A bounded independent rerun of `split-b-layout-characterization.py` passed against this immutable checkout. It derives the previous deployment list from the genuine predecessor and confirms 20/19/22 members, exclusion of source documentation, rejection of unknown/crossed epochs, and acceptance of the approved source surface. This is selector/source-surface characterization; it is not a claim that complete historical archive fixtures were reconstructed in this review. The existing retained-manifest validation code was inspected directly.

## Limits

This PASS is local independent review evidence for B only. It does not establish external exact-SHA Trust CI approval or merge authority. No later C evidence format, D HTTP runtime, E host, F publication or G backup source was used as a precondition for approval. No source edits, real credentials, network operations or operational grants were used.

## SHA-256 of inspected product/test delta

- `factory/src/adaptive_factory/landing_artifact.py`: `2452174a5d1e7188e3de0902534a0f9599583d6def0b673b2e2100850f5c42e3`
- `factory/src/adaptive_factory/landing_artifact_retention.py`: `19d138896f5f64b517468b4a575883f51f277950a92964143a273a3c62c04cc5`
- `factory/src/adaptive_factory/landing_evaluation.py`: `677d4d59e23731e912d89b6214b3d75dca9b98e343d4cf284ab21affea141741`
- `factory/src/adaptive_factory/landing_renderer.py`: `270b623ae19a01a9c97f6a1ea3874a02eac5fa1832ebf55a3d3f73facc48b8bf`
- `factory/tests/test_landing_api.py`: `41fdce38d6643d6a24bb505d513a5720079cea0263ad8424e8ca369110db49f5`
- `factory/tests/test_landing_artifact.py`: `7ca401cbb66c6a63bcd9c4e797d6b5f214709aa0b5a50a58d2512c464ec747c4`
- `factory/tests/test_landing_live.py`: `3795a2ba99c2f00f6d84f14beb67f67639848711c50334e4a11a647db005de0f`
- `factory/tests/test_landing_renderer.py`: `ecb087b7a38fa2c3d9432e1dd203c0abdd21ce5a493ba478524dd406b28da005`
- `factory/tests/test_landing_sqlite_store.py`: `07217325095ab1ea293b768a830a0acc125bf89d63cc05d1743617c56380c4ea`
