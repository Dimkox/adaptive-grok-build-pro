# Independent installer test review

Verdict: **REQUEST CHANGES — one test-adequacy blocker**. Reviewer: selected `test_reviewer`; route `148c66d20768`. Reviewed head `03fbaa91895bffe616d6a61884a7564e6057839a` against `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`, including all four product files and surrounding installer/test code. The implementer did not approve this review. No product files were modified by the reviewer.

## Finding

**P2 — Keep the source-relocation fixture valid after requiring consumer templates.** `tests/test_installer.py:731-776` still creates `source/AGENTS.md`, restricts `MANAGED_DIRS` to `.grok`, and supplies an empty `MANAGED_FILES`. The new `build_payload` at `scripts/install_into.py:592-603` requires `.grok-stack/templates/consumer-AGENTS.md` in the inventory. Consequently this source fixture is invalid even without relocation. If the intended source-binding refusal regresses, the broad `assertRaises(UnsafeInstallTarget)` can still succeed because the template is missing; `swapped` and absent-target checks do not distinguish that unrelated refusal.

Return this to the sole write owner. Supply and inventory the consumer template in the relocation fixture, then establish an unrelocated positive control and/or assert the specific binding failure so both source-root and managed-directory relocation cases remain meaningful. This finding follows directly from the fixture and the new required lookup; no mutation experiment was executed during the coordinator's CPU-exclusive verification window.

## Coverage reviewed

- `test_materialized_consumer_documentation_is_portable` constructs generic and Bitrix payloads, uses the real absent-target writer, audits installed README/AGENTS relative links, verifies optional consumer bootstrap/state/version/shared-memory/architecture wording, rejects known factory deployment identity, and compares emitted AGENTS with the helper. The Bitrix case deliberately injects an explicitly built payload; it does not claim a new public profile argument.
- The link-audit control accepts an existing local destination with a fragment and an HTTPS link, and rejects both a missing file and an existing file outside the consumer root. Resolution and root containment protect the tested inline-link format; fragment existence and general Markdown parsing are outside this helper's scope.
- Determinism and manifest tests compare rendered document bytes and SHA-256 values in both profiles. The existing publication test independently checks actual installed content, sizes and modes against the returned plan. Generated documents are intentionally exempted from raw-source parity and covered by the new rendered-byte assertions.
- Existing-consumer checks preserve the complete AGENTS bytes, including CRLF, invalid UTF-8 user text, managed markers, prefix and suffix. They retain README ownership, reject a divergent `kept_local` README and existing-target materialization, and compare complete target snapshots before/after. Existing read-only tests additionally forbid mutating filesystem primitives and dependency execution.
- Source-read race coverage now includes both consumer templates and `managed_agents_text`, while retaining managed payload, Bitrix guidance and toolchain cases. The separate source-inventory relocation fixture has the blocker above.
- Manual template review confirms required local links point to installed entries or created directories, consumer-owned handoffs are conditional, and one-writer/review/PR/exact-consent/secret/external-authority safeguards remain. Root `AGENTS.md`, root factory README and Bitrix guidance have no diff against the review base. No updater, live activation or hook-registration success is claimed.

## Verification evidence inspected

No tests, lint, compiler or Docker were started by this reviewer. The retained logs in `/home/pall/.cache/agbp-run/issues-wave-20260921/installer/` were read and their hashes independently recomputed:

- `installer-red.log`: `fe988a18c67ba24758d5f75392425fb3b840e3a003681eebfa24b87b1da3989f`; 32 tests, 14.191 seconds, three failures and two errors. The output directly shows nine unresolved README links in each profile, the old README not conflicting as kept-local, and absent-template errors. The shell wrapper's numeric unittest exit was not retained; it is not represented as captured evidence.
- `installer-green.log`: `3160794321e1c585e0af5ce831746ba57a3515b1366e15f8a5832503ce4b202a`; 32 tests, 14.757 seconds, `OK`. The implementer records exit zero.
- `verify-initial.json`: `be158ecf55768707542f7de6006a70ea348c8d729e05911bd88fabecf42d34b6`; overall `pass`, profiles `base` and `contracts`, 15 passing checks and one unconfigured workflow-artifact skip. `verify-initial-meta.json` records `GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr --json`, exit zero, head `03fbaa91895bffe616d6a61884a7564e6057839a`, September 21 07:26:34–07:34:45 UTC. The recorded fingerprint is `ae7f447d3e6b95329865b1913631660aa69d88997d32c3c1297f2dafd149e63a`; its source-stability check passed.

Current product-file hashes match the implementation evidence exactly: installer `0e462616136d005dba1b31b198dfac92b9fc1b585e3f75055302edb1560d959f`; tests `b00a9e7851e840a3ea447c86ce81b79f01346c8e2c1230e13adc9903b9ae2dfa`; consumer AGENTS template `81b982d71d3418295b6e7b0b511bdc1c887b2d1abd6a83336990024565219309`; consumer README template `b2295eccd7393c4dcbaeb137b4702fae90331ebf20360128eea855899bddddd4`.

The existing verification receipt is stale after review-state paperwork; `grok_status` reports that explicitly. Fixing the fixture requires fresh focused/full verification and re-review before a passing `test_review` receipt. The coordinator owns final fingerprint binding. This report establishes neither external HTTP availability, live consumer operation nor exact-head external Trust CI/merge authority.
