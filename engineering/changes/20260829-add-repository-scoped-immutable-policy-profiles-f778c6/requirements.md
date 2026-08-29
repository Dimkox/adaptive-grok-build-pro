# Requirements — Add repository-scoped immutable policy profiles to the Python trust-ci webhook API and worker, selecting commands and holdout by exact repository, binding jobs to the selected profile digest, rejecting unknown repositories, and preserving schema-version-1 behavior with automated tests

## Acceptance criteria

- [ ] A legacy schema-v1 policy loads unchanged and retains its exact digest and Check Run name.
- [ ] A profile catalog resolves each configured repository by exact, case-sensitive `owner/name` and rejects unknown/case-variant repositories with HTTP 403 before enqueue.
- [ ] Mixed legacy/profile forms, duplicate repositories, wildcard/default profiles, invalid holdout roots, and incompatible per-profile execution envelopes are rejected at startup.
- [ ] Repository A and B may use different repository commands and holdout bundles; changing A does not rotate B's effective profile digest.
- [ ] Common security/execution-envelope changes rotate every affected effective profile digest.
- [ ] Webhook enqueue persists the selected effective profile digest in the existing `policy_digest` job field and keeps duplicate delivery idempotent.
- [ ] The worker resolves `(job.repository, job.policy_digest)` and never substitutes the repository's current or another repository's profile.
- [ ] Missing, stale, or mismatched bindings fail closed before checkout or repository commands and cannot publish success.
- [ ] Check Run name, approval lookup, command environment, signed attestation, retry, and replay all use the job-bound profile digest.
- [ ] No database migration is added; existing jobs and schema-v1 approval/attestation payloads remain readable.

## Failure and edge cases

- A repository removed after enqueue cannot execute under a fallback profile.
- A profile changed for the same head creates a distinct idempotency identity and epoch Check Run.
- Closed pull-request events from unknown repositories cannot cancel jobs.
- Holdout digest mismatch and path traversal fail before repository checkout commands.
- API/worker catalog skew produces terminal non-success, not cross-profile execution or indefinite retry.

## Non-functional requirements

- Security: exact matching, no fallback, full effective-policy digest coverage, immutable server-mounted inputs, and App-owned exact-SHA publication remain mandatory.
- Reliability: retries and publication replay preserve the original binding; worker restart never re-resolves solely by current repository assignment.
- Performance: O(1) in-memory lookup; existing queue/store interfaces and indexes remain unchanged.
- Observability: authenticated diagnostics expose catalog generation and selected digest without command output, internal paths, or repository labels in high-cardinality metrics.
