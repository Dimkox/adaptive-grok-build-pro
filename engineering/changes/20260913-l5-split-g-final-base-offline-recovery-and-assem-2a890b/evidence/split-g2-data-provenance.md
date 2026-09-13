# G2 data analysis provenance

The bounded analysis in `/tmp/agbp-sweep/split-g-data-analysis.md` is reusable for the fresh G2 delivery route. This is a provenance confirmation by the selected read-only `data_architect`, not a replacement implementation review or verification receipt.

- Worktree: `/home/pall/grok-projects/adaptive-grok-build-pro-l5-split-g2`.
- Fresh active route: `3529132ae173`.
- Fresh change: `20260913-l5-split-g-current-base-offline-recovery-and-com-352913`.
- Genuine predecessor and inspected HEAD: `5a2ead6e6e1eff5c5df28a8d4bcb91a209975187`.
- Active route base fingerprint: `939cd5d8b4cf7af62b8a275faef0e791a8645cea3e7e4a1e065aa2a06a2698f5`.
- Frozen G extraction reference: `f31406e970d67f7cd59694da5de88915adb0fa68`.

I read the fresh active route, checked its base against actual `git rev-parse HEAD`, and compared all five hashes recorded in the original report. The two predecessor files were hashed directly from the G2 working tree; the three G extraction inputs were read as immutable Git blobs from the frozen reference. All five match exactly:

| Source | Path | SHA256 |
| --- | --- | --- |
| G2 predecessor | `factory/src/adaptive_factory/landing_sqlite_store.py` | `7b9e677d1d1b04a87b62a2c985be026c71420c64eb559bab9d5fb6bb3f44806a` |
| G2 predecessor | `delivery/src/adaptive_delivery/landing_publication.py` | `1ff0576faa5953596a2447e855742afd4926c91b09189b524e0627b2e09cd9c9` |
| Frozen reference | `factory/src/adaptive_factory/landing_backup.py` | `2c58731a22fc2224e0d30d087d002b81161c7d4459d5cfb973a5a07d41aad119` |
| Frozen reference | `factory/tests/test_landing_backup.py` | `4237b4f05ed6b063a040da001ffb350792d02c9aa2d3f90530d0601532f09be7` |
| Frozen reference | `factory/tests/test_landing_live_executors.py` | `2cc7b45945f05a2cc15bf87c8a0462e32e86ba4c51785252a3a9bd7be085a71c` |

The prior report's old route `0e93bc421bdb` and base `517741da6e883c5feacbd2f029d745ffc5e2fec0` remain historical inspection provenance; they must not be represented as G2's route or predecessor. At this check `git status --short` showed only the new untracked change-package directory, with no product edits.

The accepted implementation scope is unchanged: reproduce the reduced-cap restore regression, then reject `snapshot_budget` before creating restore roots when the remaining I/O budget cannot cover the known second pass. Preserve the existing 4-GiB I/O cap and 180-second deadline; do not raise or reset either. Document the actual restore payload limit and partial-failure behavior. The original report's lock/WAL/publication roundtrip test recommendations and deferred Qwen tail dependency analysis apply to these identical source inputs.

No broad research, source/test edit, SQL operation, operator-state backup, credential access or external action was performed. Only this provenance report was written. Any later source repair must be owned by the selected `data_implementer`, disclosed as a bounded deviation from the frozen reference, and receive G2's prescribed verification and independent reviews.
