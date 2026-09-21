# Issue 165 independent test review

Result: **FAIL — one reproduced blocking defect in checkpoint persistence.** This is an independent `test_reviewer` report for route `2dfd5804553e`, not a receipt or merge approval.

Reviewed worktree: `/home/pall/grok-projects/adaptive-grok-build-issue-165`; branch `fix/issue-165-interruption-status`; exact HEAD `21046dff16a1b927d5a781ae0ec61708ebed89bc`. Actual implementation diff was read against `839d3aa26bc90417424d814ee48d8b5cd3be367e`, together with surrounding lifecycle, serializer, parser, receipt and hook code, the adopted design, all six acceptance criteria, and all 25 focused tests. Product files were unchanged between the initial full run at `738ea719d91cf439d3332ce621418dc994e7365b` and this reviewed HEAD; the intervening changes contain evidence packaging and shared-memory documentation.

## Blocking finding T165-1: filesystem bytes cannot survive the new checkpoint lifecycle

**Priority P2; affects AC-003 and AC-005.** A legal POSIX dirty filename containing byte `0xff` is decoded losslessly by `package_status._dirty_paths()` at line 426 to a string containing a surrogate. `_checkpoint()` in `change.py:33` copies that path into the new durable state. Both `start_change()` and the first `implementing` transition then call the existing `util.dump_json()`, which uses `ensure_ascii=False` and a strict UTF-8 writer (`util.py:56–73`). The lifecycle operation raises `UnicodeEncodeError` before the new canonical checkpoint can be written.

The failure has two observable consequences:

- Starting a new package with that dirty filename raises an exception and leaves the rendered template `state.json`. A repeated start returns successfully from the existing-directory path. Static inspection of the template and that path confirms the surviving state has no route ID, checkpoint, or evidence accounting; the attempted initial observation has not been recovered.
- Creating the filename after a valid package has reached `approved` causes the first `implementing` transition to raise the same exception. Persisted state remains `approved` with only its initial checkpoint, so the intended WIP observation is missing.

Changing only the JSON serializer to ASCII escapes is insufficient. `inspect_package()` parses state with `spec._parse_canonical_json()`, whose `_bounded_walk()` explicitly rejects unpaired surrogates (`spec.py:437–449,485–498`). An independently written escaped JSON checkpoint was therefore diagnosed as `state_invalid`. The code reviewer independently identified this parser leg; the probe below confirmed it.

The current filename regression at `tests/test_package_status.py:398` covers spaces, newline, tab and valid Unicode through `collect_worktree()`. It never persists a raw-byte path through `start_change()` or `transition()` and therefore cannot detect this defect. Add failing lifecycle regressions for both creation and first implementation with a raw-byte filename, including a successful subsequent inspection/readback and retry. Define a bounded representation or explicit unavailable observation that the durable reader accepts; preserve the existing strict spec parser and authority boundaries.

## Independent bounded reproduction

The coordinator granted one isolated reproduction after issue 163 released the CPU lane. Command wrapper: `timeout 10s python3 -B -`. It used two disposable, locally initialized Git repositories containing only the change template and a baseline text file. Each route was built and saved **before** creating `raw-\xff.py` with `os.open()` on a byte pathname. The first fixture invoked `start_change()` and then repeated it. The second started a valid package, transitioned to `scoped` and `approved`, created the byte pathname, and attempted `implementing`; it then wrote the attempted checkpoint with `json.dumps(..., ensure_ascii=True)` and called `inspect_package()`.

The probe imported the reviewed source without writing bytecode, executed no broader tests, and wrote no product files or receipts. Both temporary repositories were automatically removed. Process exit was **0**, meaning the diagnostic probe completed and captured the exceptions, not that the product behavior passed. Shell elapsed was **0.30947631 seconds**; measured probe time was **0.294 seconds**. The CPU lane was immediately released.

Exact captured result:

```json
{
  "elapsed_seconds": 0.294,
  "temporary_fixtures_cleaned": true,
  "results": [
    {
      "case": "start_with_raw_byte_dirty_name",
      "exception": "UnicodeEncodeError",
      "message": "'utf-8' codec can't encode character '\\udcff' in position 285: surrogates not allowed",
      "canonical_state_exists": true,
      "partial_package_exists": true,
      "repeat_start": {
        "exception": null
      }
    },
    {
      "case": "transition_and_escaped_json_readback",
      "exception": "UnicodeEncodeError",
      "message": "'utf-8' codec can't encode character '\\udcff' in position 757: surrogates not allowed",
      "persisted_stage": "approved",
      "persisted_checkpoint_count": 1,
      "observed_paths": [
        "raw-\udcff.py"
      ],
      "escaped_json_readback_status": "incomplete",
      "escaped_json_readback_findings": [
        "state_invalid",
        "objective_unresolved",
        "objective_unresolved",
        "acceptance_criteria_missing",
        "legacy_evidence_accounting",
        "template_unexpanded"
      ]
    }
  ]
}
```

The probe's field name `canonical_state_exists` records only pathname existence: in the failed-start case the surviving bytes are the copied template, not the attempted canonical checkpoint. The other scaffold findings in the escaped-state case are expected fixture omissions; `state_invalid` is the independently confirmed parser failure.

## Acceptance coverage assessed

