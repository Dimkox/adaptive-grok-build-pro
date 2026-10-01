-- Canonicalize only the exact public pre-release histories superseded by this migration.
CREATE TABLE factory.migration_checksum_reconciliations (
  version integer PRIMARY KEY CHECK (version IN (31,34,35)),
  previous_checksum char(64) NOT NULL CHECK (previous_checksum ~ '^[0-9a-f]{64}$'),
  current_checksum char(64) NOT NULL CHECK (current_checksum ~ '^[0-9a-f]{64}$'),
  canonicalizer integer NOT NULL CHECK (canonicalizer=36),
  reconciled_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  CHECK (previous_checksum<>current_checksum)
);

DO $$
DECLARE
  v31 factory.schema_migrations%ROWTYPE;
  v34 factory.schema_migrations%ROWTYPE;
  v35 factory.schema_migrations%ROWTYPE;
  current31 constant text := '23e2d280a391a174b020055a7a4aeaf06207d5f3c157666ac4b5f24473dbfa90';
  current34 constant text := '3701115497d6614f0a3f7e41bf318e4e3f995768b298691a704115207cfc9913';
  current35 constant text := '272d8a385d87d00779ab7d6b219cd01af0981603bdb7ddb7d07a7ef050a89216';
  legacy31 constant text := '33d846f8f29c51264547cb9d924e947762c7ff8366521cdb6483b832c796f8a7';
  legacy34 constant text := 'e1e979f6adf7dc14fed76fbba4ff894eee5be823c925881629c35471108c1347';
  legacy35 constant text := 'b7285c70b5bea53a5e7eac9757f631373264e923fac82b2933e1a6655aa53207';
BEGIN
  SELECT * INTO STRICT v31 FROM factory.schema_migrations WHERE version=31;
  SELECT * INTO STRICT v34 FROM factory.schema_migrations WHERE version=34;
  SELECT * INTO STRICT v35 FROM factory.schema_migrations WHERE version=35;
  IF v31.name<>'031_native_execution_delivery.sql'
    OR v34.name<>'034_native_execution_live_grants.sql'
    OR v35.name<>'035_serialize_native_execution_revocation.sql'
    OR NOT (
      (v31.sha256=legacy31 AND v34.sha256=legacy34 AND v35.sha256 IN (legacy35,current35))
      OR (v31.sha256=legacy31 AND v34.sha256=current34 AND v35.sha256=current35)
      OR (v31.sha256=current31 AND v34.sha256=current34 AND v35.sha256=current35)
    )
  THEN RAISE EXCEPTION 'migration 036 refuses unrecognized RC checksum history'; END IF;

  INSERT INTO factory.migration_checksum_reconciliations
    (version,previous_checksum,current_checksum,canonicalizer)
  SELECT version,sha256,
    CASE version WHEN 31 THEN current31 WHEN 34 THEN current34 ELSE current35 END,36
  FROM factory.schema_migrations
  WHERE (version=31 AND sha256=legacy31)
    OR (version=34 AND sha256=legacy34)
    OR (version=35 AND sha256=legacy35);

  UPDATE factory.schema_migrations SET sha256=current31
  WHERE version=31 AND name='031_native_execution_delivery.sql' AND sha256=legacy31;
  UPDATE factory.schema_migrations SET sha256=current34
  WHERE version=34 AND name='034_native_execution_live_grants.sql' AND sha256=legacy34;
  UPDATE factory.schema_migrations SET sha256=current35
  WHERE version=35 AND name='035_serialize_native_execution_revocation.sql' AND sha256=legacy35;
END $$;

REVOKE ALL ON factory.migration_checksum_reconciliations
FROM PUBLIC,factory_runtime,factory_migrator;
GRANT SELECT ON factory.migration_checksum_reconciliations TO factory_audit_reader;
