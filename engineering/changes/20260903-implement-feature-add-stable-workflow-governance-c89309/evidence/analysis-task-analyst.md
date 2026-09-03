# Task analysis (read-only)

The closed v1 record contains exactly `superpowers`, `bmad_method`, and `spec_kit` with official repository, stable tag, tag-object and peeled commit SHA, attribution URLs, and bounded policy. Only non-draft/non-prerelease releases are stable authority; branches are observations only. Due time is exactly PT168H/604800 seconds in UTC, with no I/O before due; every completed attempt advances due and clock rollback waits.

Transport is fixed GET-only GitHub, bounded and credential-free. Canonical state is atomic under one lock; contention performs no I/O. Failures are `unknown` before any success and `stale` afterward, candidates are `review_required`, full equality is `converged`, and partial results are `degraded`. The synthesis combines bounded planning/TDD/review, traceable deterministic status, and read-only convergence without overriding route, one writer, Trust CI, or human gates. No edits were made.
