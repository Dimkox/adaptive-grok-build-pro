# M3 Tasks 1–7 implementation evidence

This ledger records local source and independent task-review evidence through product head `73a45d1feea639247fe5f66052f4a72cd6e98f9a`. The Task 7 approval is recorded by review-only commit `e7c903d837af437904b2e43a909b9e1a5bb67fc6`. These commits prove the implemented M3 behavior described below; they are not the final Task 8 verifier/review fingerprint, a `GovernanceHandoffV1`, merge authority, or deployment authority.

## Reviewed task checkpoints

| Task | Exact reviewed product checkpoint | Implemented behavior | Focused evidence retained from implementation and re-review |
| --- | --- | --- | --- |
| 1 | `491a91c260886923850e5b9ea370a13f70cdb74d` | Four closed schemas, canonical empty registries, strict nullable type-union support | 5 focused and 35 relevant tests; independent re-review approved |
| 2 | `3e2bb0c7a25c4c3df15578ef8bf3bc757afabc78` | One-root bounded no-follow loader, strict parsing/paths/limits, canonical digests, schema-reference fail-closure | 14 focused and 49 relevant tests; Ruff/Bandit; independent re-review approved |
| 3 | `33e5212dd5f89e553647f8b013511f0cc80d1ba2` | Reviewed lifecycle, human-governance activation gate, live evidence, deterministic conflict/effect selection | 12 focused and 61 relevant tests; provenance forgery repairs independently approved |
| 4 | `83bb253abca043eecf97d35e740e96c5d4dced8e` | Canonical-example/debt semantics with repository claims kept non-authoritative | 11 focused and 72 relevant tests; external-authority and malformed-evidence repairs independently approved |
| 5 | `d5a36c07f05558edd39fd3a15ddf91227b626b77` | Exact six-field handoff, independently derived M2 evidence, deterministic read-only projections | 7 focused and 79 relevant tests; 15-field evidence-forgery repair independently approved |
| 6 | `9dc89afe9b1e9c1751c3d309cce82b6a60507158` | Executable M3 architecture boundary and governance promotion fitness | 8 focused post-repair tests, exact diagram projection, Ruff; complete-schema freeze independently approved |
| 7 | `73a45d1feea639247fe5f66052f4a72cd6e98f9a` | Governance verification/receipts, installer/docs integration, durable adoption, architecture snapshot and final-fingerprint binding | 8 exact implementation/adjacent tests and 3 exact independent re-review regressions; Ruff/Bandit/compile; approved in `e7c903d` |

The Task 7 exploratory 160-test integration run is not represented as green: it completed 158 tests successfully and exposed two inverted test expectations, whose exact corrected cases then passed. A later two-module run was stopped and is not evidence. Task 8 still owns the one final broad verifier and all four route-selected reviews on one final fingerprint.

## Current deterministic source digests

The following values were re-derived from the clean `e7c903d` product tree before this package-only Step 1 edit:

- Architecture digest: `f05c557491bf0ade09d4331141c38cc31f66bd21d28a411f7de6cc54ef8a76bc`.
- Governance digest: `dfb2631cf1d47deaea71dec2d576adb72182f55401f12517333d2fff13355463`.
- Governance schema aggregate digest: `1c23d4009c40be40bd1852b4067cdf152b27920ee2b0c823991ff0a34ead174d`.
- Rule/debt/example component digests: `6f322d5b4966e873fd19792e70ac3be519bb879b660696f8ad10c0c4c4fcaf21`, `f8a91ea186fb3b83e2616a2e7448c23f3f3955486216a810707da3fb888c7b62`, and `f70a171a861646dbb906cc880f592e3a54d1c3e1d8b38be97e3ca19095140874`.
- Loaded handoff-schema component digest: `f3cd912607444a1a2a40333f523d586e96947050d94ee7591dd3a273963fd71f`.
- Frozen complete v1 handoff-schema semantic digest used by architecture fitness: `3527385869bc73f628e1dc0e22025d3e54b7e3972aba3703f9b579146a8c80ba`.

This documentation commit changes the exact Git head, so it deliberately does not publish or claim a current `GovernanceHandoffV1`. Task 8 must rederive the clean final head/base, architecture evidence, governance evidence digest, repository fingerprint, and final handoff after package preparation and before reviews.

## Authority and security boundary

- The checked-in registries contain no active rules, active examples, open debt, reviewer, or approval identity. Repository-authored actor/status/evidence fields remain claims, not human or external authority.
- The exact committed `GovernanceHandoffV1`, worktree-local governance receipt evidence, and the App-owned Trust CI exact-PR-SHA verdict are distinct domains. None substitutes for another.
- The installer distributes the engine, CLI, schemas, and non-authoritative templates, but never creates or overwrites target-owned governance registries.
- M3 adds no provider execution, factory runtime, PostgreSQL state, systemd unit, credential path, network capability, Trust CI mutation, external write, merge, release, or deployment operation.
- M4 is the next separate stacked PR and may consume only current exact M1/M2/M3 handoffs. M5–M9 remain roadmap/design only and require their own dependency-ordered changes and authority gates.
