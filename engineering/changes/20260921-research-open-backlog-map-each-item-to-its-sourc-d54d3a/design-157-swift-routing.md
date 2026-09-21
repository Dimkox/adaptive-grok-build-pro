# #157: bounded Swift repository detection

## Current behavior and boundary

`detect_repo()` in `.grok-stack/adaptive_grok/repo.py` recognizes PHP, Node, Python, Go and Rust, then chooses `kind='generic'` when no language was found. A temporary repository containing `App.swift` and `App.xcodeproj` reproduced `kind=generic`, empty languages/domains/signals. `.grok-stack/adaptive_grok/router.py:394–401` maps domains to quality profiles, but has no Swift profile or Swift gate. Issue #169 owns the separate question of whether verification checks Swift product files; this packet must not claim that finding fixed.

## Minimal implementation slice

1. Add bounded Apple/Swift signals to `detect_repo`: root `Package.swift`, root `.xcodeproj`/`.xcworkspace`, and Swift source beneath conventional source roots. Use deterministic traversal with a depth and entry cap, ignore generated/vendor/worktree directories and symlinked directories, and emit a specific signal for each detected marker. Keep a source-only Swift package detectable without Xcode metadata. Preserve existing `polyglot` behavior when another language is present.
2. Set `languages=['swift']` and `kind='swift'` for a Swift-only tree. Add `apple` domain only for Apple project markers; a Swift package need not imply Apple. Use the existing route's `repo` and `rationale` fields to expose these facts. Do not select a specialist agent absent from the allowed roles.
3. In this slice, retain `base` as the executable quality profile and explicitly document the gap in the route/doctor output. #169 is the successor that must choose and enforce a real Swift product check before any green gate is described as product coverage. An empty `swift.json` profile would imply a check exists and should be avoided.

## Acceptance and focused evidence

- Fixture with `.swift` plus `.xcodeproj` routes as Swift/Apple, and source-only `Package.swift` routes as Swift without an Apple domain.
- Nested Swift source within the bounded scan is found; generated or symlinked trees do not create false signals; large fixtures stop within the configured budget with a visible incomplete-scan signal rather than a silent generic result.
- Python-only, Bitrix, generic and Swift+Python fixtures retain the correct prior classifications or become `polyglot` predictably.
- Route output clearly exposes `base` quality only and the outstanding Swift product-check gap. No test asserts that Swift code was linted or compiled.

Likely edits: `.grok-stack/adaptive_grok/repo.py`, `.grok-stack/adaptive_grok/router.py` only if route reporting needs a field, `tests/test_repo_router.py`, and a short routing/quality document. The first implementation commit should carry a failing Swift fixture. Rollback is removal of the additive signals; current generic routing remains available.
