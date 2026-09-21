# Recovery

Trigger on hidden tracked/source changes, unstable scratch-only evidence, or ignored candidates under Git uncertainty.

1. Stop relying on candidate fingerprints and preserve regression evidence.
2. Forward-fix the provenance/filter logic or prepare a reviewed narrow utility revert; retain inclusion when uncertain.
3. Rerun utility/receipt tests, full verification and independent reviews, then regenerate local receipts for the recovered exact tree.

Fingerprints may change once because previously filtered tracked files become included. Regenerate receipts; never translate historical hashes into current approval.

No deployed state or production migration is changed by this source repair. Recovery of external consumers or services is separately authorized.
