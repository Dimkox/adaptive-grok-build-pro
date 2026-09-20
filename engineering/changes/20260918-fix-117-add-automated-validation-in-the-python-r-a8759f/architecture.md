# Architecture — #117 review evidence validation

## Current behavior

`grok_review.py` joins an arbitrary `--report` value to the repository root, checks `is_file()`, and writes a receipt using only its path and caller-supplied status. Absolute paths override the root and symlinks are followed. Receipts bind repository/spec/architecture/governance fingerprints but not report bytes; `validate_evidence` never opens the report.

## Proposed behavior

The CLI resolves a bounded regular report beneath the repository root without following an escaping symlink. It parses a versioned JSON document containing claim IDs and typed evidence. Source citations must resolve to regular repository files and valid line spans in the current tree. Execution records must contain command, cwd, exit status, output excerpt and provenance label; local self-authored records are labeled `self_reported_unverified`, never authenticated. The only supported probe is `adaptive_grok.architecture.unsupported_schema` v1 with an object input containing an object `schema`; this rejects the incident's JSON-string-to-dict mismatch without introducing an external schema fetch. Other probe IDs and shapes fail closed.

A report revision names a confined predecessor report and its digest. The validator derives the exact changed/added claim IDs by comparing all claim fields and derives changed report fields (currently `status`); declarations must match. Changed claims need evidence payloads that differ from the predecessor, removed IDs are rejected, and a status transition requires at least one fresh changed claim. A removed claim is represented by retaining its ID and replacing it with a same-ID inference retirement claim. Validation checks the declared link and digest but cannot establish append-only history or prevent an author from rewriting the chain. The receipt stores the digest of exact report bytes; evidence validation confirms the same confined report still exists and hashes identically. Receipts remain local workflow evidence and are not proof of authorship or truth.

## Components and boundaries

- `scripts/grok_review.py`: confined path handling and report parsing at receipt creation.
- `.grok-stack/adaptive_grok/receipts.py`: persist report digest and validate report binding.
- `tests/test_review_evidence.py`: path, schema, citation, command-record, revision, and tamper regression coverage.

## Trust boundary

A local report can assert that a command ran. Parsing its command/output fields, hashing the report, and binding it to the repository tree cannot prove that execution occurred or that output is truthful. No local result is presented as reviewer identity, clean-clone proof, semantic support, Trust CI attestation, or merge authority.

## Rollback

Forward-fix malformed schema/compatibility defects. No external state or production data changes. Legacy prose review reports must be rewritten in the structured format before recording a passing receipt.
