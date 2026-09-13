# Rollback

Stop the owning runtime before reverting D to C. Preserve SQLite/WAL and retained artifact state; no schema downgrade or envelope rewrite is needed. C keeps both readers but lacks the new cooperative lock, so maintain one-process operation. Earlier-than-C rollback requires a consistent pre-v2 snapshot or retained v2 reader. Never replay ambiguous model outcomes automatically. No operational rollback is executed in this source change.
