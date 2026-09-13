# Independent code review — split D, repaired source

Verdict: PASS for the bounded D HTTP/media/durable-runtime slice. Both blocking findings from the first immutable source are resolved by the inspected implementation and independent regression rerun. No remaining blocking finding was identified in this review.

## Exact identity and scope

- Route: `bec1fcdde794`; change: `20260913-l5-split-d-bounded-http-models-and-durable-runti-bec1fc`.
- Immutable source HEAD: `bb93885034e52b80653efd96602fec182f7db10a`.
- Genuine route predecessor: `a75b3cd639a1483533069e8634759cdfc6612310`. The stacked PR predecessor is C `9ce156e0128b4f18b3fccfeca9a8edc7175da090`; the original route predecessor remains unchanged.
- Independently recomputed clean-tree fingerprint: `1a7e327a57a74acdb38f883a7496e52eb97732c42c42026a22f2a102e7018999`.
- Independent reviewer: `code_reviewer`; application/test write owner: `data_implementer`.

Read the active route, reviewer role, requirements, architecture and test plan. Inspected the actual full D product diff and surrounding implementation, then the exact delta from the previously reviewed `d1fdb7aec61b242c1a2fc5fc0ced1809e1b79c76`: shared settings validation, existing-server cleanup and its new direct regression tests. The prior FAIL and original reproductions remain preserved in `code-review-before-entrypoint-repair.md`; this new report supersedes that verdict only for the new identity above.

## Resolution of previous findings

**D-CR-1 resolved.** Shared `FactorySettings.validate_landing()` now rejects `path.anchor == "//"` for every landing root before directory checks, source validation, SQLite initialization or quarantine construction. The direct default-off same-inode alias regression verifies rejection and no state-directory writes. The profile/root matrix covers all five roots and all six provider selections, with I/O seams patched to fail if validation happens too late. Existing absolute-path, parent-traversal and lexical disjointness checks remain intact.

**D-CR-2 resolved.** Existing `server.main()` now gives listener close, owned runtime close and socket cleanup independent nested `finally` stages. A failure in either earlier close stage cannot skip the next one. The new direct-entrypoint regression uses an actual owned SQLite store, injects listener or runtime close failure, verifies the propagated injected exception and cleanup order, then successfully reopens the writer. It exercises the D entry point itself and does not depend on E's dedicated host.

An independent bounded rerun of the three new regression methods passed: 3 tests in 0.231 seconds, including the root/provider subcases and both close-failure stages. No broad suite was rerun during review.

## Correctness and security analysis of the bounded slice

The actual D inventory contains 19 landing modules: 16 offline core/helper/worker modules, the SQLite store, one server-composition module and the network-bearing live-executors module. The boundary inventory, source ownership and rule changes describe those actual files; the HTTP profile/DTO module has no network import. No future host, publication or backup source is needed to satisfy D.

HTTP profiles bind provider, region endpoint, model, media set, streaming mode and integer limits into their digest. The Qwen regional selection is checked before credential acquisition in the environment composition path. Explicit private credential-file parsing accepts one bounded assignment as data and evaluates no shell syntax; it does not fall back to environment credentials after a supplied file fails. Default-off server composition acquires no model credential. Live server composition validates source/path configuration, acquires the process-lifetime SQLite writer, and only then initializes quarantine and selects the named credential/provider.

The executor confines provider I/O to a pinned HTTPS endpoint, uses no ambient proxy settings, redirects or retry, and applies a whole exchange deadline plus request/response limits. HTTP results require the expected model, single final choice, usable text, consistent bounded usage and valid UTF-8. SSE handling bounds bytes, line/event accumulation and final ordering; reasoning is not joined into retained output. The normalizer reconstructs source-owned fields through the closed draft/spec contract and turns unusable provider outcomes into terminal human-review states. End-to-end mocked Qwen/Grok tests use the real executor/decoder/composition; the mixed native-V1/HTTP-V2 test seals actual artifacts, persists them to real SQLite, rejects crossed envelopes and validates reopen without changing legacy bytes. Later publication/backup integration remains outside this unit.

Media preparation enforces admitted types/sizes; duplicate case-folded DOCX members reject. PDF extraction uses the pinned packaged worker in a separate process with resource/input/output/time limits and an environment excluding model credentials. ExitStack cleanup runs child kill/wait and pipe closure even after selector construction/registration/close failures; the regression uses real child processes. These are application/process bounds, not a claim of a kernel network sandbox for the parser.

SQLite adds a nonblocking process-lifetime advisory writer lock with descriptor type/owner/mode/link/inode checks. The disclosed constructor repairs handle connect/configure interruption, failed connection close and post-flock interruption without leaking the writer. Existing close is idempotent and releases the descriptor despite checkpoint/connection-close failures. Schema, migrations and retained V1/V2 readers remain unchanged in D. API composition owns shutdown resources and prevents competing writers from triggering quarantine startup purges or acquiring credentials.

## Completed verification examined

