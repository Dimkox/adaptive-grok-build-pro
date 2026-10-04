# Architecture

`build_route` loads `.grok-stack/config/routing.json` (fallback `DEFAULT_ROUTING`). Analysis assembly:

1. `analysis_floors.always`
2. `feature_like` when intent is feature/architecture/refactor/research
3. `standard` (`architect`, `docs_researcher`) when complexity is not micro
4. `architect` only when micro **and** feature-like
5. domain architects on match
6. `unique_ordered(analysis)[:cap]`

Review names come from the same file; predicates stay in Python. Policy loads `write_roles` from the file with `WRITE_ROLES` fallback. No analysis semaphore. No padding.
