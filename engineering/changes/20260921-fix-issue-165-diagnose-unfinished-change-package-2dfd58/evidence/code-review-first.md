# Independent code review — issue 165

Status: **FAIL — one P2 correctness finding requires repair.**

Route `2dfd5804553e`; role `code_reviewer`; worktree `/home/pall/grok-projects/adaptive-grok-build-issue-165`; branch `fix/issue-165-interruption-status`. Reviewed HEAD `21046dff16a1b927d5a781ae0ec61708ebed89bc` against ancestor `839d3aa26bc90417424d814ee48d8b5cd3be367e`. Reviewed the actual product diff, surrounding lifecycle/spec/state/receipt/Git implementations, adopted architecture and integration analyses, all six acceptance criteria, focused tests, and recorded verification evidence. This report is independent local review evidence, not a receipt or merge authority.

## Finding CR-165-01 — P2: a legal non-UTF-8 filename breaks durable checkpoint creation

Location: `.grok-stack/adaptive_grok/change.py:124` and `:153-160`, through `_checkpoint()` at `:34-48`; path decoding is `.grok-stack/adaptive_grok/package_status.py:426`.

A dirty POSIX filename containing byte `0xff` is valid Git/worktree input. The new NUL-delimited collector correctly preserves that byte using `os.fsdecode`, producing a Python surrogate such as `raw-\udcff.py`. `_checkpoint()` copies the resulting strings directly into `dirty_product_paths`. Both `start_change()` and the first `implementing` transition then pass the checkpoint to `dump_json()`. In this exact candidate, `.grok-stack/adaptive_grok/util.py:72-73` uses `json.dumps(..., ensure_ascii=False)`, while `atomic_write_text()` at `:60-62` writes strict UTF-8. The new checkpoint therefore raises `UnicodeEncodeError` instead of being persisted.

For `start_change()`, `shutil.copytree()` and spec/Markdown/route rendering have already happened before the failing state write. The rendered template `state.json` remains instead of the intended canonical state: it has no route identity, initial checkpoint, or evidence accounting. A repeated `start` takes the existing-directory branch and returns that incomplete scaffold as though creation had succeeded. For a first implementation transition, the previous state survives the atomic-write failure, but the valid transition cannot complete while that dirty filename is present. Both paths undermine the intended interruption recovery and AC-003/AC-005.

Changing only JSON output to ASCII escapes does not complete the repair: `inspect_package()` parses canonical state through `_parse_canonical_json()` at `package_status.py:225`, and `spec.py:448-449` explicitly rejects surrogate code points in `_bounded_walk()`. An escaped raw-byte path would be persisted but then classified as `state_invalid` on readback. A future unrelated utility change must not be assumed to solve this candidate's lifecycle contract.

Requested repair: give persisted filesystem names a bounded representation that round-trips through the canonical state reader without weakening the specification parser or silently merging distinct path identities. If a filesystem name cannot be represented under the chosen checkpoint contract, preserve a durable explicitly unavailable observation instead of aborting or claiming a clean snapshot. Keep ordinary Unicode filenames and current receipt authority unchanged.

Required regression: create a raw-byte dirty filename in an isolated Git fixture, exercise both new-package creation and a first implementation transition, then inspect/read back the state and retry/resume. Check that canonical state remains valid, the initial HEAD/history are preserved, raw-byte and literal escape-looking names are not confused, and no partial scaffold blocks an ordinary retry. Include lifecycle CLI output if the representation can reach it. The current filename test (`tests/test_package_status.py:398-411`) covers spaces, newline, tab, and valid Unicode but not raw-byte names.

This finding is established by the source/encoding contract above. I did **not** execute a reproduction. The controller separately authorized the independent test reviewer to run a bounded probe; that reviewer reported a 0.294-second run confirming `UnicodeEncodeError` for both lifecycle paths, the stale-template retry behavior, preservation of the approved state after transition failure, and `state_invalid` after escaped-JSON readback. See the independently authored [test review](test-review.md) for the measured record. The reviewed source and this report's hashes remain unchanged.

## Inspected boundaries without additional blocking findings

