# Requirements and scope ruling

The user approved the detailed seven-PR execution and said «Делай». This satisfies the existing scope/design decision; do not ask again. The route migration_or_external_write_approval gate applies to operational migration/external writes, none of which is exercised by this source-only slice. This is an applicability ruling, not a signed security approval or permission to deploy.

Preserve strict Qwen region and private-key selection, bounded HTTP/SSE/media parsing, no replay of ambiguous outcomes, default-off operation, writer ownership before quarantine or credentials, and v1/v2 retained reader compatibility. Prioritize failure-injection coverage for initialization interruption and cleanup failure. A reproduced SQLite constructor lock leak may receive the smallest cleanup repair; disclose that exact production deviation from frozen source.
