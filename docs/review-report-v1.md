# Structured local review report v1

`grok_review.py` accepts a bounded UTF-8 JSON report inside the repository. It validates shape, source spans and revision linkage before recording a local receipt. This format is workflow evidence: its command records and revision links are author-supplied data, not authenticated execution events or an append-only history service.

## Root object

The object has exactly these fields:

```json
{
  "schema_version": 1,
  "review_kind": "code_review",
  "status": "pass",
  "revision": {
    "revision_id": "rev-001",
    "previous_report": null,
    "previous_digest": null,
    "changed_claim_ids": [],
    "fresh_evidence_claim_ids": [],
    "changed_report_fields": []
  },
  "claims": []
}
```

`review_kind` is one of the review receipt kinds (`code_review`, `test_review`, `bitrix_review`, `security_review`, `data_review`, or `release_review`). `status` is `pass` or `fail` and must match the CLI request. Reports are limited to 512 KiB and 200 unique claims. A report path must be normalized, repository-relative, and resolve through regular non-symlink files beneath the repository root.

## Claims

Each claim has a stable unique `id` (1–64 characters, uppercase letter followed by uppercase letters, digits, `_` or `-`), a bounded non-empty `statement`, and a `type`.

- `source_citation` has `citations`, a non-empty array of at most 20 records. Each record is exactly `{ "path", "start_line", "end_line", "span_sha256" }`. Paths are current-tree repository-relative files. Lines are one-based inclusive spans of at most 501 lines; the digest is SHA-256 of the exact UTF-8 bytes of those lines, including line endings. The validator checks existence, regular-file status, bounds and digest. It does not judge semantic support.
- `execution` has a `command` record with `argv` (1–64 bounded argument strings), repository-relative `cwd`, integer `exit_code` (booleans are rejected), bounded `stdout_excerpt` and `stderr_excerpt`, and `provenance` exactly `self_reported_unverified`. It may also contain the closed probe `{"schema_id":"adaptive_grok.architecture.unsupported_schema","schema_version":1,"input":{"schema":{...}}}`. The probe input must contain a JSON object under `schema`, matching the dict input required by `architecture._unsupported_schema`; JSON strings and unknown probe schemas are rejected. Malformed records are rejected. Valid records remain self-reported; the validator does not execute commands or prove output truth.
- `inference` has `basis_claim_ids`, a bounded array of other claim IDs in the same report. It remains an authored inference.

Unknown fields and unknown claim types fail closed. The report contains no authenticated reviewer identity, clean-clone assertion, merge authority, or Trust CI result.

## Revisions and receipts

The first revision uses null predecessor fields and empty change arrays. A later revision names a confined `previous_report` and its exact `previous_digest`, uses a distinct `revision_id`, and declares `changed_claim_ids` and `fresh_evidence_claim_ids` exactly equal (in sorted ID order) to the validator-derived set of added or modified claims. Claim content is compared by stable ID across every field; editing a statement, type, or evidence without listing that ID is rejected. Evidence payloads for changed claims must differ from the predecessor. Silent removal is rejected: retain the ID and replace it with an explicit same-ID `inference` claim that explains the retirement and cites replacement/basis claim IDs. `changed_report_fields` must exactly list `status` when the pass/fail value changes; status transitions also require at least one fresh changed claim. The predecessor file must exist and match its digest. These checks detect omitted deltas and repeated evidence payloads; they do not provide a cryptographic append-only log or establish that the declared evidence is true.

A passing receipt stores the normalized report path, SHA-256 of the exact report bytes, and a bounded validation summary. `validate_evidence` repeats report validation and digest comparison. Deleting or changing the report invalidates the local receipt. Receipt freshness remains tied to the repository tree fingerprint; no local receipt replaces the external Trust CI check.
