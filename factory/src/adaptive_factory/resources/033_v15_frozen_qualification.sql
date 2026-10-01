-- Bind persisted qualification to the immutable twelve-case F24 suite.
CREATE FUNCTION factory.v15_valid_frozen_qualification(p_value jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE v_case jsonb; v_index integer:=0; v_expected_domain text;
BEGIN
  IF NOT factory.execution_object_has_exact_keys(p_value,ARRAY['status','suite_digest','cases'])
    OR p_value->>'suite_digest'<>'d57c08cecf33c021e15911cfd3a6b4c96ea198c4b3e34f8b76048399daf51c9a'
    OR p_value->>'status' NOT IN ('not_evaluated','supported','failed')
    OR jsonb_typeof(p_value->'cases') IS DISTINCT FROM 'array'
    OR jsonb_array_length(p_value->'cases')<>12
  THEN RETURN false; END IF;
  FOR v_case IN SELECT value FROM jsonb_array_elements(p_value->'cases') LOOP
    v_index:=v_index+1;
    v_expected_domain:=CASE WHEN v_index<=4 THEN 'pump_selector'
      WHEN v_index<=8 THEN 'factory' ELSE 'cross_component' END;
    IF NOT factory.execution_object_has_exact_keys(v_case,ARRAY['case_id','domain','status'])
      OR v_case->>'case_id'<>format('F24-%s',lpad(v_index::text,3,'0'))
      OR v_case->>'domain'<>v_expected_domain
      OR v_case->>'status' NOT IN ('pass','fail','not_evaluated')
    THEN RETURN false; END IF;
  END LOOP;
  IF p_value->>'status'='supported'
    AND EXISTS (SELECT 1 FROM jsonb_array_elements(p_value->'cases') item WHERE item->>'status'<>'pass')
  THEN RETURN false; END IF;
  IF p_value->>'status'='failed'
    AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements(p_value->'cases') item WHERE item->>'status'='fail')
  THEN RETURN false; END IF;
  IF p_value->>'status'='not_evaluated'
    AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements(p_value->'cases') item WHERE item->>'status'='not_evaluated')
  THEN RETURN false; END IF;
  RETURN true;
END $$;

ALTER TABLE factory.v15_runtime_evaluations ADD CONSTRAINT v15_runtime_frozen_qualification
  CHECK (factory.v15_valid_frozen_qualification(body->'qualification'));

REVOKE ALL ON FUNCTION factory.v15_valid_frozen_qualification(jsonb)
  FROM PUBLIC,factory_runtime,factory_migrator;
