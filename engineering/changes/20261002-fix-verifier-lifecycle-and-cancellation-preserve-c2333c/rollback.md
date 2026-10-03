# Rollback and recovery

Trigger: cancellation fails to reap owned children within its deadline, a finalization fault hides a completed verdict, a failed publication leaves pass evidence, or existing check selection regresses.

1. Revert the eventual scoped source PR through a new isolated branch and reviewed pull request. Do not restore historical dirty worktrees or reset shared main.
2. Invalidate local verification/review receipts and rerun the required full PR verifier and independent reviews against the replacement tree. Receipt files are regenerated workflow evidence; no product data or database migration is involved.
3. Recheck App-owned exact-head Trust CI and required approvals before merging the rollback. If deployed source was separately authorized, restore the prior exact accepted source through that separately authorized operation; this package performs no deployment.

Forward recovery for evidence I/O failure is to fix storage/permissions, verify the unchanged exact head/tree and rerun recording. Never turn a skipped, cancelled or unrecorded outcome into pass by reusing an old receipt. A source or HEAD change requires new evidence.
