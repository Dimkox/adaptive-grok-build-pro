# Rollback plan — Model Agnostic Autonomous Factory

## Trigger conditions

User rejects the design, self-review finds a contradiction/security/scope defect, typed validation fails, or the commit contains anything outside the approved design/docs scope.

## Application rollback

No application/runtime change exists. Before commit, correct the documents with a bounded patch. After the local commit, use a normal follow-up design commit if the user requests changes; do not rewrite unrelated history.

## Data recovery / forward-fix

No database or external data is touched. The durable package and reports remain review evidence; superseded design text is corrected explicitly rather than hidden.

## Verification after rollback

Re-run typed-spec validation, placeholder/contradiction/security/scope review, Markdown diff checks, and repository verification against the new exact tree. The package remains behind the user approval gate.
