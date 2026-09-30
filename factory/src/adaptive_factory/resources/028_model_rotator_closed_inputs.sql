-- Additive hardening for migration 027.  The original bytes stay immutable.
-- Runtime callers reach closed wrappers; the renamed 027 bodies are private implementation details.
ALTER FUNCTION factory.model_rotator_claim_v1(jsonb,text,char,char,integer,char,bigint)
  RENAME TO model_rotator_claim_v1_027;
ALTER FUNCTION factory.model_rotator_reserve_v1(char,char,text,bigint)
  RENAME TO model_rotator_reserve_v1_027;
ALTER FUNCTION factory.model_rotator_finish_v1(char,char,jsonb,jsonb,integer,bigint)
  RENAME TO model_rotator_finish_v1_027;
ALTER FUNCTION factory.model_rotator_quarantine_v1(char,char,jsonb)
  RENAME TO model_rotator_quarantine_v1_027;
ALTER FUNCTION factory.model_rotator_reconcile_v1(char,text)
  RENAME TO model_rotator_reconcile_v1_027;

REVOKE ALL ON FUNCTION
  factory.model_rotator_claim_v1_027(jsonb,text,char,char,integer,char,bigint),
  factory.model_rotator_reserve_v1_027(char,char,text,bigint),
  factory.model_rotator_finish_v1_027(char,char,jsonb,jsonb,integer,bigint),
  factory.model_rotator_quarantine_v1_027(char,char,jsonb),
  factory.model_rotator_reconcile_v1_027(char,text)
FROM PUBLIC, factory_runtime, factory_migrator;

