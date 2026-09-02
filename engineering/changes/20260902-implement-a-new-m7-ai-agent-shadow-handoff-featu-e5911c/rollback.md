# Rollback plan — M7 local shadow handoff

Trigger rollback if the future contract accepts stale/replayed/non-pass/external-capability input, exposes readiness from opaque caller digests, accepts a direct aggregate, mixes cohort tuples or requires invented producer semantics.

Before a PR, abandon/revert the isolated M7 source commits `9152daf`, `030a8d7` and `5615933` (plus their documentation successors); M4 remains unchanged because no runtime/store integration or migration exists. After a future PR, revert exact M7 commits through a reviewed PR. There is no database/external state. Invalid derived content-addressed values are discarded and rebuilt from new accepted evidence; historical evidence is never edited.

After rollback run the pre-M7 factory suite and repository preflight, then confirm no shadow module is imported by M4 runtime and no migration exists.
