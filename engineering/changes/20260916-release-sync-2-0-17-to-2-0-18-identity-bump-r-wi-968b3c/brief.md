# Release sync 2.0.17 to 2.0.18 — identity bump R

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Why

`v2.0.17` was published 2026-09-16T01:17:14Z (`c86b1a19`). Since then four pull requests landed on `main` (#101 streamed oversized tracked binaries, #102 landing-convention docs, #105 the live-proven `qwen-omni-intl` profile with classified operator probe failures, #106 the omni package closure). The tree therefore cannot keep claiming that no release preparation remains, and `2.0.17` cannot keep being simultaneously the product version and the newest published version while new merged source sits above the tag.

## What this wave is

Stage **R** only: candidate identity bump with the post-publication landing archive, the pending artifact slot asserted byte-free, the published v2.0.17 candidate archived verbatim, a fresh read-only runtime observation re-pinned to `d146ca45…`, and every coupled test literal moved in lockstep.

## What this wave deliberately is not

- No artifact, tag, GitHub Release or publication (stage A and the successor come after this merge, each with its own delegated grant).
- No installation or provider activation: issue #86's enablement remainder stays open; the services keep running their recorded pre-#93 SHAs (verified live, MainPIDs unchanged).
- No contract edits: the frozen capability contract waits for the #104 decision.
