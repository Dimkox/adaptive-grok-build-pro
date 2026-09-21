# fix(factory): explain repair-child binding rejections

Repair-child precondition failures previously returned SQL NULL and surfaced as an
`invalid_object` error. Add migration `021` to return twelve fixed rejection reasons,
classify them before parsing a binding, and preserve a separate malformed-payload
diagnosis. Existing databases keep their immutable migration prefix and upgrade by
replacing the function; the accept/reject conditions and role grants are preserved.

Use request/server clocks in the affected PostgreSQL fixtures so the evidence suite
can run beyond the authority freshness window without expiring its own valid inputs.
Refresh the bootstrap handoff to identify this branch and the already-merged PR #151.

Validation is being completed in [the continuation record](continuation.md): full
route verification, four consecutive PostgreSQL passes bound to the final product
contents, and independent code/test/security/data reviews. This draft is not a passing
verification claim.

Rollback uses the documented forward-fix procedure. No installed service or database
is changed by this source PR; deployment remains a separate operation.

Fixes #155. Fixes #164.
