# Integration architecture: transferable evidence requirements

Route: `78b680187560`. Role: `integration_architect`. Method: read-only comparison of pinned delivery refs, original heads and landed identities; detailed source findings remain private.

Select an explicit delivery ref when reconstructing historical delivery. The default branch and its latest timestamp may describe a different baseline. An open stacked PR head can already be reachable in the selected delivery ref, so open status alone cannot establish undelivered work.

Preserve both original head and landed merge identities. Exact identity reachability is separate from semantic code delivery: squash merges and cherry-picks can preserve changes without retaining the original commit identity. Classify branch synchronization separately and deduplicate source identities without creating additional accepted tasks.

Keep merged delivery, explicit task acceptance, operator-event coverage and exact-profile metadata as independent fields. A user-account merge or an application approval policy does not measure engineering intervention. Partial event evidence is a lower bound and cannot establish complete-session autonomy.

Historical profile revisions require contemporaneous sources. Missing digests must not be reconstructed from current configuration, and unsupported task classes must remain visible as observed work without being silently converted into an eligible cohort. Local validation claims remain separate from current exact-SHA external trust evidence.

The resulting gap report has no activation or operational authority. Public reports retain these general rules; inventory quantities, private decisions and observed source outcomes remain in private evidence artifacts.
