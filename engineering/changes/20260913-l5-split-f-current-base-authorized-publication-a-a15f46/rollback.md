# Rollback and recovery

Stop any separately activated operator before reverting F source. Preserve publication SQLite/WAL, immutable stage files and observed active-pointer state. Reverting source does not restore an external site pointer. Use observation-based reconciliation for ambiguous outcomes; predecessor activation/restoration requires its own exact grant. No live recovery or schema downgrade is performed in this slice.
