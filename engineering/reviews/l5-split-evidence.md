# L5 split evidence checkout

This branch stores durable verification and independent review reports for immutable source checkouts A–G in the same repository. Each report names the exact source HEAD, genuine base and tree fingerprint. Receipt commands run from the corresponding unchanged source checkout and reference absolute report paths here. This evidence checkout's HEAD is not a product-test identity or merge authority.

No report copy, state transition or documentation commit is made in a source checkout after its final verification commit. Its frozen state.json records the verification stage at source freeze; current outcomes live here and in ignored source runtime receipts.
