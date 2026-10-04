# Rollback

Trigger rollback if this source cleanup breaks canonical hook discovery, installed compatibility aliases or architecture ownership.

1. Create an isolated revert branch restoring the nine wrappers, nine architecture paths and their test/documentation expectations.
2. Run targeted compatibility/architecture controls, independent review and fresh full local verification on the final candidate.
3. Deliver the revert PR only with fresh App-owned exact-head Trust CI and applicable approvals.

No database recovery, service restart, deployed policy mutation, history rewrite, tag or release asset change is involved. Installed consumers retain the same alias/template bytes, so this change needs no destructive consumer cleanup. Restored HEAD-based root inventory and both-profile alias execution are the rollback acceptance controls.
