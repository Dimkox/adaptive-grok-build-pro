# Rollback plan — Fix governance and architecture Git input hardening: explicit repository object binding, controlled Git environment, filter-free committed reads and pinned bounded regular-file projections.

## Trigger conditions

Unexpected rejection of a supported registered repository, changed successful CLI shape, stale-input publication or architecture compatibility failure blocks acceptance.

## Application rollback

Revert this isolated PR through a successor reviewed PR. Do not reset, modify historical recovery trees or rewrite shared history.

## Data recovery / forward-fix

No database or persistent product writes occur. Projection commands still only emit JSON and never write Markdown; evidence is retained. A bounded forward fix can restore supported binding compatibility without relaxing identity/content or external authority gates.

## Verification after rollback

Run governance/governance_fitness/architecture_fitness suites, full PR verifier and selected independent reviews on the exact rollback candidate; require external exact-head Trust CI before merge.
