# Rollback plan — M7 local shadow handoff

Trigger rollback if the future contract accepts stale/replayed/contradictory/non-pass/external-capability input, the cohort mixes tuples or misclassifies safety, or restacked producer facts require invented semantics.

Before a PR, abandon/revert only M7 commits; M4 remains unchanged because no runtime/store integration or migration exists. After a future PR, revert exact M7 commits through a reviewed PR. There is no database/external state. Invalid derived content-addressed values are discarded and rebuilt from new accepted evidence; historical evidence is never edited.

After rollback run the pre-M7 factory suite and repository preflight, then confirm no shadow module is imported by M4 runtime and no migration exists.
