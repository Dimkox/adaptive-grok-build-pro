# L5 live-path fix: canonicalize model item order

The installed v2.0.16 runner rejects every real model draft: `_sorted_unique` demands items already sorted+unique, which HTTP models never emit (observed needs_human/http_outcome_unusable on live submissions; the direct executor probe returns a valid 1.5KB draft). decode_landing_draft now sorts and deduplicates all-string item lists before strict validation; everything else keeps the previous fail-closed behavior.
