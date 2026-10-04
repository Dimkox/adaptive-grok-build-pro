# Upgrade existing Claw runtime units

Result: partial upgrade. Grok accepted the target; Qwen Omni failed draft validation and the primary was fully restored to its original runtime. See evidence/final-runtime.json and release.md. The two-service acceptance criterion remains unmet.

User-approved operational change: move adaptive-l5.service and adaptive-l5-grok.service to merged control revision 26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960. Primary selects qwen-omni-intl; Grok retains grok-vision. The separate Omni service remains its existing installation.

The exact procedure, source provenance, bounded acceptance and rollback are in evidence/operations-plan.md. No product behavior, VERSION, tag, release, Trust CI deployment or public site changes are included. This operation does not establish an accepted external issue-to-PR pilot or M8 activation.

Acceptance: both named units active/running and enabled on the target executable/config; authenticated exact-profile capability and one durable artifact_ready synthetic job each; preserved original unit/config and independently complete per-service SQLite/artifact snapshot; aggregate pre/post row counts and schema transition recorded; original third Omni unit unchanged.
