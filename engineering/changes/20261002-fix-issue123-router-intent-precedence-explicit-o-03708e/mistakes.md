# Implementation corrections

The first implementation import failed because a single-quoted regex contained an unescaped single quote in its character class. Use a double-quoted Python fragment for single-quote matching; the corrected matrix imports and passes.

The initial quote filter assumed single-line content and treated an apostrophe inside a quoted contraction as the closing quote. Three fresh RED cases showed coordinated publish text leaking from those spans; preserve internal word apostrophes and consume multiline/incomplete quoted content conservatively.

Whole-clause historical markers and whole-object negative/past-state scans confused artifact/context qualifiers with the requested action; coordinator splitting also lost descriptive infinitive scope and the noun guard omitted plurals. Both independent reviews exposed these root causes after a green initial suite, so the repair adds their exact cases, binds exclusions to instruction context, carries descriptive scope, and tests marker-only history independently; the previous full verifier and reviews are stale for the repaired candidate.

The first scoped repair still split numeric version periods before seeing a past predicate, recognized only one-token historical subjects, and implemented plan context only in English despite an EN/RU contract. The second reviews exposed those coverage gaps; six exact RED cases now protect numeric segmentation, bounded multiword declarations without consuming relative qualifiers, and Russian plan coordination with an optional colon.
