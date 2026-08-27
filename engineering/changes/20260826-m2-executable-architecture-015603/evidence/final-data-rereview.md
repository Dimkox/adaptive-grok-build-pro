# Final data and contract re-review — M2-A fix wave

## Exact identity

- Route: `0156034c05bd`
- Change: `20260826-m2-executable-architecture-015603`
- Adoption base: `25bfbe59ea188d9687b20a9caad19e7db3d031f8`
- Prior reviewed head: `99de2f9757400f7394b7a9e2c46b3ebce939e438` (tree `bae34faabdf968396e393d40f7219d3bbf5a60b5`)
- Fix head: `fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d` (tree `962d7f858fbf7754dd0f800e65a8f41f8ba5f983`)
- Prior-to-fix merge base: `99de2f9757400f7394b7a9e2c46b3ebce939e438`
- Exact diff package: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-99de2f9..fd5f7eb.diff`
- Diff package SHA-256: `ac1aba14c8498f1c3d1fd6fbd9de7ef7557b09c8c14c9461ce7d5921a3acca54`

## Verdict

**BLOCKED — 0 Critical, 1 Important, 0 Minor.** Both original data-review findings are **ADDRESSED**, but the fix wave introduced one new Important contract-truth breakage. PASS requires zero Critical or Important findings.

## Original findings

### Important 1 — Added-contract supported-semantics validation: ADDRESSED

Added contracts no longer bypass compatibility validation. `_contract_compatibility()` invokes the applicable comparator against the new record itself and converts unsupported baseline semantics into an `unsupported` fitness result (`.grok-stack/adaptive_grok/architecture_fitness.py:418-454`). The bounded OpenAPI subset now accepts the frozen baseline's `application/json`, `application/octet-stream`, and `text/plain` media types while rejecting empty, excessive, unknown, malformed, or unsupported-schema content (`.grok-stack/adaptive_grok/architecture.py:1099-1138`). Directional request/response media comparison is also explicit.

The current OpenAPI baseline self-comparison is `compatible` (`tests/test_architecture_model.py:998-1040`), and the exact adoption-base-to-fix-head contract fitness is `pass` with no findings. The new adversarial bootstrap regression verifies that an added JSON Schema with unsupported `oneOf` semantics fails closed (`tests/test_architecture_fitness.py:1549-1588`).

### Important 2 — Ambiguous repository ownership and duplicate seed owner: ADDRESSED

System semantic validation rejects exact ownership ties (`.grok-stack/adaptive_grok/architecture.py:376-399`; regression at `tests/test_architecture_model.py:209-221`). Runtime ownership resolution selects the unique longest matching repository prefix and rejects equal-specificity ties instead of relying on node order (`.grok-stack/adaptive_grok/architecture_fitness.py:729-745`; regressions at `tests/test_architecture_fitness.py:666-704`).

The seed now assigns `trust-ci/compose.yaml` only to `NODE-TRUST-CI-WORKER`; `NODE-DOCKER-ENGINE` owns no repository path (`architecture/system.yaml:496-528,548-562`). The seed regression asserts the single owner (`tests/test_architecture_model.py:936-945`). An exact-head probe found no duplicate repository path and resolved a nested path to the most-specific owner.

## New fix-wave breakage

### Important N1 — The published frozen M2-B source contract contains stale architecture digests

Changing canonical repository ownership in `architecture/system.yaml` correctly changed the system and composite architecture digests. At the exact fix head, `grok_architecture summary --json` reports:

- Composite architecture digest: `ea8750fcec55d8880d142981764e6842e944424cf5c5b4bf89d13b3713f85c8a`
- System digest: `feb9f1596d664a5909dfb7e0d76ec379ca8ddb77e616b970aeef6ba32c5c869c`

The active package's authoritative **Frozen source contract** still publishes the prior-head values:

- Composite architecture digest: `ca97384dd1ceb33547ef6de0b38fc04a3dcbdb8648ce0a278f764bec11c562bc`
- System digest: `f8eeaf182b9f59fe33dd2c238e5147431569257f0a9ccdf7430bdee12b852847`

Those stale values are at `engineering/changes/20260826-m2-executable-architecture-015603/requirements.md:17-25`. The rules, schema, and contract-inventory digests remain unchanged and match. The typed spec gate passes because it checks criterion mapping, not that the frozen digest literals equal the canonical current model. Consequently AC-007's requirement to publish a frozen contract for separate M2-B consumption is presently false even though local validation is green (`change-spec.yaml:35-36`).

Required repair: update the frozen composite architecture and system digests to the exact final model values, and add a bounded check that the published frozen literals equal the canonical summary before AC-007 can close. Any resulting repository write requires fresh exact-head verification and rereview binding.

## Evidence

- `python3 scripts/grok_architecture.py validate --json`: PASS, no findings.
- `python3 scripts/grok_architecture.py summary --json`: current canonical digests shown above; contract inventory digest remains `039feea9a076516e3dd414c8e59bc2a2eeb522e2ca19a9087438b7ec7314e017`.
- Corrected focused seed test `ArchitectureModelTests.test_seed_architecture_models_current_boundaries_and_real_contracts`: PASS.
- Focused ownership and added-contract regressions: PASS. A prior missing-test-module error was a reviewer command typo and is not product evidence.
- `python3 scripts/grok_spec.py validate --change-id 20260826-m2-executable-architecture-015603 --gate --json`: PASS, `7/7` criteria mapped, no errors.
- `git diff --check 99de2f9757400f7394b7a9e2c46b3ebce939e438..fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d`: PASS.
- The scoped fix diff changes no path under `trust-ci/**`, no SQL/migration, and no contract/schema inventory file. It introduces no database, backfill, PostgreSQL source-of-truth, external-state mutation, or rollback/no-migration contradiction. The only data/contract blocker found in this fix diff is N1.

## Residual risk and disclaimer

The supported OpenAPI comparator remains intentionally bounded; future media types or schema constructs must continue to fail closed until explicitly implemented and tested. Repository ownership permits non-equal nested prefixes by design and assigns the most-specific owner; that rule is now deterministic and tie-safe.

This is repository-local independent review evidence only. It is not merge authority and does not replace the App-owned policy-epoch exact-SHA Trust CI check, deployed holdout enforcement, branch protection, or required human-signed approvals.
