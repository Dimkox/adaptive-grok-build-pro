# Design

Existing hook directories own canonical sources and template. Installed root shims are consumer outputs. Diagram topology stays unchanged.

Historical spec migrations need explicit retained evidence bound to the actual comparison base. Active/version2 specs stay strictly validated. Deployed Trust CI inputs stay unchanged.

## Bounded verification evidence

The completed check set at HEAD `52e1163da49d80b1ee40210c48e565f2fa3f13e7` could not publish its receipt: the unchanged 262,144-byte envelope limit was exceeded. The 1,442 checked paths and 488 rejected paths already exceed that limit through repeated mandatory metadata, even without logs; removing log text is insufficient.

Keep small verification receipts inline. For large reports, atomically publish the exact complete report in ignored runtime with a finite 8 MiB bound, then publish a compact closed reference carrying its path, exact byte count and SHA256. Descriptor-relative no-follow publication and reading must reject missing, tampered, malformed, oversized, symlinked or concurrently changed evidence. Bind the report to the receipt's immutable route, kind, Git/tree, spec, architecture and governance identity; hydration preserves invalidation/stale flags. Any report or envelope publication failure invalidates prior qualifying evidence. No mandatory inventory, scope, skipped check or detailed result is silently omitted; no hash qualifies without the actual file.

This is local workflow evidence only. The App-owned exact-head check and separately required external approvals remain unchanged. Trust CI's historical documentation-test compatibility is delivered separately through PR #240; no Trust CI code enters this product PR.
