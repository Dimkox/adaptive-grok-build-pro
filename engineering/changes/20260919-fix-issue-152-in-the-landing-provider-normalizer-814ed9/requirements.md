# Requirements

The typed authority is change-spec.yaml. AC-001 distinguishes known failure reasons and preserves the validated original digest/usage; AC-002 prevents raw detail leakage and leaves unvalidated-result handling alone; AC-003 verifies durable authenticated retrieval and unchanged old records. INV-001 keeps draft refusal terminal and ineligible for fallback. FORBID-001 excludes raw or invented evidence.

The reason must be a constant from the reviewed vocabulary, not a sanitized arbitrary message or regex-shaped unknown code. The upstream response digest covers the actual response envelope/SSE bytes; do not replace it with a fresh hash of normalized stdout.
