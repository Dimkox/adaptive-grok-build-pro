# Merge provenance V1

Promotion authority depends on three separate immutable facts:

1. A GitHub-HMAC-authenticated `pull_request.closed` delivery with `merged=true` records a normalized `MergedPullRequestFact`. Delivery GUID plus payload SHA-256 is idempotent; a conflicting digest is a security conflict. This fact is pending evidence, never authority by itself.
2. A leased worker independently corroborates repository, PR, protected base ref and exact `merge_commit_sha` through the GitHub App installation API. It never substitutes a mutable branch tip.
3. The exact merged object runs in the isolated protected-branch runner. A passed signed `ProtectedBranchAttestationV1` binds merge fact ID, repository/ref/SHA, full policy epoch, runner/holdout/image digests and the SHA-256 of the exact artifact bytes.

`POST /promotions` accepts only when its `source_attestation_id`, repository, merged commit, artifact digest and policy epoch join that passed evidence exactly in the acceptance transaction. Squash, merge-commit and rebase strategies are represented by GitHub's exact merged object without assuming equality to the PR head. Webhook recovery uses the bounded durable reconciliation watermark `(updated_at, pr_number)` and fails closed when a capped batch cannot prove completeness.

Producers tolerate duplicate delivery and worker retry. Durable lease claim IDs prevent stale completion. Retryable failures persist `next_attempt_at` with bounded 5–300 second exponential backoff, so a process restart cannot erase eligibility and the worker keeps normal polling cadence. Exact provenance mismatches become permanent dead letters; retry-exhausted transient facts may be reset only by the constrained reconciliation requeue transition, which preserves immutable fact identity and attempt history in logs/metrics. No caller assertion, branch name, local receipt, raw webhook body, human signature alone or mutable artifact can substitute for this provenance chain.

Protected evidence insertion is idempotent by the unique `(repository, protected_ref, merged_commit_sha, policy_epoch, artifact_sha256)` tuple. If that tuple already exists, the store returns its original signed envelope only when merge fact, runner/holdout/image digests, result and signer key also match; otherwise it rejects the replay. The App success Check Run is published only after this durable get-or-insert transition, and merge-fact completion may then be retried after a crash without creating a second evidence identity.
