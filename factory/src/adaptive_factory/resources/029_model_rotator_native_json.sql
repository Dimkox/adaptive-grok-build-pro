-- Additive strict native-JSON validation over immutable migrations 027/028.
ALTER FUNCTION factory.model_rotator_claim_v1(jsonb,text,char,char,integer,char,bigint)
  RENAME TO model_rotator_claim_v1_028;
ALTER FUNCTION factory.model_rotator_reserve_v1(char,char,text,bigint)
  RENAME TO model_rotator_reserve_v1_028;
ALTER FUNCTION factory.model_rotator_finish_v1(char,char,jsonb,jsonb,integer,bigint)
  RENAME TO model_rotator_finish_v1_028;
ALTER FUNCTION factory.model_rotator_quarantine_v1(char,char,jsonb)
  RENAME TO model_rotator_quarantine_v1_028;
ALTER FUNCTION factory.model_rotator_reconcile_v1(char,text)
  RENAME TO model_rotator_reconcile_v1_028;

REVOKE ALL ON FUNCTION
  factory.model_rotator_claim_v1_028(jsonb,text,char,char,integer,char,bigint),
  factory.model_rotator_reserve_v1_028(char,char,text,bigint),
  factory.model_rotator_finish_v1_028(char,char,jsonb,jsonb,integer,bigint),
  factory.model_rotator_quarantine_v1_028(char,char,jsonb),
  factory.model_rotator_reconcile_v1_028(char,text)
FROM PUBLIC, factory_runtime, factory_migrator;

CREATE FUNCTION factory.model_rotator_claim_v1(
  p_binding jsonb,p_wire text,p_binding_digest char(64),p_registry char(64),
  p_cursor integer,p_requested char(64),p_now bigint
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE v_name text;
BEGIN
  IF p_binding IS NULL OR jsonb_typeof(p_binding)<>'object'
    OR p_binding->'schema_version' IS DISTINCT FROM '1'::jsonb
  THEN RETURN jsonb_build_object('error','binding_digest_mismatch'); END IF;
  FOREACH v_name IN ARRAY ARRAY[
    'tenant_id','repository_id','task_id','run_id','attempt_id',
    'budget_reservation_id','budget_digest','registry_digest','operation_id',
    'requested_provider_id','requested_model_id'
  ] LOOP
    IF jsonb_typeof(p_binding->v_name) IS DISTINCT FROM 'string'
    THEN RETURN jsonb_build_object('error','binding_digest_mismatch'); END IF;
  END LOOP;
  FOREACH v_name IN ARRAY ARRAY['fence','remaining_token_units','remaining_request_units'] LOOP
    IF jsonb_typeof(p_binding->v_name) IS DISTINCT FROM 'number'
    THEN RETURN jsonb_build_object('error','binding_digest_mismatch'); END IF;
    IF (p_binding->>v_name)::numeric<>trunc((p_binding->>v_name)::numeric)
      OR (p_binding->>v_name)::numeric<(CASE WHEN v_name='fence' THEN 1 ELSE 0 END)
      OR (p_binding->>v_name)::numeric>9223372036854775807
    THEN RETURN jsonb_build_object('error','binding_digest_mismatch'); END IF;
  END LOOP;
  RETURN factory.model_rotator_claim_v1_028(
    p_binding,p_wire,p_binding_digest,p_registry,p_cursor,p_requested,p_now
  );
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN
  RETURN jsonb_build_object('error','binding_digest_mismatch');
END $$;

CREATE FUNCTION factory.model_rotator_reserve_v1(
  p_binding char(64),p_claim char(64),p_mode text,p_units bigint
) RETURNS boolean
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT factory.model_rotator_reserve_v1_028(p_binding,p_claim,p_mode,p_units)
$$;

CREATE FUNCTION factory.model_rotator_finish_v1(
  p_binding char(64),p_claim char(64),p_evidence jsonb,p_cooldowns jsonb,
  p_cursor integer,p_version bigint
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE v_value jsonb;
BEGIN
  IF p_evidence IS NULL OR jsonb_typeof(p_evidence)<>'object'
    OR jsonb_typeof(p_evidence->'evidence_digest') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_evidence->'next_model_digest') IS DISTINCT FROM 'string'
    OR p_cooldowns IS NULL OR jsonb_typeof(p_cooldowns)<>'object'
  THEN RETURN false; END IF;
  FOR v_value IN SELECT value FROM jsonb_each(p_cooldowns) LOOP
    IF jsonb_typeof(v_value) IS DISTINCT FROM 'number'
      OR (v_value#>>'{}')::numeric<>trunc((v_value#>>'{}')::numeric)
      OR (v_value#>>'{}')::numeric<0
      OR (v_value#>>'{}')::numeric>9223372036854775807
    THEN RETURN false; END IF;
  END LOOP;
  RETURN factory.model_rotator_finish_v1_028(
    p_binding,p_claim,p_evidence,p_cooldowns,p_cursor,p_version
  );
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN RETURN false;
END $$;

CREATE FUNCTION factory.model_rotator_quarantine_v1(
  p_binding char(64),p_claim char(64),p_evidence jsonb
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  IF p_evidence IS NULL OR jsonb_typeof(p_evidence)<>'object'
    OR jsonb_typeof(p_evidence->'evidence_digest') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_evidence->'outcome_digest') IS DISTINCT FROM 'string'
  THEN RETURN false; END IF;
  RETURN factory.model_rotator_quarantine_v1_028(p_binding,p_claim,p_evidence);
END $$;

CREATE FUNCTION factory.model_rotator_reconcile_v1(
  p_binding char(64),p_outcome text
) RETURNS boolean
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT factory.model_rotator_reconcile_v1_028(p_binding,p_outcome)
$$;

REVOKE ALL ON FUNCTION
  factory.model_rotator_claim_v1(jsonb,text,char,char,integer,char,bigint),
  factory.model_rotator_reserve_v1(char,char,text,bigint),
  factory.model_rotator_finish_v1(char,char,jsonb,jsonb,integer,bigint),
  factory.model_rotator_quarantine_v1(char,char,jsonb),
  factory.model_rotator_reconcile_v1(char,text)
FROM PUBLIC, factory_runtime, factory_migrator;
GRANT EXECUTE ON FUNCTION
  factory.model_rotator_claim_v1(jsonb,text,char,char,integer,char,bigint),
  factory.model_rotator_reserve_v1(char,char,text,bigint),
  factory.model_rotator_finish_v1(char,char,jsonb,jsonb,integer,bigint),
  factory.model_rotator_quarantine_v1(char,char,jsonb)
TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.model_rotator_reconcile_v1(char,text) TO factory_migrator;
