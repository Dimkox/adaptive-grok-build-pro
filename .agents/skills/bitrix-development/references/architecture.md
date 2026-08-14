# Bitrix architecture guidance

- New custom code belongs under `local/` whenever the deployment supports it.
- D7 is the default for new code, but brownfield compatibility may require controlled legacy adapters.
- Prefer composition and encapsulation; framework base-class inheritance can create update coupling.
- Keep request/bootstrap concerns at the edge and isolate domain logic from global `$APPLICATION`, `$USER`, `$DB`, and page lifecycle.
- Use explicit services for permissions, cache invalidation, external synchronization, and business operations.
- Avoid N+1 ORM/iblock queries. Batch IDs and select only needed fields.
- Treat highload blocks and iblocks as framework persistence mechanisms, not permission to spread raw arrays across the codebase.
