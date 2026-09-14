# Test plan

The initial 26-test result did not cover the three defects found by independent review. Preserve those reports as [code review](evidence/code-review-initial-fail.md) and [test review](evidence/test-review-initial-fail.md); they are failure evidence for the previous head, not approval for this repair.

Review-repair TDD adds direct decoder regressions for mixed-language/escaped ordering and digest stability, invalid section containers, 12/13 section and raw-item bounds, section ordering, and nearby strict item/text/field rejection. HTTP tests use real Grok/Qwen executors, response decoding, and normalizers with an in-process `httpx.MockTransport`. A real SQLite-backed service test checks the persisted controlled reason and evidence digest. The Codex test uses its existing offline executor fixture.

- Red before production edits: 18 tests, eight failing subtests and 13 error subtests, exit 1. The errors are the actual escaped `TypeError` and rejected valid multilingual drafts; see [red evidence](evidence/review-repair-red.md).
- Green after the decoder repair: the same 18 tests pass. The broader normalizer/contracts/provider/live-executor suite passes all 66 tests in the locked factory environment, and Ruff passes for all three edited Python files; see [focused evidence](evidence/review-repair-focused.md).
- The first broader run with system Python reached 65 passes and one existing test import error because `uvicorn` was absent. The locked-environment rerun resolves this environment prerequisite without source, dependency, or lock changes.
- Parent runs `UV_LOCKED=1 python3 scripts/grok_verify.py --mode pr` after all source/package edits finish, then obtains both route-selected reviews and records current fingerprint-bound local receipts.
- A new commit requires a fresh App-owned policy-epoch check on its exact PR head and any required external approvals. Focused tests are local preflight only.

No real provider request, live input, credential acquisition, or running service mutation is part of these tests. Live success remains unverified until the separate authorized rollout and bounded observation described in [release.md](release.md).

## Bounded PDF fixture recovery after the first full run

The parent archived the [initial full verification](evidence/initial-full-verification.md) and [operational recovery facts](evidence/operational-recovery.md). It ran `UV_LOCKED=1 python3 scripts/grok_verify.py --mode pr`: root tests passed (654 tests, 529.477s), pilot tests passed (44), and factory tests ran 711 tests in 356.762s with one failure and two skips. All other guards passed. The full result is **FAIL**, solely `factory-postgres-exit`: the existing oversized-page fixture expected `pdf_page_limit` for a corrupt PDF and received `pdf_invalid`.

The locked isolated PDF module reproduced the same failure without the newly added normalizer tests. Direct parser diagnostics showed the byte replacement left `startxref=371` but shifted the actual xref to 373; `PdfReader(strict=True)` raised `PdfReadError: Broken xref table`. A real 101-page PDF parsed correctly and the unchanged worker returned `pdf_page_limit`. Correct only the fixture, preserve the corruption test, and add the valid 100-page boundary.

The corrected full PDF module plus the prior 66 focused tests pass in one locked run: 74 tests, one expected unavailable-parser skip, 8.295s; Ruff passes on all four edited Python files. See [PDF fixture recovery evidence](evidence/pdf-fixture-recovery.md). The parent will inspect fresh independent reviews and run the mandatory full verifier on the committed final tree; a passing full result and current receipts remain **pending**, and the initial failed result is not promoted to passing evidence.
