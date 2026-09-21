# Exact-byte review-fix evidence

`red.log.json` and `change.patch.json` preserve the original bytes as base64 because
those bytes contain whitespace rejected by Git's diff check. Decode their `data` field
and verify `decoded_sha256` to recover the original files; the source paths named in
`report.md` and `results.json` refer to the unchanged external originals. The index binds
the stored envelope bytes separately from the decoded evidence bytes. No log content
was trimmed or edited to make a check pass.
