# Rollback

Stop the dedicated host before reverting E to D. Existing full Factory composition remains available in D and v1/v2 SQLite readers stay compatible; preserve state/WAL/artifacts. Do not revert before compatible v2 readers or replay ambiguous provider work. No migration or operational rollback is executed by this slice.
