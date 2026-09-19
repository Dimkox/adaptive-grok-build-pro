# Docs and contract research — issue #125

M1 typed-spec design explicitly requires evidence for AC and is silent on INV/FORBID. The schema requires an evidence array for all categories but allows `[]`. Trust CI `criterion_coverage` and local receipts currently have AC-only signed/bound semantics; changing that wire meaning needs a versioned, separately deployed policy/service change. A local gate can enforce INV/FORBID while preserving current AC-only attestation semantics.
