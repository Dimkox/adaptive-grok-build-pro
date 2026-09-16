# Rollback plan — v2.0.18 release sync (R)

## Trigger

Coupled identity/record tests fail post-merge or a landing row proves mis-derived.

## Move

Forward-fix commit correcting the record (strategy `forward_fix`, ≤2 steps). Published releases are immutable and untouched by this wave, so no restore of tags, artifacts or runtime state is ever implicated; reverting the whole commit is also safe because no external effect exists to unwind.
