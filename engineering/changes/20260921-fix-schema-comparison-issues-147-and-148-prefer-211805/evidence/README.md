# Candidate evidence

Initial full verification passed at6867f6dc. Independent reviews found a registered-ID fallback regression; [the repair](review-repair.md) passed four focused methods after four failing subtests. Renewed [code](code-review.md) and [test](test-review.md) reviews pass atd19b1b68; first findings remain preserved.

[Candidate history](candidate-verification-history.json) binds current product hashes and renewed reports. The final candidate must run the mandatory full PR verifier and receive current review receipts before publication. Final raw output lives under `/home/pall/.cache/agbp-run/issues-wave-20260921/schema/` and its result must be included in the PR. No old full result is reused for corrected bytes. Preserve pending PR137 semantics during later integration.
