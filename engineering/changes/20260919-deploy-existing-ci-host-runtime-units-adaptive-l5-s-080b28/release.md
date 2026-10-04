# Operational decision: partial rollout, Qwen recovered

Grok at 26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960 is GO for this bounded artifact-generation acceptance. Primary Qwen Omni at that revision is NO-GO: transport/usage completed but its draft was rejected. It was disabled, its failed v2 data preserved, and the original qwen-intl runtime fully restored. Both current services and the untouched separate Omni service are active and enabled.

This is an operational record, not a new product release. VERSION, published tags/assets and deployed Trust CI remain unchanged. Local verification must record the failed overall objective. The docs/evidence branch may be reviewed and merged through exact-head external Trust CI without asserting Qwen acceptance or M8/M9 qualification.

The next Qwen investigation must preserve an allowlisted decoder failure code/real response digest without raw content, test schema-versus-validator boundaries offline, and only then justify a new bounded acceptance. The old rejected reply cannot be reconstructed and must not be represented as a deterministic reproduction.
