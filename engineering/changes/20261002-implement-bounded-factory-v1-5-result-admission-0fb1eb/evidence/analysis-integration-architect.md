# Integration and threat analysis

Blocking source defects: missing store methods; absent repository identity comparison; caller-asserted allow/redacted payload without PR3a semantic revalidation; duplicate-key collapse; schema/OpenAPI drift; missing correlation parity; character rather than UTF-8 byte assumptions. Do not transplant source broker regressions.

The bounded contract seam must test auth/scope/owner/repository and every grant identity mismatch, strict outer JSON, structured secrets/nonfinite/surrogates, content/media/body bounds, safe 503 behavior and zero side effects. Durable idempotency/restart/concurrency and dormant outbox tests belong to the next persistence slice.
