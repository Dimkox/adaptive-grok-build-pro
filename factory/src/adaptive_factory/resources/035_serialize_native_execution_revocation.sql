-- Serialize direct runtime reads and budget mutations with lease release and kill publication.
CREATE TABLE factory.migration_checksum_reconciliations (
  version integer PRIMARY KEY CHECK (version IN (31,34)),
  previous_checksum char(64) NOT NULL CHECK (previous_checksum ~ '^[0-9a-f]{64}$'),
  current_checksum char(64) NOT NULL CHECK (current_checksum ~ '^[0-9a-f]{64}$'),
  canonicalizer integer NOT NULL CHECK (canonicalizer=35),
  reconciled_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  CHECK (previous_checksum<>current_checksum)
);

DO $$
DECLARE
  v31 factory.schema_migrations%ROWTYPE;
  v34 factory.schema_migrations%ROWTYPE;
  current31 constant text := '23e2d280a391a174b020055a7a4aeaf06207d5f3c157666ac4b5f24473dbfa90';
  current34 constant text := '3701115497d6614f0a3f7e41bf318e4e3f995768b298691a704115207cfc9913';
  legacy31 constant text := '33d846f8f29c51264547cb9d924e947762c7ff8366521cdb6483b832c796f8a7';
  legacy34 constant text := 'e1e979f6adf7dc14fed76fbba4ff894eee5be823c925881629c35471108c1347';
BEGIN
  SELECT * INTO STRICT v31 FROM factory.schema_migrations WHERE version=31;
  SELECT * INTO STRICT v34 FROM factory.schema_migrations WHERE version=34;
  IF v31.name<>'031_native_execution_delivery.sql'
    OR v31.sha256 NOT IN (legacy31,current31)
    OR v34.name<>'034_native_execution_live_grants.sql'
    OR v34.sha256 NOT IN (legacy34,current34)
  THEN RAISE EXCEPTION 'migration 035 refuses unrecognized RC checksum history'; END IF;

  INSERT INTO factory.migration_checksum_reconciliations
    (version,previous_checksum,current_checksum,canonicalizer)
  SELECT version,sha256,
    CASE version WHEN 31 THEN current31 ELSE current34 END,35
  FROM factory.schema_migrations
  WHERE (version=31 AND sha256=legacy31) OR (version=34 AND sha256=legacy34);

  UPDATE factory.schema_migrations SET sha256=current31
  WHERE version=31 AND name='031_native_execution_delivery.sql' AND sha256=legacy31;
  UPDATE factory.schema_migrations SET sha256=current34
  WHERE version=34 AND name='034_native_execution_live_grants.sql' AND sha256=legacy34;
END $$;