`split-d-full-final.json` reports PASS for this exact route, HEAD and fingerprint. Every reported mandatory check passes: architecture/drift/diagrams, governance, contracts/static/security checks, 653 core tests, coverage, factory-unit checks, PostgreSQL suite (619 run, one skipped) with two actual restarts and exact-role recovery/reconciliation, and source stability. These are the fresh repaired-source results; prior passing verifier evidence did not establish that the two now-fixed defects were absent.

## Limits

PASS is bounded independent local code-review evidence. It does not create external exact-SHA App Trust CI approval, human-signed approval or merge authority. Other route-required independent reviews remain their reviewers' responsibility. No E/F/G operational behavior, real provider response or deployment readiness is claimed. This reviewer used no real credential, external request/write, operational grant, source edit or self-issued receipt.

## SHA-256 inventory of the product/test delta at the reviewed HEAD

- `architecture/rules.yaml`: `30d11d294c1a4336633f9d1c80ddaa859b43e271d8dff65743f99ba6df0d4d45`
- `architecture/system.yaml`: `a9eb0db56d01021d2b5052d448f9d5b5f65e8dc67709f4153f8cfe0e38c3b21b`
- `factory/pyproject.toml`: `7821d3485cbd1fd6f9a7d1842a07ac692fa2386f60c88ac57f30019bff566b55`
- `factory/src/adaptive_factory/landing_host_config.py`: `ab1cc6e1f29b2f9a710b63f3ee84082ba39d6e1b0cfd15f29fff6f3564dfe00d`
- `factory/src/adaptive_factory/landing_http.py`: `ad1ec53d953df1e383f17acb0d7effeac7152cd3da5cb9bdeb2b5f4527abe55f`
- `factory/src/adaptive_factory/landing_intake.py`: `b7e19e75a0014be85b098bb8c9b4bdd0b5b87def83ffd5e3e47a43db13f0cc19`
- `factory/src/adaptive_factory/landing_live_executors.py`: `bc5d65baac30e8b0447c965df89af2a73f29627025955ef60e01552ed527a620`
- `factory/src/adaptive_factory/landing_media.py`: `fde1e88a2b22edc58b598b8ec4a5ddda14414cd78e93dfe9e01303fb44cf8efa`
- `factory/src/adaptive_factory/landing_normalizer.py`: `9efc109b97d8769f5ea347752edbe6ccc632c63521275f95bb3a54893c6c2e96`
- `factory/src/adaptive_factory/landing_runtime.py`: `22a8f6996096d495157dd5b9a7b21cbceeb1691c6ed27310296326d64f3af533`
- `factory/src/adaptive_factory/landing_server.py`: `c29e34644d20d8fb8ce4edcb74070310da8aaddfab9795b3ebaa5cb9838f70b8`
- `factory/src/adaptive_factory/landing_sqlite_store.py`: `7b9e677d1d1b04a87b62a2c985be026c71420c64eb559bab9d5fb6bb3f44806a`
- `factory/src/adaptive_factory/landing_sse.py`: `e9b92b75601d67aaf478c1f7bf702578c223773156d3cc4b6883821f00c75861`
- `factory/src/adaptive_factory/resources/landing_pdf_worker.py`: `55d527a6fbaa3e54340cb0fba9764c4b3682610b38c6b4d7555304b9432454ae`
- `factory/src/adaptive_factory/server.py`: `825e594624e35b4459cf66d35873eaf62c854391aba70ea31f94c7ec41dae358`
- `factory/src/adaptive_factory/settings.py`: `0241a3e27200444bc3114da6e9c2940c6551d6db9e2112e74d6ab4c056c6dd02`
- `factory/tests/test_landing_live_executors.py`: `3e8ac9c037309b14c154359098d9de5fd6ffb1220f67d3e7e7ff8e972d1afa67`
- `factory/tests/test_landing_media.py`: `39cfc6a4d491e00eba2d4db7c101cd1d2d4747c5b07d4b7276641c256a5ab7d3`
- `factory/tests/test_landing_normalizer.py`: `f267dd1ee0856b375b1c2b805d998a4eea4c5f0c048af256863cd0edbe86462f`
- `factory/tests/test_landing_server.py`: `1a70c29bc8a5436017cb1b25d5b7ec2d780f90a15210af3249e5e1885dfcd671`
- `factory/tests/test_landing_sse.py`: `9218d4cbde9c7ce11e9e27ed38ade06ad1c61aa9616844e4ac5bf5b5e36d3e67`
- `factory/tests/test_server.py`: `de267f7d063326310bf60004cf4bf5e205bb57d4032937a37fd8a58e5f969d68`
- `factory/uv.lock`: `27e8a6001da8598cb0765412e07b4ae9112b69b621b23a8d4f8c0ae0a10b0c28`
- `tests/test_landing_architecture_boundaries.py`: `5df7246f54b7d8ad48e215e93297daabe6a036973f00df03cf94615316ba26b3`