CREATE FUNCTION factory.model_rotator_claim_v1(
  p_binding jsonb,p_wire text,p_binding_digest char(64),p_registry char(64),
  p_cursor integer,p_requested char(64),p_now bigint
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  IF p_binding IS NULL OR p_wire IS NULL OR p_binding_digest IS NULL OR p_registry IS NULL
    OR p_cursor IS NULL OR p_requested IS NULL OR p_now IS NULL
    OR octet_length(p_wire)>16384 OR jsonb_typeof(p_binding)<>'object'
    OR p_binding_digest!~'^[0-9a-f]{64}$' OR p_registry!~'^[0-9a-f]{64}$'
    OR p_requested!~'^[0-9a-f]{64}$' OR p_cursor<0 OR p_now<0
  THEN RETURN jsonb_build_object('error','binding_digest_mismatch'); END IF;
  IF p_binding-ARRAY['schema_version','tenant_id','repository_id','task_id','run_id','attempt_id','fence','budget_reservation_id','budget_digest','registry_digest','operation_id','requested_provider_id','requested_model_id','remaining_token_units','remaining_request_units']<>'{}'::jsonb
    OR (SELECT count(*) FROM jsonb_object_keys(p_binding))<>15
    OR (p_binding->>'task_id')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    OR (p_binding->>'run_id')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    OR (p_binding->>'attempt_id')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    OR (p_binding->>'budget_reservation_id')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    OR (p_binding->>'budget_digest')!~'^[0-9a-f]{64}$'
    OR (p_binding->>'registry_digest')!~'^[0-9a-f]{64}$'
    OR (p_binding->>'fence')!~'^[1-9][0-9]{0,18}$'
    OR (p_binding->>'remaining_token_units')!~'^(0|[1-9][0-9]{0,18})$'
    OR (p_binding->>'remaining_request_units')!~'^(0|[1-9][0-9]{0,18})$'
    OR octet_length(p_binding->>'tenant_id') NOT BETWEEN 1 AND 512
    OR octet_length(p_binding->>'repository_id') NOT BETWEEN 1 AND 512
    OR octet_length(p_binding->>'operation_id') NOT BETWEEN 1 AND 512
    OR octet_length(p_binding->>'requested_provider_id') NOT BETWEEN 1 AND 128
    OR octet_length(p_binding->>'requested_model_id') NOT BETWEEN 1 AND 256
  THEN RETURN jsonb_build_object('error','binding_digest_mismatch'); END IF;
  RETURN factory.model_rotator_claim_v1_027(
    p_binding,p_wire,p_binding_digest,p_registry,p_cursor,p_requested,p_now
  );
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN
  RETURN jsonb_build_object('error','binding_digest_mismatch');
END $$;

CREATE FUNCTION factory.model_rotator_reserve_v1(
  p_binding char(64),p_claim char(64),p_mode text,p_units bigint
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  IF p_binding IS NULL OR p_claim IS NULL OR p_mode IS NULL OR p_units IS NULL
    OR p_binding!~'^[0-9a-f]{64}$' OR p_claim!~'^[0-9a-f]{64}$'
    OR p_mode NOT IN ('token','request') OR p_units<=0
  THEN RETURN false; END IF;
  RETURN factory.model_rotator_reserve_v1_027(p_binding,p_claim,p_mode,p_units);
END $$;

CREATE FUNCTION factory.model_rotator_finish_v1(
  p_binding char(64),p_claim char(64),p_evidence jsonb,p_cooldowns jsonb,
  p_cursor integer,p_version bigint
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  IF p_binding IS NULL OR p_claim IS NULL OR p_evidence IS NULL OR p_cooldowns IS NULL
    OR p_cursor IS NULL OR p_version IS NULL
    OR p_binding!~'^[0-9a-f]{64}$' OR p_claim!~'^[0-9a-f]{64}$'
    OR p_cursor<0 OR p_version<0 OR jsonb_typeof(p_evidence)<>'object'
    OR jsonb_typeof(p_cooldowns)<>'object'
  THEN RETURN false; END IF;
  IF p_evidence-ARRAY['evidence_digest','next_model_digest']<>'{}'::jsonb
    OR (SELECT count(*) FROM jsonb_object_keys(p_evidence))<>2
    OR (p_evidence->>'evidence_digest')!~'^[0-9a-f]{64}$'
    OR (p_evidence->>'next_model_digest')!~'^[0-9a-f]{64}$'
    OR octet_length(p_cooldowns::text)>16384
    OR (SELECT count(*) FROM jsonb_object_keys(p_cooldowns))>64
    OR EXISTS(SELECT 1 FROM jsonb_each_text(p_cooldowns) AS e(k,v)
      WHERE k!~'^[0-9a-f]{64}$' OR v!~'^(0|[1-9][0-9]{0,18})$')
  THEN RETURN false; END IF;
  RETURN factory.model_rotator_finish_v1_027(
    p_binding,p_claim,p_evidence,p_cooldowns,p_cursor,p_version
  );
END $$;

CREATE FUNCTION factory.model_rotator_quarantine_v1(
  p_binding char(64),p_claim char(64),p_evidence jsonb
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  IF p_binding IS NULL OR p_claim IS NULL OR p_evidence IS NULL
    OR p_binding!~'^[0-9a-f]{64}$' OR p_claim!~'^[0-9a-f]{64}$'
    OR jsonb_typeof(p_evidence)<>'object'
  THEN RETURN false; END IF;
  IF p_evidence-ARRAY['evidence_digest','outcome_digest']<>'{}'::jsonb
    OR (SELECT count(*) FROM jsonb_object_keys(p_evidence))<>2
    OR (p_evidence->>'evidence_digest')!~'^[0-9a-f]{64}$'
    OR (p_evidence->>'outcome_digest')!~'^[0-9a-f]{64}$'
  THEN RETURN false; END IF;
  RETURN factory.model_rotator_quarantine_v1_027(p_binding,p_claim,p_evidence);
END $$;

CREATE FUNCTION factory.model_rotator_reconcile_v1(
  p_binding char(64),p_outcome text
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  IF p_binding IS NULL OR p_outcome IS NULL OR p_binding!~'^[0-9a-f]{64}$'
    OR p_outcome NOT IN ('settle','release')
  THEN RETURN false; END IF;
  RETURN factory.model_rotator_reconcile_v1_027(p_binding,p_outcome);
END $$;

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