CREATE OR REPLACE FUNCTION factory.execution_consume_analysis_budget(
  p_task uuid,p_run uuid,p_owner text,p_fence bigint,p_packet char(64),
  p_rounds integer,p_tools integer,p_facts char(64),p_blocker char(64)
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v factory.execution_analysis_budgets%ROWTYPE;
  v_repository text;
BEGIN
  IF p_rounds<0 OR p_tools<0 OR p_rounds+p_tools=0 THEN RAISE EXCEPTION 'invalid analysis consumption'; END IF;

  -- Release locks these authoritative rows. Keep this first so lease revocation and
  -- runtime consumption have a single ordering point.
  SELECT t.repository_id INTO v_repository
  FROM factory.runs r JOIN factory.tasks t ON t.task_id=r.task_id
  WHERE r.task_id=p_task AND r.run_id=p_run AND r.owner_id=p_owner AND r.fence=p_fence
  FOR UPDATE OF r,t;
  IF NOT FOUND THEN RAISE EXCEPTION 'analysis budget binding mismatch'; END IF;

  -- A kill insert updates kill_switch_heads in its trigger. SHARE blocks both an
  -- UPDATE and a first INSERT, closing the otherwise-unlockable missing-row race.
  LOCK TABLE factory.kill_switch_heads IN SHARE MODE;

  IF NOT EXISTS (
    SELECT 1 FROM factory.runs r
    JOIN factory.tasks t ON t.task_id=r.task_id
    JOIN factory.execution_native_contexts c ON c.run_id=r.run_id
    WHERE r.task_id=p_task AND r.run_id=p_run AND r.owner_id=p_owner AND r.fence=p_fence
      AND r.state='leased' AND r.released_at IS NULL AND r.lease_expires_at>clock_timestamp()
      AND t.current_run_id=r.run_id AND t.current_fence=r.fence
      AND t.deadline_at>clock_timestamp() AND c.packet_digest=p_packet
      AND NOT EXISTS (SELECT 1 FROM factory.kill_switch_heads k
        WHERE k.enabled AND k.scope_key IN ('global','repository:'||v_repository))
  ) THEN RAISE EXCEPTION 'analysis budget binding mismatch'; END IF;

  SELECT * INTO v FROM factory.execution_analysis_budgets WHERE run_id=p_run FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'analysis budget unavailable'; END IF;
  -- Recheck clock-based authority at the mutation statement boundary.
  IF NOT EXISTS (
    SELECT 1 FROM factory.runs r JOIN factory.tasks t ON t.task_id=r.task_id
    WHERE r.run_id=p_run AND r.task_id=p_task AND r.state='leased' AND r.released_at IS NULL
      AND r.lease_expires_at>clock_timestamp() AND t.current_run_id=r.run_id
      AND t.current_fence=r.fence AND t.deadline_at>clock_timestamp()
  ) THEN RAISE EXCEPTION 'analysis budget binding mismatch'; END IF;
  IF v.status='exhausted' OR v.used_rounds+p_rounds>v.max_rounds
    OR v.used_tool_operations+p_tools>v.max_tool_operations THEN
    IF p_facts IS NULL OR p_blocker IS NULL THEN RAISE EXCEPTION 'exhaustion evidence required'; END IF;
    UPDATE factory.execution_analysis_budgets SET status='exhausted',facts_digest=p_facts,
      blocker_digest=p_blocker,updated_at=clock_timestamp() WHERE run_id=p_run;
    RETURN jsonb_build_object('accepted',false,'status','exhausted','used_rounds',v.used_rounds,
      'used_tool_operations',v.used_tool_operations);
  END IF;
  UPDATE factory.execution_analysis_budgets SET used_rounds=used_rounds+p_rounds,
    used_tool_operations=used_tool_operations+p_tools,updated_at=clock_timestamp() WHERE run_id=p_run;
  RETURN jsonb_build_object('accepted',true,'status','active','used_rounds',v.used_rounds+p_rounds,
    'used_tool_operations',v.used_tool_operations+p_tools);
END $$;

CREATE OR REPLACE FUNCTION factory.execution_native_context(
  p_task uuid,p_run uuid,p_owner text,p_fence bigint,p_packet char(64)
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_body jsonb;
  v_repository text;
BEGIN
  SELECT t.repository_id INTO v_repository
  FROM factory.runs r JOIN factory.tasks t ON t.task_id=r.task_id
  WHERE r.task_id=p_task AND r.run_id=p_run AND r.owner_id=p_owner AND r.fence=p_fence
  FOR UPDATE OF r,t;
  IF NOT FOUND THEN RETURN NULL; END IF;

  LOCK TABLE factory.kill_switch_heads IN SHARE MODE;
  SELECT c.body INTO v_body FROM factory.execution_native_contexts c
  JOIN factory.runs r ON r.run_id=c.run_id JOIN factory.tasks t ON t.task_id=r.task_id
  WHERE r.task_id=p_task AND r.run_id=p_run AND r.owner_id=p_owner AND r.fence=p_fence
    AND r.state='leased' AND r.released_at IS NULL AND r.lease_expires_at>clock_timestamp()
    AND t.current_run_id=r.run_id AND t.current_fence=r.fence
    AND t.deadline_at>clock_timestamp() AND c.packet_digest=p_packet
    AND NOT EXISTS (SELECT 1 FROM factory.kill_switch_heads k
      WHERE k.enabled AND k.scope_key IN ('global','repository:'||v_repository));
  RETURN v_body;
END $$;

REVOKE ALL ON FUNCTION
  factory.execution_consume_analysis_budget(uuid,uuid,text,bigint,char,integer,integer,char,char),
  factory.execution_native_context(uuid,uuid,text,bigint,char)
FROM PUBLIC,factory_runtime,factory_migrator;
GRANT EXECUTE ON FUNCTION
  factory.execution_consume_analysis_budget(uuid,uuid,text,bigint,char,integer,integer,char,char),
  factory.execution_native_context(uuid,uuid,text,bigint,char)
TO factory_runtime;

REVOKE ALL ON factory.migration_checksum_reconciliations
FROM PUBLIC,factory_runtime,factory_migrator;
GRANT SELECT ON factory.migration_checksum_reconciliations TO factory_audit_reader;
