# Architecture

Take frozen delivery landing_filesystem, landing_publication, landing_publication_contracts and request-v1 schema; factory landing_publication_cli and its tests; scripts/grok_landing_publish; factory/tests/__init__.py bootstrap. Add exact request-schema owner and offline CLI source/rule/inventory, reaching 21 actual modules. Existing staged-delivery urllib.parse exception remains exact, with no broader urllib/network allowance. Do not introduce backup or its imports until G. No factory console script change belongs to F. Preserve C/D/E code and tests, especially D lock cleanup.

F data analysis identifies a frozen-source validation gap: application/version and column names alone accept a v1 table without request-id uniqueness or with added triggers. Sole writer must reproduce the supplied temporary-database RED cases and apply the smallest fail-closed supported-v1-schema validation. Disclose the exact tested correction from frozen source; do not add migration, new state or a framework.

## Independent conflict-policy repair

Initial F2 full verification passed but security/data reviews reproduced SQLite UNIQUE ON CONFLICT REPLACE bypassing PRAGMA-only schema validation and replacing a durable intent through the store API. The supported coordinator precheck limited CLI impact; it did not make the store guarantee valid. Preserve the initial pass and both FAIL reports as historical evidence.

Bind sqlite_schema.sql to the supported application-created v1 CREATE TABLE after case/whitespace normalization only, retaining all existing PRAGMA checks; comments, quotes and extra clauses remain distinct unsupported declarations. INSERT OR ABORT separately enforces no replacement at this insert. Existing generated schemas and backup/restore serialization retain the same application ID/user version and DDL; no migration is introduced. Hand-authored schemas outside the closed supported declaration are refused and preserved for diagnosis.
