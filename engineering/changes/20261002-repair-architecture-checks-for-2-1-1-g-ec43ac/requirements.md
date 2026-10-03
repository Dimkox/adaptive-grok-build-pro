# Acceptance criteria

AC-001: G-shaped positively bound Trust CI metadata/source cochanges pass separation; actual mixed product/Trust CI code, unrelated contracts, runtime/secret/edge/policy changes and absent/ambiguous base still fail.
AC-002: Supported added components/new operations are compatible without changing any existing contract; removed or changed existing components/operations/authentication remain incompatible.
AC-003: Dangling/cyclic/unsupported/malformed/over-budget additions remain unsupported, and exact/versioned-break semantics remain intact.
AC-004: Final combined exact candidate needs full PR verification, independent selected review and external App-owned exact-head checks; this isolated H draft and historical tests confer no merge authority.
