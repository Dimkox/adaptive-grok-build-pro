# Contour E decisions

Preserving the current descriptor-pinned authority topology and clean/current-head handoff gates avoided importing the historical draft's weaker dirty-state semantics. The existing raw blob batch reader and capped runner supplied the needed safeguards without replacing stronger helpers.

Repository status can hide assume-unchanged governance paths; a direct final authority/content recheck killed the reproduced late-mutation publication case. Projection output now uses one pinned observation for merge, digest and mismatch calculation and rechecks it before emission.

Architecture supports full native SHA-1/SHA-256 commit identities, while the frozen GovernanceHandoffV1 schema remains SHA-1-only. Explicit unsupported refusal keeps the contract compatible and avoids silently changing evidence semantics.

Pinning Git registration identities before reading and validating the common-directory relationship caught two reproduced object-store redirects that explicit --git-dir alone did not exclude. Once the unique-byte budget is exhausted, further evidence reads stop even when validation converts individual errors into findings.
