# Test plan — #117

- Reject absolute paths, `..` traversal, symlink escape, missing files, non-regular files, and oversized report bytes.
- Accept a minimal valid versioned report and reject malformed JSON/schema, invalid claim IDs/types, unsupported probe IDs, the exact JSON-string-instead-of-object probe input, and malformed execution records.
- Validate existing source path/line spans; reject nonexistent paths, directory/symlink targets, and out-of-range spans.
- Check execution evidence is always marked self-reported/unverified and never treated as captured proof; require report status to match the receipt request.
- Accept a valid linked revision; reject missing/wrong prior digest, duplicate revision IDs, unlisted statement/evidence/type changes, added claims omitted from change/fresh-evidence arrays, removed claims, changed claims whose evidence payload is missing or unchanged, and status transitions omitting `changed_report_fields` or fresh changed claims.
- Record a passing review, then mutate/delete the report and confirm `validate_evidence` reports stale/missing evidence.
- Run focused tests and the route-selected full PR verification; run both independent route reviews only after the final tree passes verification.
