# Rollback plan — Fix issue50 architecture diagnostics: exact source locations, malformed path and line-skip rejection, bounded architecture input preflight in verifier.

## Trigger conditions

A previously valid configured model becomes inadmissible unexpectedly, coordinates disagree with physical source, or a refusal allows an expensive dependent check to run.

## Application rollback

Forward-fix or revert this isolated source commit through a new reviewed PR; rerun architecture and verifier compatibility modules and full applicable verification before delivery. No deployed process or feature activation changes in this contour.

## Data recovery / forward-fix

No migration, persistent-data write, credential or deployed-setting change. Correct a malformed model in its own source change rather than silently normalize a path or downgrade an unloadable input.

## Verification after rollback

Current valid load/digests/generated views, adoption/history fail-closed behavior and root discovery retain their known behavior; reconcile new malformed-input checks explicitly if reverting the preflight.
