# #157 / #169 — detected product scope must receive meaningful verification

Research route `d54d3afd1c92`; execution packet only. This designs an honest consumer result and does not invent a Swift toolchain, grant deployment authority or weaken Trust CI.

## Required outcome and compatibility decision

A Swift/Apple consumer must be recognized, and a verification pass must not imply its changed product was checked when only installed stack files or empty scopes were inspected. Optional irrelevant checks may remain skipped; “any skip means failure” is not a requirement and would break valid repositories without SQL/contracts.

Recommended first implementation preserves report/receipt `pass|fail` compatibility. Add a required applicability/coverage-completeness check that fails with machine-readable `incomplete_product_coverage` and names the uncovered paths/languages or unavailable required tool. Checks with no applicable scope become explicit not-applicable skips. An overall new `incomplete` enum is optional future API/schema work, not necessary: `receipts.py` currently accepts only pass/fail, and CLI consumers use that status for exit code.

## Bounded sequence and acceptance

1. Complete #157 detection in `repo.py` and route tests: bounded safe discovery of root/nested `Package.swift`, `.xcodeproj` and Swift sources; deduplicate polyglot signals; ignore managed stack/vendor/cache noise without excluding real consumer sources. Project bundle names should signal Apple context, while actual Swift files/Package.swift establish Swift. An Objective-C-only Xcode project must not falsely become proven Swift coverage. Reflect chosen domains/profile in router configuration; do not invent unavailable specialized agents.
2. Introduce an explicit product change inventory shared with verifier applicability: distinguish installed managed stack paths from consumer product paths, preserve tracked configuration, account for exclusions, renamed/untracked files and unknown inventory. Missing source coverage produces an actionable non-green result, not “language-less generic” success.
3. Instrument Python tools with actual selected/scanned file counts using supported machine output or bounded file-discovery interfaces. A configured tool that selects zero files while relevant changed Python files exist cannot pass. Do not claim LOC counts from file counts; preserve genuine analyzer failures and sanitize bounded output.
4. For Swift, choose an available configured product check. On Linux without an Apple toolchain report precisely that native verification is unavailable; do not auto-install Xcode/Swift, execute package build scripts just for detection, or substitute Python lint for Swift validation. If a native command is configured, prove it inspected the applicable project/source and failed on a deliberately invalid fixture in a suitable environment.
5. Align consumer installer defaults/disclosures with #161, preserving user-owned lint/coverage settings and the #110 refresh boundary. The factory's exclusions must not be copied as authoritative consumer product scope. Add installed-consumer fixtures: Python product under engineering excluded by old config; pure Swift; mixed Swift/Python; no SQL/contracts; missing tool; all checks meaningful; unsupported source language.
6. Expose checked/uncovered/applicable scope and reasons in CLI/JSON/receipt details. Coordinate with #51 full discovery and #167 static profile; every selected profile must prove its own product checks. A passing stack-only self-test is labelled as such.

Files: `.grok-stack/adaptive_grok/{repo,router,verification}.py`, `.grok-stack/config/{routing.json,quality-profiles/}`, `scripts/install_into.py` and consumer template only in coordination with #161/#110; `tests/test_repo_router.py`, `tests/test_verification_doctor.py`, `tests/test_installer.py`, report/receipt compatibility fixtures. Do not make all existing optional checks mandatory as a shortcut.

## Gates, risks and recovery

No new user approval is needed for local source implementation beyond any named route gate. Real native project execution requires an appropriate platform/toolchain and user-authorized environment; production CI policy/image installation is a separate exact external operation. Source PR cannot claim those unavailable platform results. Normal full verifier/selected reviews/external merge checks remain required.

Risks: counting proposed input paths instead of actual analyzer scope; treating managed stack tests as consumer product coverage; false language detection; excluded tracked files; changing report enums without consumers. Recovery uses additive metadata and versioned config defaults, retains existing consumer settings, and discloses unsupported coverage. Reverting source removes the new gate but must not be presented as proof the consumer was checked.

Optional alternatives: a new `incomplete` status across every schema/CLI/receipt consumer, language-specific generated lint configs, or a configurable plugin checker registry. None is required for truthful first-pass scope coverage; generic skip-to-pass and blanket any-skip failure are both rejected.