| Criterion | Meaningful coverage in the reviewed tests | Assessment |
| --- | --- | --- |
| AC-001: bounded package inspection | Draft-to-active/blocked transitions; missing, duplicate-key, malformed and oversized selected inputs; traversal, absolute path, ancestor/leaf symlinks and FIFO; permission denial; aggregate bound; concurrent file replacement; no unrelated evidence crawling. | Broad positive and negative controls. No reproduced defect in these exercised paths. |
| AC-002: additive, nonmutating status | Real subprocess CLI runs twice with runtime absent and with populated current receipts. Full fixture inventory compares contents, sizes, modes and mtimes, including the Git index and ignored runtime/bytecode paths. The subprocess environment removes the bytecode-suppression variable, so the test exercises the CLI's own protection. Unsafe selected input has a real CLI sentinel control. | Meaningful coverage of the stated no-write guarantee; access times are explicitly outside it. |
| AC-003: named Git baseline and unknown observations | A stacked Git fixture distinguishes initial checkpoint HEAD from the older unchanged route base; ordinary dirty names, rename/delete/untracked paths, one-commit-ahead, package-only noise, missing/invalid/unavailable base, detached/unborn/no Git, query failure, malformed NUL output, and path-count overflow are covered. | **Blocked by T165-1:** collection alone does not establish durable raw-byte path support. |
| AC-004: current obligations and placeholders | Quoted/fenced/indented/inline historical markers and unreferenced old reports are controls against false positives; a current standalone marker is rejected. Missing obligations, empty reasons and missing recorded references are rejected; `not_run` and a recorded failure leave canonical receipt gaps present. | Meaningful separation of accounting from passing evidence. |
| AC-005: durable checkpoints and retry | Actual initial HEAD, invalid-transition nonmutation, repeated-start inventory equality, first implementation and blocked/resumed deduplication; injected README write failure leaves canonical state pending, and explicit retry preserves history and checkpoint count. | **Blocked by T165-1:** the missing raw-byte persistence/readback regression permits a new lifecycle failure. |
| AC-006: soft Stop and review behavior | Real Stop subprocesses expose incomplete packages both with no receipt obligations and with current receipts, never blocking or marking the route complete. A real review CLI first records pass without requiring later receipts, then refuses a malformed package without replacing the receipt, and still records fail. Existing adjacent hook/receipt tests retain successful ordinary completion behavior. | Covered controls match the adopted local-evidence boundary. |

Additional coverage limits, not separate blocking findings: the focused suite does not directly exercise an available-but-nonancestor Git base, HEAD changing between the two reads, raw-byte branch names, every file/finding-count threshold, or an initial-start mirror failure. The query-failure fixture raises the existing bounded-runner error and does not independently benchmark every timeout/output cap. No remote operation, deployment, external approval or Trust CI eligibility is proven by these tests.

## Verification evidence and its limits

- Initial focused RED: preserved `implementation-red.log.json`, 20 tests in 9.787 seconds, 32 assertion failures including subtests, no errors. Five later negative-control methods were not present in this RED.
- Final focused GREEN from the writer: preserved `implementation-green-2.log.json`, 25 tests in 13.066 seconds, `OK`. I read the captured output and independently decoded its content hash: `d6e17b84025b31f64563f8d0ce91060a2cfbf1ef31ff7d0bbaa99ab978b0032d`, matching the envelope. I did not rerun that suite.
- Initial full command: `GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr --json`, 09:11:56–09:20:25 UTC at `738ea719d91cf439d3332ce621418dc994e7365b`, **overall FAIL / exit 1**. The preserved `initial-full-result.json` reports passing product, unit, coverage, lint, architecture, PostgreSQL and source-stability checks; `git-diff-check` failed on trailing whitespace in the original RED log. The subsequent lossless log packaging changed no product file. These passing component results are not an overall PASS.
- Final frozen-tree full verification and receipts remain the coordinator's work. No passing review receipt was recorded by this reviewer; the reproduced defect must return to the sole implementation owner before renewed review.

## Actual reviewed file hashes

SHA-256 values were recomputed from the reviewed worktree. The combined `git diff` against the stated base for these implementation/test/contract files plus `.grok-stack/templates/change/evidence/README.md` was `644747dca9950edf46fbf8c5a7811798837757034af35f2cfc01f345f3e40382`.

```text
2345a4e03cc27be9d9b2aaab324ec04eb781e47b37a2be93cd4b46f4d7989397  .grok-stack/adaptive_grok/package_status.py
99586b99387285408f48dbb68b52e20a768c8551e872d3bb4b84d6c62befb886  .grok-stack/adaptive_grok/change.py
7dd3a2acd933f7b4240f44248b773715d30931385e62a2d8c9ca6db89a3058c9  .grok-stack/adaptive_grok/state.py
7be3f2be3fb9ea1e581344388a40da84c3a092945e3fb1a51a024847ad0bf48b  .grok/hooks/stop_gate.py
7bd6e8fd4268dde34c88705a6ed7fcf12dbd9b4b3ff9200ef9191fda44ec4281  scripts/grok_status.py
11b2bd54c307867d775b80b227fda3298722d3cddaa5819b6287458d6f4c46b1  scripts/grok_review.py
6910de8f2ea9057f06f52dd2225f2489f2332c6ff8abe0acfd625d0973b92fe4  tests/test_package_status.py
85097a484d15a19f1201056a6935b8e03d57abd7b10a45cdd36381b569f955dd  docs/package-status.md
```

Only this assigned report was written. Shared-memory fact for the coordinator: test filesystem-name support through both durable serialization and the strict readback parser; successful NUL-safe collection is not proof that a checkpoint can be saved and resumed. Preserve the distinction between a surviving template file and a successfully persisted canonical observation.
