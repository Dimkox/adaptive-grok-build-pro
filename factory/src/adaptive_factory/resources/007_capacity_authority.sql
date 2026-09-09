ALTER TABLE factory.capacity_counters
  ADD CONSTRAINT capacity_counters_canonical_policy CHECK (
    (scope_key='global:reader' AND ceiling=20)
    OR (scope_key='global:writer' AND ceiling=1)
    OR (
      left(scope_key,11)='repository:' AND right(scope_key,7)=':reader'
      AND octet_length(scope_key) BETWEEN 19 AND 146 AND ceiling=10
    )
  );

CREATE FUNCTION factory.capacity_eligible_repositories(p_role text, p_repositories text[])
RETURNS SETOF text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path=pg_catalog,factory
AS $$
DECLARE
  repository text;
  global_active integer;
  global_ceiling integer;
BEGIN
  IF p_role NOT IN ('reader','writer') OR cardinality(p_repositories) IS NULL THEN
    RAISE EXCEPTION 'invalid capacity request';
  END IF;
  SELECT active_count,ceiling INTO STRICT global_active,global_ceiling
  FROM factory.capacity_counters WHERE scope_key='global:' || p_role FOR UPDATE;
  IF global_active >= global_ceiling THEN
    RETURN;
  END IF;
  IF p_role='writer' THEN
    RETURN QUERY SELECT DISTINCT value FROM unnest(p_repositories) AS value;
    RETURN;
  END IF;
  FOREACH repository IN ARRAY p_repositories LOOP
    IF octet_length(repository) NOT BETWEEN 1 AND 128 THEN
      RAISE EXCEPTION 'invalid repository capacity identity';
    END IF;
    INSERT INTO factory.capacity_counters(scope_key,active_count,ceiling)
    VALUES ('repository:' || repository || ':reader',0,10) ON CONFLICT DO NOTHING;
  END LOOP;
  PERFORM scope_key FROM factory.capacity_counters
  WHERE scope_key=ANY(ARRAY(
    SELECT 'repository:' || value || ':reader' FROM unnest(p_repositories) AS value
  )) ORDER BY scope_key FOR UPDATE;
  FOREACH repository IN ARRAY p_repositories LOOP
    IF EXISTS (
      SELECT 1 FROM factory.capacity_counters
      WHERE scope_key='repository:' || repository || ':reader' AND active_count < ceiling
    ) THEN
      RETURN NEXT repository;
    END IF;
  END LOOP;
END;
$$;

CREATE FUNCTION factory.capacity_lock_run(p_run_id uuid)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path=pg_catalog,factory
AS $$
DECLARE
  allocation_role text;
  allocation_repository text;
  keys text[];
BEGIN
  SELECT role,repository_id INTO allocation_role,allocation_repository
  FROM factory.capacity_allocations WHERE run_id=p_run_id AND released_at IS NULL;
  IF NOT FOUND THEN RETURN false; END IF;
  keys := ARRAY['global:' || allocation_role];
  IF allocation_role='reader' THEN
    keys := array_append(keys,'repository:' || allocation_repository || ':reader');
  END IF;
  PERFORM scope_key FROM factory.capacity_counters
  WHERE scope_key=ANY(keys) ORDER BY scope_key FOR UPDATE;
  RETURN true;
END;
$$;

CREATE FUNCTION factory.capacity_allocate(
  p_allocation_id uuid, p_run_id uuid, p_task_id uuid, p_repository_id text, p_role text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path=pg_catalog,factory
AS $$
DECLARE
  keys text[];
  inserted uuid;
BEGIN
  IF p_role NOT IN ('reader','writer') OR octet_length(p_repository_id) NOT BETWEEN 1 AND 128 THEN
    RAISE EXCEPTION 'invalid allocation identity';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM factory.runs r JOIN factory.tasks t ON t.task_id=r.task_id
    WHERE r.run_id=p_run_id AND r.task_id=p_task_id AND r.role=p_role
      AND t.repository_id=p_repository_id AND r.state='leased' AND r.released_at IS NULL
  ) THEN
    RAISE EXCEPTION 'allocation does not match a live run';
  END IF;
  IF p_role='reader' THEN
    INSERT INTO factory.capacity_counters(scope_key,active_count,ceiling)
    VALUES ('repository:' || p_repository_id || ':reader',0,10) ON CONFLICT DO NOTHING;
  END IF;
  keys := ARRAY['global:' || p_role];
  IF p_role='reader' THEN
    keys := array_append(keys,'repository:' || p_repository_id || ':reader');
  END IF;
  PERFORM scope_key FROM factory.capacity_counters
  WHERE scope_key=ANY(keys) ORDER BY scope_key FOR UPDATE;
  IF EXISTS (
    SELECT 1 FROM factory.capacity_counters
    WHERE scope_key=ANY(keys) AND active_count >= ceiling
  ) THEN
    RETURN false;
  END IF;
  INSERT INTO factory.capacity_allocations(allocation_id,run_id,task_id,repository_id,role)
  VALUES (p_allocation_id,p_run_id,p_task_id,p_repository_id,p_role)
  ON CONFLICT DO NOTHING RETURNING allocation_id INTO inserted;
  IF inserted IS NULL THEN RETURN false; END IF;
  UPDATE factory.capacity_counters SET active_count=active_count+1 WHERE scope_key=ANY(keys);
  RETURN true;
END;
$$;

CREATE FUNCTION factory.capacity_release(p_run_id uuid)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path=pg_catalog,factory
AS $$
DECLARE
  allocation_role text;
  allocation_repository text;
  keys text[];
BEGIN
  SELECT role,repository_id INTO allocation_role,allocation_repository
  FROM factory.capacity_allocations WHERE run_id=p_run_id AND released_at IS NULL;
  IF NOT FOUND THEN RETURN false; END IF;
  keys := ARRAY['global:' || allocation_role];
  IF allocation_role='reader' THEN
    keys := array_append(keys,'repository:' || allocation_repository || ':reader');
  END IF;
  PERFORM scope_key FROM factory.capacity_counters
  WHERE scope_key=ANY(keys) ORDER BY scope_key FOR UPDATE;
  PERFORM 1 FROM factory.capacity_allocations a JOIN factory.runs r ON r.run_id=a.run_id
  WHERE a.run_id=p_run_id AND a.released_at IS NULL AND r.released_at IS NOT NULL FOR UPDATE OF a;
  IF NOT FOUND THEN RAISE EXCEPTION 'run must close before capacity release'; END IF;
  IF EXISTS (SELECT 1 FROM factory.capacity_counters WHERE scope_key=ANY(keys) AND active_count <= 0) THEN
    RAISE EXCEPTION 'capacity counter underflow';
  END IF;
  UPDATE factory.capacity_allocations SET released_at=clock_timestamp()
  WHERE run_id=p_run_id AND released_at IS NULL;
  UPDATE factory.capacity_counters SET active_count=active_count-1 WHERE scope_key=ANY(keys);
  RETURN true;
END;
$$;

REVOKE ALL ON FUNCTION factory.capacity_eligible_repositories(text,text[]) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.capacity_lock_run(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.capacity_allocate(uuid,uuid,uuid,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.capacity_release(uuid) FROM PUBLIC;
REVOKE INSERT, UPDATE ON factory.capacity_counters FROM factory_runtime;
REVOKE INSERT ON factory.capacity_allocations FROM factory_runtime;
GRANT EXECUTE ON FUNCTION factory.capacity_eligible_repositories(text,text[]) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.capacity_lock_run(uuid) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.capacity_allocate(uuid,uuid,uuid,text,text) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.capacity_release(uuid) TO factory_runtime;