- The selected package path is confined to `engineering/changes/<change-id>`. Descriptor-relative no-follow opens, regular-file checks, file identity checks, explicit reference filtering, and file/byte/finding limits protect the new inspector from selected-path escapes and unbounded directory discovery. There is no recursive evidence crawl.
- Stage comes from durable state. Draft unresolved scope is expected; active/blocked unresolved scope is an error. Only owned current template forms are matched; quoted, fenced, indented, and inline-code history is deliberately excluded. Typed `not_run` accounting remains separate from receipt validity.
- The status entrypoint disables bytecode before adaptive imports, state getter path construction no longer creates runtime directories, and Git reads disable optional locks. Existing receipt validation remains separate and may cost more than the new bounded observer; the documentation states that limit.
- Git observations retain a named initial-checkpoint or route baseline, do not fall back to current HEAD, and preserve unknown values after unavailable/truncated queries. The new NUL parser handles rename source/destination and ordinary unusual Unicode names. The persistence mismatch above is at the boundary after that parser.
- Canonical state is written before the README mirror; a mirror failure leaves an explicit pending flag, and the same transition can repair it without adding checkpoint/history rows. Reentry preserves the first implementation observation. No automatic commit, publication, or archive migration was introduced.
- Review preflight checks package errors before passing receipt creation and does not require its own or later review receipts. Failed reviews remain recordable for ordinary completeness failures; known unsafe inputs are refused before legacy binding readers reopen them. Stop remains warning-only. Existing receipt envelopes, delegated-grant logic, and external App-owned merge authority are unchanged.

These observations describe inspected source behavior, not independently executed test outcomes or a claim that every possible environment has been qualified.

## Verification evidence and limits

The recorded focused GREEN is **25 tests, 13.066 seconds, exit 0**; the earlier RED and first failed GREEN are retained. I inspected the test source and evidence records but ran no tests, Python imports, compilation, lint, Docker, or PostgreSQL work in this review lane.

The initial full verifier at `738ea719d91cf439d3332ce621418dc994e7365b` ran `09:11:56–09:20:25 UTC` and had overall **FAIL**, exit 1. Its record lists product/unit/coverage/lint/architecture/PostgreSQL/source-stability checks as passing, with `git-diff-check` as the sole failed check because the raw RED log contained trailing whitespace. The controller subsequently stored lossless JSON log envelopes and reported exact staged/both-base diff checks passing at the reviewed HEAD; the inspected product hashes agree with the writer's recorded product hashes. This review does **not** relabel that full run PASS. A frozen-candidate full run and current receipts remain pending, after the finding is repaired and independently reviewed.

Only this assigned report was written. No implementation changes, receipt recording, delegation, commit, or external operation were performed.

## Reviewed file identities

| File | SHA-256 |
| --- | --- |
| `.grok-stack/adaptive_grok/change.py` | `99586b99387285408f48dbb68b52e20a768c8551e872d3bb4b84d6c62befb886` |
| `.grok-stack/adaptive_grok/package_status.py` | `2345a4e03cc27be9d9b2aaab324ec04eb781e47b37a2be93cd4b46f4d7989397` |
| `.grok-stack/adaptive_grok/state.py` | `7dd3a2acd933f7b4240f44248b773715d30931385e62a2d8c9ca6db89a3058c9` |
| `.grok-stack/templates/change/evidence/README.md` | `461b381c637dc0c5cf1ce7f82a2f4d4f1cc39f142f9f19fb473b737391f340dd` |
| `.grok/hooks/stop_gate.py` | `7be3f2be3fb9ea1e581344388a40da84c3a092945e3fb1a51a024847ad0bf48b` |
| `scripts/grok_review.py` | `11b2bd54c307867d775b80b227fda3298722d3cddaa5819b6287458d6f4c46b1` |
| `scripts/grok_status.py` | `7bd6e8fd4268dde34c88705a6ed7fcf12dbd9b4b3ff9200ef9191fda44ec4281` |
| `tests/test_package_status.py` | `6910de8f2ea9057f06f52dd2225f2489f2332c6ff8abe0acfd625d0973b92fe4` |
| `docs/package-status.md` | `85097a484d15a19f1201056a6935b8e03d57abd7b10a45cdd36381b569f955dd` |
