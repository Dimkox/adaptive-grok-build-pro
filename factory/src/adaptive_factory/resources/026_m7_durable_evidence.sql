-- Additive M7.1; no live source bindings are seeded. Prior migrations are immutable.
-- One UTF8 encoder for M7 only; old contracts and migrations retain their bytes.
CREATE FUNCTION factory.m7_canonical_json(v jsonb, depth integer DEFAULT 0) RETURNS text
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,factory,pg_temp AS $$
DECLARE result text; s text;
BEGIN
  IF depth>16 THEN RAISE EXCEPTION 'm7 complexity limit'; END IF;
  CASE jsonb_typeof(v)
    WHEN 'object' THEN
      IF (SELECT count(*) FROM jsonb_object_keys(v))>128 THEN RAISE EXCEPTION 'm7 object limit'; END IF;
      SELECT '{'||COALESCE(string_agg(factory.m7_canonical_json(to_jsonb(key),depth+1)||':'||
        factory.m7_canonical_json(value,depth+1),',' ORDER BY key COLLATE "C"),'')||'}'
        INTO result FROM jsonb_each(v);
    WHEN 'array' THEN
      IF jsonb_array_length(v)>1024 THEN RAISE EXCEPTION 'm7 array limit'; END IF;
      SELECT '['||COALESCE(string_agg(factory.m7_canonical_json(value,depth+1),',' ORDER BY ordinal),'')||']'
        INTO result FROM jsonb_array_elements(v) WITH ORDINALITY a(value,ordinal);
    WHEN 'string' THEN
      s=v#>>'{}';
      IF s IS NOT NFC NORMALIZED OR octet_length(s)>4096 OR s ~ '[[:cntrl:]]'
        OR s ~ ('['||chr(127)||'-'||chr(159)||']') THEN RAISE EXCEPTION 'm7 text contract'; END IF;
      result=to_json(s)::text;
    WHEN 'number' THEN
      s=v#>>'{}';
      IF s !~ '^-?(0|[1-9][0-9]*)$' OR s::numeric NOT BETWEEN -9223372036854775807 AND 9223372036854775807
        THEN RAISE EXCEPTION 'm7 integer contract'; END IF;
      result=s;
    WHEN 'boolean' THEN result=v#>>'{}';
    WHEN 'null' THEN result='null';
    ELSE RAISE EXCEPTION 'm7 JSON contract';
  END CASE;
  RETURN result;
END $$;
CREATE FUNCTION factory.m7_hash(domain text, canonical text) RETURNS text
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,factory,pg_temp AS $$
BEGIN
  IF octet_length(canonical)>1048576 OR factory.m7_canonical_json(canonical::jsonb)<>canonical
    THEN RAISE EXCEPTION 'm7 canonical bytes mismatch'; END IF;
  RETURN encode(sha256(convert_to(domain,'UTF8')||decode('00','hex')||convert_to(canonical,'UTF8')),'hex');
END $$;
CREATE FUNCTION factory.m7_hash(domain text, body jsonb) RETURNS text
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,factory,pg_temp AS $$
  SELECT factory.m7_hash(domain,factory.m7_canonical_json(body));
$$;


CREATE FUNCTION factory.m7_wire_catalog() RETURNS jsonb
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,factory,pg_temp AS $schema$
SELECT $json${"M7LookupRequestV1":{"type":"object","properties":{"schema_version":{"const":1,"type":"integer"},"repository_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"task_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"run_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"generation":{"type":"integer","minimum":1,"maximum":9223372036854775807},"bundle_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"profile_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"pr_number":{"type":"integer","minimum":1,"maximum":9223372036854775807},"base_sha":{"type":"string","pattern":"^[0-9a-f]{40}$"},"head_sha":{"type":"string","pattern":"^[0-9a-f]{40}$"},"app_id":{"type":"integer","minimum":1,"maximum":9223372036854775807},"check_name":{"type":"string","minLength":1,"maxLength":256,"pattern":"^[^\\x00-\\x1f]+$"},"policy_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"holdout_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"}},"required":["schema_version","repository_id","task_id","run_id","generation","bundle_digest","profile_digest","pr_number","base_sha","head_sha","app_id","check_name","policy_digest","holdout_digest"],"additionalProperties":false},"M7BundleRegistrationV1":{"type":"object","properties":{"schema_version":{"const":1,"type":"integer"},"generation":{"type":"integer","minimum":1,"maximum":9223372036854775807},"bundle":{"type":"object","additionalProperties":false,"required":["schema_version","status","evidence","operator_handoff","bundle_digest"],"properties":{"schema_version":{"const":1},"status":{"const":"blocked_pending_durable_lookup"},"evidence":{"type":"object","additionalProperties":false,"required":["schema_version","m4","m5","m6"],"properties":{"schema_version":{"const":1},"m4":{"type":"object","additionalProperties":false,"required":["schema_version","task_id","run_id","owner","role","fence","intent_digest","lease_packet_digest"],"properties":{"schema_version":{"const":1},"task_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"run_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"owner":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"role":{"const":"writer"},"fence":{"type":"integer","minimum":1,"maximum":9223372036854775807},"intent_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"lease_packet_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"}}},"m5":{"type":"object","additionalProperties":false,"required":["schema_version","task_id","run_id","owner","role","fence","repository_id","legacy_intent_digest","task_packet_digest","run_manifest_digest","workspace_snapshot_digest","workspace_result_digest","authority_exact_head_sha","snapshot_input_head_sha","snapshot_result_head_sha","result_exact_head_sha"],"properties":{"schema_version":{"const":1},"task_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"run_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"owner":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"role":{"const":"writer"},"fence":{"type":"integer","minimum":1,"maximum":9223372036854775807},"repository_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"legacy_intent_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"task_packet_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"run_manifest_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"workspace_snapshot_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"workspace_result_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"authority_exact_head_sha":{"type":"string","pattern":"^[0-9a-f]{40}$"},"snapshot_input_head_sha":{"type":"string","pattern":"^[0-9a-f]{40}$"},"snapshot_result_head_sha":{"type":"string","pattern":"^[0-9a-f]{40}$"},"result_exact_head_sha":{"type":"string","pattern":"^[0-9a-f]{40}$"}}},"m6":{"type":"object","additionalProperties":false,"required":["schema_version","task_id","run_id","owner","role","fence","repository_id","legacy_intent_digest","task_packet_digest","run_manifest_digest","workspace_snapshot_digest","workspace_result_digest","binding_input_head_sha","binding_exact_head_sha","subject_exact_head_sha","envelope_digest","binding_digest","validation_inputs_digest","subject_digest","evidence_set_digest","verdict_digest","verdict"],"properties":{"schema_version":{"const":1},"task_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"run_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"owner":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"role":{"const":"writer"},"fence":{"type":"integer","minimum":1,"maximum":9223372036854775807},"repository_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"legacy_intent_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"task_packet_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"run_manifest_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"workspace_snapshot_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"workspace_result_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"binding_input_head_sha":{"type":"string","pattern":"^[0-9a-f]{40}$"},"binding_exact_head_sha":{"type":"string","pattern":"^[0-9a-f]{40}$"},"subject_exact_head_sha":{"type":"string","pattern":"^[0-9a-f]{40}$"},"envelope_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"binding_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"validation_inputs_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"subject_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"evidence_set_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"verdict_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"verdict":{"type":"object","additionalProperties":false,"required":["schema_version","subject_digest","decision","decision_source","finding_identity_digests","duplicate_identity_digests","correlated_requirement_keys","contradicted_requirement_keys","unsupported_pass_requirement_keys","residual_risk"],"properties":{"schema_version":{"const":1},"subject_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"decision":{"const":"pass"},"decision_source":{"const":"deterministic_adjudicator"},"finding_identity_digests":{"type":"array","maxItems":0,"items":{"type":"string","pattern":"^[0-9a-f]{64}$"}},"duplicate_identity_digests":{"type":"array","maxItems":0,"items":{"type":"string","pattern":"^[0-9a-f]{64}$"}},"correlated_requirement_keys":{"type":"array","maxItems":0,"items":{"type":"string"}},"contradicted_requirement_keys":{"type":"array","maxItems":0,"items":{"type":"string"}},"unsupported_pass_requirement_keys":{"type":"array","maxItems":0,"items":{"type":"string"}},"residual_risk":{"const":"none"}}}}}}},"operator_handoff":{"type":"object","additionalProperties":false,"required":["schema_version","subject_digest","external_capability","recommended_action","instructions"],"properties":{"schema_version":{"const":1},"subject_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"external_capability":{"const":"absent"},"recommended_action":{"const":"human_review"},"instructions":{"type":"array","minItems":4,"maxItems":4,"uniqueItems":true,"prefixItems":[{"const":"human_decides_merge"},{"const":"inspect_local_bundle"},{"const":"obtain_human_review"},{"const":"verify_exact_sha_trust_ci"}],"items":false}}},"bundle_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"}}},"profile":{"oneOf":[{"type":"object","properties":{"schema_version":{"oneOf":[{"type":"integer","minimum":1,"maximum":9223372036854775807},{"type":"null"}]},"repository_id":{"oneOf":[{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},{"type":"null"}]},"task_class":{"oneOf":[{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},{"type":"null"}]},"m7_change_class":{"oneOf":[{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},{"type":"null"}]},"m7_cohort_key_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"provider_mapping_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"agent_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"validator_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"provider_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"model_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"prompt_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"policy_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"runner_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"holdout_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"authority_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"authority_ceiling":{"oneOf":[{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},{"type":"null"}]},"expires_at":{"oneOf":[{"type":"string","format":"date-time","maxLength":32,"pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|[+-](?:[01]\\d|2[0-3]):[0-5]\\d)$"},{"type":"null"}]}},"required":["schema_version","repository_id","task_class","m7_change_class","m7_cohort_key_digest","provider_mapping_digest","agent_digest","validator_digest","provider_digest","model_digest","prompt_digest","policy_digest","runner_digest","holdout_digest","authority_digest","authority_ceiling","expires_at"],"additionalProperties":false},{"type":"null"}]}},"required":["schema_version","generation","bundle","profile"],"additionalProperties":false},"M7OutcomeObservationV1":{"type":"object","properties":{"schema_version":{"const":1,"type":"integer"},"repository_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"bundle_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"result_head_sha":{"type":"string","pattern":"^[0-9a-f]{40}$"},"provenance":{"type":"object","properties":{"schema_version":{"const":1,"type":"integer"},"source_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"source_kind":{"enum":["human_outcome","signed_ci","github_current","deployed_epoch"]},"adapter_version":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"source_event_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"source_revision":{"type":"integer","minimum":1,"maximum":9223372036854775807},"predecessor_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"source_issued_at":{"type":"string","format":"date-time","maxLength":32,"pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|[+-](?:[01]\\d|2[0-3]):[0-5]\\d)$"},"observed_at":{"type":"string","format":"date-time","maxLength":32,"pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|[+-](?:[01]\\d|2[0-3]):[0-5]\\d)$"},"valid_until":{"type":"string","format":"date-time","maxLength":32,"pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|[+-](?:[01]\\d|2[0-3]):[0-5]\\d)$"},"trust_config_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"evidence_ref":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"verifier_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"}},"required":["schema_version","source_id","source_kind","adapter_version","source_event_id","source_revision","predecessor_digest","source_issued_at","observed_at","valid_until","trust_config_digest","evidence_ref","verifier_id"],"additionalProperties":false},"decision":{"enum":["accepted","rejected","withdrawn"]},"outcome":{"oneOf":[{"type":"object","additionalProperties":false,"required":["schema_version","outcome_id","bundle_digest","cohort_key_digest","human_evidence_digest","human_decision","first_pass_accepted","rework_required","validator_false_negative","validator_false_positive_or_disagreement","repair_cycles","cost_within_budget","latency_within_slo","deadline_met","token_budget_met","human_review_seconds","critical_high_miss_count","security_miss_count","unauthorized_effect_count","rollback_count","escaped_defect_count","duplicate_dispatch_count","unaccounted_call_count","injection_attempt_count","injection_contained_count"],"properties":{"schema_version":{"const":1},"outcome_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"bundle_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"cohort_key_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"human_evidence_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"human_decision":{"enum":["merged_accepted","not_merged"]},"first_pass_accepted":{"type":"boolean"},"rework_required":{"type":"boolean"},"validator_false_negative":{"type":"boolean"},"validator_false_positive_or_disagreement":{"type":"boolean"},"repair_cycles":{"type":"integer","minimum":0,"maximum":3},"cost_within_budget":{"type":"boolean"},"latency_within_slo":{"type":"boolean"},"deadline_met":{"type":"boolean"},"token_budget_met":{"type":"boolean"},"human_review_seconds":{"type":"integer","minimum":1,"maximum":604800},"critical_high_miss_count":{"type":"integer","minimum":0,"maximum":1000000},"security_miss_count":{"type":"integer","minimum":0,"maximum":1000000},"unauthorized_effect_count":{"type":"integer","minimum":0,"maximum":1000000},"rollback_count":{"type":"integer","minimum":0,"maximum":1000000},"escaped_defect_count":{"type":"integer","minimum":0,"maximum":1000000},"duplicate_dispatch_count":{"type":"integer","minimum":0,"maximum":1000000},"unaccounted_call_count":{"type":"integer","minimum":0,"maximum":1000000},"injection_attempt_count":{"type":"integer","minimum":0,"maximum":1000000},"injection_contained_count":{"type":"integer","minimum":0,"maximum":1000000}},"allOf":[{"if":{"properties":{"first_pass_accepted":{"const":true}}},"then":{"properties":{"human_decision":{"const":"merged_accepted"},"rework_required":{"const":false}}}}]},{"type":"null"}]},"profile":{"oneOf":[{"type":"object","properties":{"schema_version":{"oneOf":[{"type":"integer","minimum":1,"maximum":9223372036854775807},{"type":"null"}]},"repository_id":{"oneOf":[{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},{"type":"null"}]},"task_class":{"oneOf":[{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},{"type":"null"}]},"m7_change_class":{"oneOf":[{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},{"type":"null"}]},"m7_cohort_key_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"provider_mapping_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"agent_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"validator_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"provider_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"model_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"prompt_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"policy_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"runner_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"holdout_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"authority_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"authority_ceiling":{"oneOf":[{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},{"type":"null"}]},"expires_at":{"oneOf":[{"type":"string","format":"date-time","maxLength":32,"pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|[+-](?:[01]\\d|2[0-3]):[0-5]\\d)$"},{"type":"null"}]}},"required":["schema_version","repository_id","task_class","m7_change_class","m7_cohort_key_digest","provider_mapping_digest","agent_digest","validator_digest","provider_digest","model_digest","prompt_digest","policy_digest","runner_digest","holdout_digest","authority_digest","authority_ceiling","expires_at"],"additionalProperties":false},{"type":"null"}]},"measurements":{"type":"object","properties":{"schema_version":{"const":1,"type":"integer"},"cost_usd_micros":{"oneOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]},"latency_ms":{"oneOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]},"repair_count":{"oneOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]},"rollback_count":{"oneOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]},"regression_count":{"oneOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]},"intervention_count":{"oneOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]},"intervention_coverage":{"enum":["unknown","partial","complete"]},"intervention_source_refs":{"type":"array","items":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"maxItems":64,"uniqueItems":true},"session_started_at":{"oneOf":[{"type":"string","format":"date-time","maxLength":32,"pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|[+-](?:[01]\\d|2[0-3]):[0-5]\\d)$"},{"type":"null"}]},"session_ended_at":{"oneOf":[{"type":"string","format":"date-time","maxLength":32,"pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|[+-](?:[01]\\d|2[0-3]):[0-5]\\d)$"},{"type":"null"}]}},"required":["schema_version","cost_usd_micros","latency_ms","repair_count","rollback_count","regression_count","intervention_count","intervention_coverage","intervention_source_refs","session_started_at","session_ended_at"],"additionalProperties":false}},"required":["schema_version","repository_id","bundle_digest","result_head_sha","provenance","decision","outcome","profile","measurements"],"additionalProperties":false},"M7CheckObservationV1":{"type":"object","properties":{"schema_version":{"const":1,"type":"integer"},"repository_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"pr_number":{"type":"integer","minimum":1,"maximum":9223372036854775807},"base_sha":{"type":"string","pattern":"^[0-9a-f]{40}$"},"head_sha":{"type":"string","pattern":"^[0-9a-f]{40}$"},"policy_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"holdout_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"external_job_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"attestation_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"signer_key_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"result":{"enum":["passed","failed","revoked"]},"provenance":{"type":"object","properties":{"schema_version":{"const":1,"type":"integer"},"source_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"source_kind":{"enum":["human_outcome","signed_ci","github_current","deployed_epoch"]},"adapter_version":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"source_event_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"source_revision":{"type":"integer","minimum":1,"maximum":9223372036854775807},"predecessor_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"source_issued_at":{"type":"string","format":"date-time","maxLength":32,"pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|[+-](?:[01]\\d|2[0-3]):[0-5]\\d)$"},"observed_at":{"type":"string","format":"date-time","maxLength":32,"pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|[+-](?:[01]\\d|2[0-3]):[0-5]\\d)$"},"valid_until":{"type":"string","format":"date-time","maxLength":32,"pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|[+-](?:[01]\\d|2[0-3]):[0-5]\\d)$"},"trust_config_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"evidence_ref":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"verifier_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"}},"required":["schema_version","source_id","source_kind","adapter_version","source_event_id","source_revision","predecessor_digest","source_issued_at","observed_at","valid_until","trust_config_digest","evidence_ref","verifier_id"],"additionalProperties":false}},"required":["schema_version","repository_id","pr_number","base_sha","head_sha","policy_digest","holdout_digest","external_job_id","attestation_digest","signer_key_id","result","provenance"],"additionalProperties":false},"M7GitHubContextV1":{"type":"object","properties":{"schema_version":{"const":1,"type":"integer"},"repository_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"pr_number":{"type":"integer","minimum":1,"maximum":9223372036854775807},"base_sha":{"type":"string","pattern":"^[0-9a-f]{40}$"},"head_sha":{"type":"string","pattern":"^[0-9a-f]{40}$"},"app_id":{"type":"integer","minimum":1,"maximum":9223372036854775807},"check_name":{"type":"string","minLength":1,"maxLength":256,"pattern":"^[^\\x00-\\x1f]+$"},"external_job_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"check_id":{"type":"integer","minimum":1,"maximum":9223372036854775807},"check_state":{"enum":["queued","in_progress","completed"]},"check_conclusion":{"enum":["unknown","success","failure","cancelled","action_required","timed_out","neutral","skipped"]},"revoked":{"type":"boolean"},"provenance":{"type":"object","properties":{"schema_version":{"const":1,"type":"integer"},"source_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"source_kind":{"enum":["human_outcome","signed_ci","github_current","deployed_epoch"]},"adapter_version":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"source_event_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"source_revision":{"type":"integer","minimum":1,"maximum":9223372036854775807},"predecessor_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"source_issued_at":{"type":"string","format":"date-time","maxLength":32,"pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|[+-](?:[01]\\d|2[0-3]):[0-5]\\d)$"},"observed_at":{"type":"string","format":"date-time","maxLength":32,"pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|[+-](?:[01]\\d|2[0-3]):[0-5]\\d)$"},"valid_until":{"type":"string","format":"date-time","maxLength":32,"pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|[+-](?:[01]\\d|2[0-3]):[0-5]\\d)$"},"trust_config_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"evidence_ref":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"verifier_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"}},"required":["schema_version","source_id","source_kind","adapter_version","source_event_id","source_revision","predecessor_digest","source_issued_at","observed_at","valid_until","trust_config_digest","evidence_ref","verifier_id"],"additionalProperties":false}},"required":["schema_version","repository_id","pr_number","base_sha","head_sha","app_id","check_name","external_job_id","check_id","check_state","check_conclusion","revoked","provenance"],"additionalProperties":false},"M7EpochContextV1":{"type":"object","properties":{"schema_version":{"const":1,"type":"integer"},"repository_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"policy_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"holdout_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"app_id":{"type":"integer","minimum":1,"maximum":9223372036854775807},"check_name":{"type":"string","minLength":1,"maxLength":256,"pattern":"^[^\\x00-\\x1f]+$"},"revoked":{"type":"boolean"},"provenance":{"type":"object","properties":{"schema_version":{"const":1,"type":"integer"},"source_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"source_kind":{"enum":["human_outcome","signed_ci","github_current","deployed_epoch"]},"adapter_version":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"source_event_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"source_revision":{"type":"integer","minimum":1,"maximum":9223372036854775807},"predecessor_digest":{"oneOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"source_issued_at":{"type":"string","format":"date-time","maxLength":32,"pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|[+-](?:[01]\\d|2[0-3]):[0-5]\\d)$"},"observed_at":{"type":"string","format":"date-time","maxLength":32,"pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|[+-](?:[01]\\d|2[0-3]):[0-5]\\d)$"},"valid_until":{"type":"string","format":"date-time","maxLength":32,"pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,6})?(?:Z|[+-](?:[01]\\d|2[0-3]):[0-5]\\d)$"},"trust_config_digest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"evidence_ref":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"},"verifier_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"}},"required":["schema_version","source_id","source_kind","adapter_version","source_event_id","source_revision","predecessor_digest","source_issued_at","observed_at","valid_until","trust_config_digest","evidence_ref","verifier_id"],"additionalProperties":false}},"required":["schema_version","repository_id","policy_digest","holdout_digest","app_id","check_name","revoked","provenance"],"additionalProperties":false}}$json$::jsonb
$schema$;

CREATE FUNCTION factory.m7_schema_valid(v jsonb,s jsonb,depth integer DEFAULT 0) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,factory,pg_temp AS $$
DECLARE k text; child jsonb; n integer; stamp timestamptz; normalized text;
BEGIN
  IF depth>24 OR v IS NULL OR s IS NULL THEN RETURN false; END IF;
  IF s ? 'oneOf' THEN
    SELECT count(*) INTO n FROM jsonb_array_elements(s->'oneOf') q
      WHERE factory.m7_schema_valid(v,q,depth+1);
    RETURN n=1;
  END IF;
  IF s ? 'const' AND v::text IS DISTINCT FROM (s->'const')::text THEN RETURN false; END IF;
  IF s ? 'enum' AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(s->'enum') q WHERE q=v) THEN RETURN false; END IF;
  IF s ? 'type' AND NOT (
    jsonb_typeof(v)=s->>'type' OR s->>'type'='integer' AND jsonb_typeof(v)='number' AND v::text ~ '^[0-9]+$'
  ) THEN RETURN false; END IF;
  IF jsonb_typeof(v)='object' THEN
    IF s->>'additionalProperties'='false' AND EXISTS(
      SELECT 1 FROM jsonb_object_keys(v) x WHERE NOT (s->'properties' ? x)
    ) THEN RETURN false; END IF;
    IF EXISTS(SELECT 1 FROM jsonb_array_elements_text(COALESCE(s->'required','[]')) x WHERE NOT (v ? x)) THEN RETURN false; END IF;
    FOR k,child IN SELECT * FROM jsonb_each(v) LOOP
      IF NOT factory.m7_schema_valid(child,s->'properties'->k,depth+1) THEN RETURN false; END IF;
    END LOOP;
  ELSIF jsonb_typeof(v)='array' THEN
    IF jsonb_array_length(v)>COALESCE((s->>'maxItems')::integer,1024)
      OR jsonb_array_length(v)<COALESCE((s->>'minItems')::integer,0) THEN RETURN false; END IF;
    IF s->>'uniqueItems'='true' AND (SELECT count(*)<>count(DISTINCT q) FROM jsonb_array_elements(v) q) THEN RETURN false; END IF;
    FOR child IN SELECT * FROM jsonb_array_elements(v) LOOP
      IF NOT factory.m7_schema_valid(child,s->'items',depth+1) THEN RETURN false; END IF;
    END LOOP;
  ELSIF jsonb_typeof(v)='number' THEN
    IF v::numeric<COALESCE((s->>'minimum')::numeric,0)
      OR v::numeric>COALESCE((s->>'maximum')::numeric,9223372036854775807) THEN RETURN false; END IF;
  ELSIF jsonb_typeof(v)='string' THEN
    k=v#>>'{}';
    IF k IS NOT NFC NORMALIZED OR k ~ ('['||chr(127)||'-'||chr(159)||']') THEN RETURN false; END IF;
    IF octet_length(k)<COALESCE((s->>'minLength')::integer,0)
      OR octet_length(k)>COALESCE((s->>'maxLength')::integer,4096)
      OR k ~ '[[:cntrl:]]' OR s ? 'pattern' AND k !~ (s->>'pattern') THEN RETURN false; END IF;
    IF s->>'format'='date-time' THEN
      stamp=k::timestamptz;
      normalized=to_char(stamp AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"');
      normalized=replace(normalized,'.000000Z','Z');
      IF k<>normalized THEN RETURN false; END IF;
    END IF;
  END IF;
  RETURN true;
EXCEPTION WHEN OTHERS THEN RETURN false;
END $$;

CREATE FUNCTION factory.m7_sorted_references(v jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,factory,pg_temp AS $$
  SELECT CASE WHEN jsonb_typeof(v)<>'array' OR jsonb_array_length(v)>64 THEN false ELSE
    NOT EXISTS(SELECT 1 FROM jsonb_array_elements(v) item WHERE jsonb_typeof(item)<>'string'
      OR item#>>'{}' !~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$') AND
    (SELECT array_agg(item#>>'{}' ORDER BY position) FROM jsonb_array_elements(v) WITH ORDINALITY a(item,position))
    IS NOT DISTINCT FROM (SELECT array_agg(item ORDER BY item COLLATE "C")
      FROM (SELECT DISTINCT item#>>'{}' AS item FROM jsonb_array_elements(v) item) unique_items) END;
$$;

CREATE FUNCTION factory.m7_wire(kind text,canonical text) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,factory,pg_temp AS $$
DECLARE body jsonb;
BEGIN
  IF canonical IS NULL OR octet_length(canonical)>1048576 THEN RAISE EXCEPTION 'm7 wire limit'; END IF;
  body=canonical::jsonb;
  IF factory.m7_canonical_json(body)<>canonical
    OR NOT factory.m7_schema_valid(body,factory.m7_wire_catalog()->kind) THEN
    RAISE EXCEPTION 'm7 invalid canonical contract';
  END IF;
  IF body#>'{measurements,intervention_source_refs}' IS NOT NULL AND NOT
    factory.m7_sorted_references(body#>'{measurements,intervention_source_refs}')
    THEN RAISE EXCEPTION 'm7 references not sorted unique'; END IF;
  RETURN body;
END $$;

DO $$ DECLARE role_name text;
BEGIN
  FOREACH role_name IN ARRAY ARRAY['factory_m7_registry','factory_m7_outcome','factory_m7_check_context','factory_m7_reader'] LOOP
    IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_roles WHERE rolname=role_name) THEN
      EXECUTE format('CREATE ROLE %I NOLOGIN NOINHERIT',role_name);
    END IF;
    IF EXISTS(SELECT 1 FROM pg_catalog.pg_roles WHERE rolname=role_name AND
      (rolcanlogin OR rolinherit OR rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls
       OR COALESCE(array_length(rolconfig,1),0)>0))
      OR EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members m JOIN pg_catalog.pg_roles r ON r.oid=m.member WHERE r.rolname=role_name)
    THEN RAISE EXCEPTION 'm7 unsafe capability role'; END IF;
    EXECUTE format('GRANT USAGE ON SCHEMA factory TO %I',role_name);
  END LOOP;
END $$;

CREATE TABLE factory.m7_source_bindings (
  principal_oid oid NOT NULL, principal_name name NOT NULL,
  repository_id text NOT NULL CHECK(octet_length(repository_id) BETWEEN 1 AND 128),
  source_id text NOT NULL CHECK(octet_length(source_id) BETWEEN 1 AND 128),
  capability_kind text NOT NULL CHECK(capability_kind IN ('registry','outcome','check_context','reader')),
  source_kind text NOT NULL CHECK(source_kind IN ('registry','human_outcome','signed_ci','github_current','deployed_epoch')),
  mode text NOT NULL CHECK(mode IN ('synthetic','imported','authenticated')),
  trust_config_digest text NOT NULL CHECK(trust_config_digest ~ '^[0-9a-f]{64}$'),
  binding_digest text NOT NULL CHECK(binding_digest ~ '^[0-9a-f]{64}$'),
  enabled boolean NOT NULL, valid_until timestamptz NOT NULL,
  max_age_seconds integer NOT NULL CHECK(max_age_seconds BETWEEN 1 AND 86400),
  canonical_body text NOT NULL CHECK(octet_length(canonical_body)<=4096),
  PRIMARY KEY(principal_oid,repository_id,source_id,capability_kind),
  UNIQUE(principal_name,repository_id,source_id,capability_kind)
);
CREATE INDEX m7_binding_source_scope ON factory.m7_source_bindings(repository_id,source_id,capability_kind,source_kind);

CREATE TABLE factory.m7_bundles (
  bundle_digest text PRIMARY KEY CHECK(bundle_digest ~ '^[0-9a-f]{64}$'),
  registration_digest text NOT NULL CHECK(registration_digest ~ '^[0-9a-f]{64}$'),
  repository_id text NOT NULL, task_id uuid NOT NULL REFERENCES factory.tasks(task_id),
  run_id uuid NOT NULL, intent_digest char(64) NOT NULL REFERENCES factory.accepted_intents(intent_digest),
  generation integer NOT NULL CHECK(generation>0),
  workspace_result_digest char(64) NOT NULL REFERENCES factory.workspace_results(workspace_result_digest),
  subject_digest char(64) NOT NULL REFERENCES factory.semantic_subjects(subject_digest),
  verdict_digest char(64) NOT NULL REFERENCES factory.semantic_verdicts(verdict_digest),
  profile_digest text NULL CHECK(profile_digest IS NULL OR profile_digest ~ '^[0-9a-f]{64}$'),
  source_id text NOT NULL, binding_digest text NOT NULL, source_mode text NOT NULL,
  body jsonb NOT NULL,
  canonical_body text NOT NULL CHECK(octet_length(canonical_body)<=1048576),
  selector_digest text NOT NULL CHECK(selector_digest ~ '^[0-9a-f]{64}$'),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  FOREIGN KEY(run_id,task_id) REFERENCES factory.runs(run_id,task_id)
);
CREATE INDEX m7_bundle_subject ON factory.m7_bundles(repository_id,task_id,run_id,profile_digest,bundle_digest);

CREATE TABLE factory.m7_outcomes (
  observation_digest text PRIMARY KEY CHECK(observation_digest ~ '^[0-9a-f]{64}$'),
  repository_id text NOT NULL, bundle_digest text NOT NULL REFERENCES factory.m7_bundles(bundle_digest),
  source_id text NOT NULL, source_event_id text NOT NULL, stream_key text NOT NULL,
  source_revision bigint NOT NULL CHECK(source_revision>0), predecessor_digest text,
  binding_digest text NOT NULL, source_mode text NOT NULL,
  observed_at timestamptz NOT NULL, valid_until timestamptz NOT NULL,
  body jsonb NOT NULL,
  canonical_body text NOT NULL CHECK(octet_length(canonical_body)<=1048576),
  selector_digest text NOT NULL CHECK(selector_digest ~ '^[0-9a-f]{64}$'),
  received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(repository_id,source_id,source_event_id), UNIQUE(repository_id,source_id,stream_key,source_revision)
);
CREATE INDEX m7_outcome_latest ON factory.m7_outcomes(repository_id,bundle_digest,source_id,source_revision DESC);

CREATE TABLE factory.m7_checks (
  observation_digest text PRIMARY KEY CHECK(observation_digest ~ '^[0-9a-f]{64}$'),
  repository_id text NOT NULL, pr_number bigint NOT NULL CHECK(pr_number>0),
  base_sha text NOT NULL, head_sha text NOT NULL, policy_digest text NOT NULL,
  source_id text NOT NULL, source_event_id text NOT NULL, stream_key text NOT NULL,
  source_revision bigint NOT NULL CHECK(source_revision>0), predecessor_digest text,
  binding_digest text NOT NULL, source_mode text NOT NULL,
  observed_at timestamptz NOT NULL, valid_until timestamptz NOT NULL,
  body jsonb NOT NULL,
  canonical_body text NOT NULL CHECK(octet_length(canonical_body)<=1048576),
  selector_digest text NOT NULL CHECK(selector_digest ~ '^[0-9a-f]{64}$'),
  received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(repository_id,source_id,source_event_id), UNIQUE(repository_id,source_id,stream_key,source_revision)
);
CREATE INDEX m7_check_latest ON factory.m7_checks(repository_id,pr_number,source_id,source_revision DESC);
CREATE INDEX m7_check_subject ON factory.m7_checks(repository_id,pr_number,base_sha,head_sha,policy_digest,source_id,source_revision DESC);

CREATE TABLE factory.m7_contexts (
  observation_digest text PRIMARY KEY CHECK(observation_digest ~ '^[0-9a-f]{64}$'),
  repository_id text NOT NULL, pr_number bigint NOT NULL CHECK(pr_number>=0), source_kind text NOT NULL,
  source_id text NOT NULL, source_event_id text NOT NULL, stream_key text NOT NULL,
  source_revision bigint NOT NULL CHECK(source_revision>0), predecessor_digest text,
  binding_digest text NOT NULL, source_mode text NOT NULL,
  observed_at timestamptz NOT NULL, valid_until timestamptz NOT NULL,
  body jsonb NOT NULL,
  canonical_body text NOT NULL CHECK(octet_length(canonical_body)<=1048576),
  selector_digest text NOT NULL CHECK(selector_digest ~ '^[0-9a-f]{64}$'),
  received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(repository_id,source_id,source_event_id), UNIQUE(repository_id,source_id,stream_key,source_revision)
);
CREATE INDEX m7_context_latest ON factory.m7_contexts(repository_id,pr_number,source_kind,source_id,source_revision DESC);

CREATE TABLE factory.m7_command_results (
  source_id text NOT NULL, operation text NOT NULL, idempotency_key text NOT NULL CHECK(octet_length(idempotency_key) BETWEEN 1 AND 128),
  repository_id text NOT NULL, request_digest text NOT NULL,
  response_body jsonb NOT NULL,
  response_canonical text NOT NULL CHECK(octet_length(response_canonical)<=1048576),
  response_digest text NOT NULL CHECK(response_digest ~ '^[0-9a-f]{64}$'),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY(repository_id,source_id,operation,idempotency_key)
);


-- Indexed lookup selectors are derived from the stored canonical bytes. Corrupt
-- denormalized metadata cannot route around the latest row's integrity check.
DO $$ DECLARE relation text;
BEGIN
  FOREACH relation IN ARRAY ARRAY['m7_bundles','m7_outcomes','m7_checks','m7_contexts'] LOOP
    EXECUTE format('ALTER TABLE factory.%I
      ADD COLUMN lookup_repository text COLLATE "C" GENERATED ALWAYS AS
        (COALESCE(canonical_body::jsonb->>''repository_id'',canonical_body::jsonb#>>''{bundle,evidence,m5,repository_id}'')) STORED,
      ADD COLUMN lookup_source text COLLATE "C" GENERATED ALWAYS AS
        (canonical_body::jsonb#>>''{provenance,source_id}'') STORED,
      ADD COLUMN lookup_revision bigint GENERATED ALWAYS AS
        ((canonical_body::jsonb#>>''{provenance,source_revision}'')::bigint) STORED,
      ADD COLUMN lookup_pr bigint GENERATED ALWAYS AS
        (COALESCE((canonical_body::jsonb->>''pr_number'')::bigint,0)) STORED,
      ADD COLUMN lookup_kind text COLLATE "C" GENERATED ALWAYS AS
        (canonical_body::jsonb#>>''{provenance,source_kind}'') STORED,
      ADD COLUMN lookup_bundle text COLLATE "C" GENERATED ALWAYS AS
        (COALESCE(canonical_body::jsonb->>''bundle_digest'',canonical_body::jsonb#>>''{bundle,bundle_digest}'')) STORED,
      ADD COLUMN lookup_stream text COLLATE "C" GENERATED ALWAYS AS
        ((canonical_body::jsonb->>''repository_id'')||'':''||(canonical_body::jsonb#>>''{provenance,source_kind}'')||'':''||
         COALESCE(canonical_body::jsonb->>''bundle_digest'',canonical_body::jsonb->>''pr_number'',''0'')) STORED',relation);
  END LOOP;
END $$;
CREATE INDEX m7_outcome_canonical_latest ON factory.m7_outcomes(lookup_repository,lookup_bundle,lookup_source,lookup_revision DESC);
CREATE INDEX m7_check_canonical_latest ON factory.m7_checks(lookup_repository,lookup_pr,lookup_source,lookup_revision DESC);
CREATE INDEX m7_context_canonical_latest ON factory.m7_contexts(lookup_repository,lookup_pr,lookup_kind,lookup_source,lookup_revision DESC);
CREATE INDEX m7_bundle_canonical_subject ON factory.m7_bundles(lookup_repository,lookup_bundle);
CREATE INDEX m7_outcome_canonical_stream ON factory.m7_outcomes(lookup_repository,lookup_source,lookup_stream,lookup_revision DESC);
CREATE INDEX m7_check_canonical_stream ON factory.m7_checks(lookup_repository,lookup_source,lookup_stream,lookup_revision DESC);
CREATE INDEX m7_context_canonical_stream ON factory.m7_contexts(lookup_repository,lookup_source,lookup_stream,lookup_revision DESC);

-- Metadata is derived from the canonical body and immutable configured source.
CREATE FUNCTION factory.m7_metadata(b jsonb, binding text, mode text) RETURNS jsonb
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,factory,pg_temp AS $$
  SELECT CASE WHEN b ? 'bundle' THEN jsonb_build_object(
    'repository_id',b#>>'{bundle,evidence,m5,repository_id}','task_id',b#>>'{bundle,evidence,m4,task_id}',
    'run_id',b#>>'{bundle,evidence,m4,run_id}','generation',b->'generation',
    'bundle_digest',b#>>'{bundle,bundle_digest}','intent_digest',b#>>'{bundle,evidence,m4,intent_digest}',
    'workspace_result_digest',b#>>'{bundle,evidence,m5,workspace_result_digest}',
    'subject_digest',b#>>'{bundle,evidence,m6,subject_digest}','verdict_digest',b#>>'{bundle,evidence,m6,verdict_digest}',
    'profile_digest',CASE WHEN b->'profile'='null'::jsonb THEN NULL ELSE factory.m7_hash('adaptive-factory.m7-profile-metadata/v1',b->'profile') END,
    'binding_digest',binding,'source_mode',mode)
  ELSE jsonb_build_object('repository_id',b->>'repository_id','source_id',b#>>'{provenance,source_id}',
    'source_event_id',b#>>'{provenance,source_event_id}','source_revision',b#>'{provenance,source_revision}',
    'predecessor_digest',b#>'{provenance,predecessor_digest}','binding_digest',binding,'source_mode',mode,
    'source_kind',b#>>'{provenance,source_kind}',
    'stream_key',(b->>'repository_id')||':'||(b#>>'{provenance,source_kind}')||':'||COALESCE(b->>'bundle_digest',b->>'pr_number','0'),
    'bundle_digest',b->>'bundle_digest','pr_number',COALESCE((b->>'pr_number')::bigint,0),
    'base_sha',b->>'base_sha','head_sha',b->>'head_sha','policy_digest',b->>'policy_digest',
    'observed_at',b#>>'{provenance,observed_at}','valid_until',b#>>'{provenance,valid_until}') END;
$$;
CREATE FUNCTION factory.m7_binding_valid(b factory.m7_source_bindings) RETURNS boolean
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,factory,pg_temp AS $$
DECLARE wire jsonb; expected jsonb;
BEGIN
  wire=b.canonical_body::jsonb;
  expected=jsonb_build_object('principal_oid',b.principal_oid::bigint,'principal_name',b.principal_name,
    'repository_id',b.repository_id,'source_id',b.source_id,'capability_kind',b.capability_kind,
    'source_kind',b.source_kind,'mode',b.mode,'trust_config_digest',b.trust_config_digest,'enabled',b.enabled,
    'valid_until',wire->'valid_until','max_age_seconds',b.max_age_seconds);
  RETURN wire=expected AND (wire->>'valid_until')::timestamptz=b.valid_until AND
    factory.m7_hash('adaptive-factory.m7-source-binding/v1',b.canonical_body)=b.binding_digest;
EXCEPTION WHEN OTHERS THEN RETURN false;
END $$;
CREATE FUNCTION factory.m7_row_valid(kind text,r jsonb,w factory.m7_source_bindings) RETURNS boolean
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,factory,pg_temp AS $$
DECLARE body jsonb; expected jsonb; k text; v jsonb; contract text;
BEGIN
  body=(r->>'canonical_body')::jsonb;
  IF body IS DISTINCT FROM r->'body' OR r->>'binding_digest' IS DISTINCT FROM w.binding_digest
    OR r->>'source_mode' IS DISTINCT FROM w.mode OR r->>'repository_id' IS DISTINCT FROM w.repository_id
    OR r->>'source_id' IS DISTINCT FROM w.source_id THEN RETURN false; END IF;
  expected=factory.m7_metadata(body,w.binding_digest,w.mode);
  IF factory.m7_hash('adaptive-factory.m7-selector/v1',expected) IS DISTINCT FROM r->>'selector_digest'
    THEN RETURN false; END IF;
  FOR k,v IN SELECT * FROM jsonb_each(expected) LOOP
    IF r ? k THEN
      IF k IN ('observed_at','valid_until') THEN
        IF (r->>k)::timestamptz IS DISTINCT FROM (v#>>'{}')::timestamptz THEN RETURN false; END IF;
      ELSIF r->k IS DISTINCT FROM v THEN RETURN false; END IF;
    END IF;
  END LOOP;
  contract=CASE kind WHEN 'registry' THEN 'M7BundleRegistrationV1' WHEN 'human_outcome' THEN 'M7OutcomeObservationV1'
    WHEN 'signed_ci' THEN 'M7CheckObservationV1' WHEN 'github_current' THEN 'M7GitHubContextV1' ELSE 'M7EpochContextV1' END;
  PERFORM factory.m7_wire(contract,r->>'canonical_body');
  IF kind<>'registry' AND (body#>>'{provenance,source_kind}' IS DISTINCT FROM kind OR
    body#>>'{provenance,trust_config_digest}' IS DISTINCT FROM w.trust_config_digest) THEN RETURN false; END IF;
  RETURN true;
EXCEPTION WHEN OTHERS THEN RETURN false;
END $$;


CREATE FUNCTION factory.m7_principal(capability text) RETURNS oid
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,factory,pg_temp AS $$
DECLARE principal oid; role_oid oid; role_name text; memberships integer;
BEGIN
  IF capability NOT IN ('registry','outcome','check_context','reader') THEN RAISE EXCEPTION 'm7 capability denied'; END IF;
  role_name='factory_m7_'||capability;
  SELECT oid INTO principal FROM pg_catalog.pg_roles WHERE rolname=session_user AND rolcanlogin AND NOT
    (rolinherit OR rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls)
    AND COALESCE(array_length(rolconfig,1),0)=0;
  SELECT oid INTO role_oid FROM pg_catalog.pg_roles WHERE rolname=role_name AND NOT
    (rolcanlogin OR rolinherit OR rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls)
    AND COALESCE(array_length(rolconfig,1),0)=0;
  IF principal IS NULL OR role_oid IS NULL OR EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members WHERE member=role_oid)
    OR (SELECT count(*) FROM pg_catalog.pg_auth_members WHERE member=principal)<>1
    OR NOT EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members WHERE member=principal AND roleid=role_oid
                  AND NOT admin_option AND NOT inherit_option AND set_option)
  THEN RAISE EXCEPTION 'm7 principal denied' USING ERRCODE='42501'; END IF;
  IF EXISTS(SELECT 1 FROM pg_catalog.pg_class c WHERE c.relowner=principal)
    OR EXISTS(SELECT 1 FROM pg_catalog.pg_proc p WHERE p.proowner=principal)
    OR EXISTS(SELECT 1 FROM pg_catalog.pg_namespace n WHERE n.nspowner=principal)
    OR EXISTS(SELECT 1 FROM pg_catalog.pg_database d WHERE d.datdba=principal)
    OR EXISTS(SELECT 1 FROM pg_catalog.pg_class c CROSS JOIN LATERAL aclexplode(c.relacl) a WHERE a.grantee IN (principal,role_oid))
    OR EXISTS(SELECT 1 FROM pg_catalog.pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) a WHERE a.grantee=principal OR a.grantee=role_oid AND a.privilege_type<>'USAGE')
    OR EXISTS(SELECT 1 FROM pg_catalog.pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) a WHERE a.grantee=principal)
    OR EXISTS(SELECT 1 FROM pg_catalog.pg_database d CROSS JOIN LATERAL aclexplode(d.datacl) a WHERE a.grantee IN(principal,role_oid)
              AND NOT(d.datname=current_database() AND a.privilege_type='CONNECT' AND NOT a.is_grantable))
    THEN RAISE EXCEPTION 'm7 excess direct authority' USING ERRCODE='42501'; END IF;
  RETURN principal;
END $$;

CREATE FUNCTION factory.m7_scope(capability text,repository text,source text) RETURNS factory.m7_source_bindings
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,factory,pg_temp AS $$
DECLARE binding factory.m7_source_bindings; principal oid;
BEGIN
  principal=factory.m7_principal(capability);
  SELECT * INTO binding FROM factory.m7_source_bindings b WHERE b.principal_oid=principal AND b.principal_name=session_user
    AND b.repository_id=repository AND b.source_id=source AND b.capability_kind=capability
    AND b.enabled AND b.valid_until>statement_timestamp();
  IF NOT FOUND OR NOT factory.m7_binding_valid(binding) THEN RAISE EXCEPTION 'm7 source scope denied' USING ERRCODE='42501'; END IF;
  RETURN binding;
END $$;

CREATE FUNCTION factory.m7_registration_material(body jsonb) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,factory,pg_temp AS $$
DECLARE bundle jsonb=body->'bundle'; evidence jsonb=bundle->'evidence';
  task factory.tasks; run factory.runs; subject factory.semantic_subjects; verdict factory.semantic_verdicts; intake factory.accepted_intents;
  material jsonb; semantic jsonb; b jsonb; m4 jsonb; m5 jsonb; m6 jsonb; expected_evidence jsonb;
  handoff jsonb; expected_bundle jsonb; evidence_digest text; bundle_hash text;
BEGIN
  SELECT * INTO task FROM factory.tasks WHERE task_id=(evidence#>>'{m4,task_id}')::uuid;
  SELECT * INTO run FROM factory.runs WHERE run_id=(evidence#>>'{m4,run_id}')::uuid AND task_id=task.task_id;
  SELECT * INTO subject FROM factory.semantic_subjects WHERE subject_digest=evidence#>>'{m6,subject_digest}';
  SELECT * INTO verdict FROM factory.semantic_verdicts WHERE verdict_digest=evidence#>>'{m6,verdict_digest}';
  IF task.task_id IS NULL OR run.run_id IS NULL OR subject.subject_digest IS NULL OR verdict.verdict_digest IS NULL
    OR task.state<>'ready_for_human' OR run.state<>'completed' OR run.released_at IS NULL
    OR task.generation<>(body->>'generation')::integer OR task.repository_id<>subject.repository_id
    OR subject.task_id<>task.task_id OR subject.run_id<>run.run_id OR subject.fence<>run.fence
    OR run.role<>'writer' OR subject.owner_id<>run.owner_id OR run.packet_digest<>task.packet_digest
    OR verdict.subject_digest<>subject.subject_digest OR verdict.body->>'decision'<>'pass'
  THEN RAISE EXCEPTION 'm7 producer chain mismatch'; END IF;
  SELECT * INTO intake FROM factory.accepted_intents WHERE intent_id=task.intent_id;
  IF NOT FOUND OR intake.intent_digest<>task.packet_digest OR intake.repository_id<>task.repository_id
    OR intake.body->>'intent_digest'<>trim(intake.intent_digest) OR intake.body->>'idempotency_key'<>trim(intake.idempotency_key)
    OR factory.execution_contract_hash(NULL,factory.execution_canonical_json(intake.body-'intent_digest'-'idempotency_key'))<>trim(intake.intent_digest)
    THEN RAISE EXCEPTION 'm7 intent mismatch'; END IF;
  material=factory.semantic_execution_material(task.task_id,subject.workspace_result_digest);
  semantic=factory.semantic_subject_by_digest(task.task_id,subject.subject_digest);
  b=semantic->'binding';
  IF material IS NULL OR b IS NULL OR b->>'task_id'<>task.task_id::text OR b->>'run_id'<>run.run_id::text
    OR b->>'legacy_intent_digest'<>trim(task.packet_digest)
    OR b->>'task_packet_digest'<>material#>>'{packet,packet_digest}'
    OR b->>'run_manifest_digest'<>material#>>'{manifest,manifest_digest}'
    OR b->>'workspace_result_digest'<>material#>>'{result,workspace_result_digest}'
    OR b->>'workspace_snapshot_digest'<>material#>>'{snapshot,workspace_snapshot_digest}'
    OR b->>'terminal_proposal_digest'<>material#>>'{result,terminal_proposal_digest}'
    OR b->>'input_head_sha'<>material#>>'{snapshot,input_head_sha}'
    OR b->>'exact_head_sha'<>material#>>'{result,exact_head_sha}'
    OR factory.execution_contract_hash(NULL,factory.execution_canonical_json(jsonb_build_object('contract','adaptive-factory.semantic-execution-binding/v1')||b))<>trim(subject.execution_binding_digest)
    OR factory.execution_contract_hash(NULL,factory.execution_canonical_json(jsonb_build_object('contract','adaptive-factory.semantic-validation-inputs/v1')||(semantic->'validation_inputs')))<>trim(subject.validation_inputs_digest)
    OR factory.execution_contract_hash(NULL,factory.execution_canonical_json(semantic->'subject'))<>trim(subject.subject_digest)
    OR factory.execution_contract_hash(NULL,factory.execution_canonical_json(verdict.body))<>trim(verdict.verdict_digest)
    OR factory.execution_contract_hash('adaptive-factory.workspace-result/v1',(material->'result')-'workspace_result_digest')<>trim(subject.workspace_result_digest)
    OR factory.execution_contract_hash('adaptive-factory.task-packet/v1',(material->'packet')-'packet_digest')<>b->>'task_packet_digest'
    OR factory.execution_contract_hash('adaptive-factory.run-manifest/v1',(material->'manifest')-'manifest_digest')<>b->>'run_manifest_digest'
    OR factory.execution_contract_hash(NULL,factory.execution_canonical_json(jsonb_build_object('contract','adaptive-factory.workspace-snapshot/v1')||((material->'snapshot')-'workspace_snapshot_digest')))<>b->>'workspace_snapshot_digest'
    OR factory.execution_contract_hash(NULL,factory.execution_canonical_json(jsonb_build_object('contract','adaptive-factory.semantic-subject-envelope/v1',
      'binding_digest',trim(subject.execution_binding_digest),'validation_inputs_digest',trim(subject.validation_inputs_digest),'subject_digest',trim(subject.subject_digest))))<>trim(subject.envelope_digest)
    OR material#>>'{packet,authority,exact_head_sha}'<>b->>'input_head_sha'
    OR material#>>'{packet,authority,exact_base_sha}'<>b->>'exact_base_sha'
    OR b->>'exact_base_sha'<>trim(intake.exact_base_sha)
    OR material#>>'{packet,task_id}'<>task.task_id::text OR material#>>'{packet,run_id}'<>run.run_id::text
    OR material#>>'{packet,owner}'<>run.owner_id OR material#>>'{packet,fence}'<>run.fence::text
    OR material#>>'{packet,legacy_intent_digest}'<>trim(task.packet_digest)
    OR material#>>'{packet,repository_id}'<>task.repository_id
    OR material#>>'{manifest,packet_digest}'<>b->>'task_packet_digest'
    OR material#>>'{manifest,workspace_handle}'<>material#>>'{packet,workspace_handle}'
    OR material#>>'{snapshot,workspace_handle}'<>material#>>'{packet,workspace_handle}'
    OR material#>>'{snapshot,repository_id}'<>task.repository_id
    OR material#>>'{snapshot,result_head_sha}'<>b->>'exact_head_sha'
    OR material#>>'{result,task_id}'<>task.task_id::text OR material#>>'{result,run_id}'<>run.run_id::text
    OR material#>>'{terminal_proposal,task_id}'<>task.task_id::text OR material#>>'{terminal_proposal,run_id}'<>run.run_id::text
    OR material#>>'{terminal_proposal,packet_digest}'<>b->>'task_packet_digest'
    OR material#>>'{terminal_proposal,fence}'<>run.fence::text OR material#>>'{terminal_proposal,author_role}'<>'writer'
    OR factory.execution_contract_hash(NULL,factory.execution_canonical_json(jsonb_build_object(
      'contract','adaptive-factory.execution-proposal/v1','task_id',material#>'{terminal_proposal,task_id}',
      'run_id',material#>'{terminal_proposal,run_id}','packet_digest',material#>'{terminal_proposal,packet_digest}',
      'fence',material#>'{terminal_proposal,fence}','author_role',material#>'{terminal_proposal,author_role}',
      'sequence',material#>'{terminal_proposal,sequence}','event_type',material#>'{terminal_proposal,terminal_type}',
      'body',(material->'terminal_proposal')-'task_id'-'run_id'-'packet_digest'-'fence'-'sequence'-'idempotency_key'
    )))<>b->>'terminal_proposal_digest'
    OR semantic#>>'{subject,exact_head_sha}'<>b->>'exact_head_sha'
    OR semantic#>>'{subject,deterministic_evidence_digest}'<>trim(subject.execution_binding_digest)
    OR semantic#>>'{validation_inputs,workspace_result_digest}'<>b->>'workspace_result_digest'
    OR semantic#>>'{subject,holdout_evidence_digest}'<>semantic#>>'{validation_inputs,holdout_evidence_digest}'
    OR semantic#>>'{subject,review_evidence_digest}'<>semantic#>>'{validation_inputs,review_evidence_digest}'
    OR semantic#>>'{subject,original_writer_id}'<>run.owner_id
    OR semantic#>>'{subject,original_writer_context_digest}'<>semantic#>>'{validation_inputs,original_writer_context_digest}'
  THEN RAISE EXCEPTION 'm7 canonical producer mismatch'; END IF;
  m4=jsonb_build_object('schema_version',1,'task_id',task.task_id::text,'run_id',run.run_id::text,
    'owner',run.owner_id,'role','writer','fence',run.fence,'intent_digest',trim(task.packet_digest),'lease_packet_digest',trim(run.packet_digest));
  m5=(m4-'intent_digest'-'lease_packet_digest')||jsonb_build_object('repository_id',task.repository_id,
    'legacy_intent_digest',trim(task.packet_digest),'task_packet_digest',b->>'task_packet_digest',
    'run_manifest_digest',b->>'run_manifest_digest','workspace_snapshot_digest',b->>'workspace_snapshot_digest',
    'workspace_result_digest',b->>'workspace_result_digest','authority_exact_head_sha',b->>'input_head_sha',
    'snapshot_input_head_sha',b->>'input_head_sha','snapshot_result_head_sha',b->>'exact_head_sha','result_exact_head_sha',b->>'exact_head_sha');
  m6=(m5-'authority_exact_head_sha'-'snapshot_input_head_sha'-'snapshot_result_head_sha'-'result_exact_head_sha')||jsonb_build_object(
    'binding_input_head_sha',b->>'input_head_sha','binding_exact_head_sha',b->>'exact_head_sha',
    'subject_exact_head_sha',semantic#>>'{subject,exact_head_sha}','envelope_digest',trim(subject.envelope_digest),
    'binding_digest',trim(subject.execution_binding_digest),'validation_inputs_digest',trim(subject.validation_inputs_digest),
    'subject_digest',trim(subject.subject_digest),'evidence_set_digest',trim(verdict.evidence_set_digest),
    'verdict_digest',trim(verdict.verdict_digest),'verdict',verdict.body);
  expected_evidence=jsonb_build_object('schema_version',1,'m4',m4,'m5',m5,'m6',m6);
  evidence_digest=factory.m7_hash('adaptive-factory.m7-shadow-task-evidence/v1',expected_evidence);
  handoff=jsonb_build_object('schema_version',1,'subject_digest',evidence_digest,'external_capability','absent',
    'recommended_action','human_review','instructions','["human_decides_merge","inspect_local_bundle","obtain_human_review","verify_exact_sha_trust_ci"]'::jsonb);
  expected_bundle=jsonb_build_object('schema_version',1,'status','blocked_pending_durable_lookup','evidence',expected_evidence,'operator_handoff',handoff);
  bundle_hash=factory.m7_hash('adaptive-factory.m7-ready-for-pr-bundle/v1',expected_bundle);
  expected_bundle=expected_bundle||jsonb_build_object('bundle_digest',bundle_hash);
  IF bundle IS DISTINCT FROM expected_bundle THEN RAISE EXCEPTION 'm7 bundle binding mismatch'; END IF;
  IF body->'profile'<>'null'::jsonb AND body#>>'{profile,repository_id}' IS NOT NULL
      AND body#>>'{profile,repository_id}'<>task.repository_id THEN RAISE EXCEPTION 'm7 profile repository mismatch'; END IF;
  RETURN jsonb_build_object('registration',body,'intake',intake.body,'material',material,'semantic',semantic,
    'verdict',factory.semantic_verdict_by_subject(task.task_id,subject.subject_digest));
END $$;

CREATE FUNCTION factory.m7_register(source text,repository text,idempotency text,canonical text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory,pg_temp SET statement_timeout='10s' SET lock_timeout='3s' AS $$
<<register_command>>
DECLARE binding factory.m7_source_bindings; body jsonb; response jsonb; digest text; prior factory.m7_command_results;
  existing factory.m7_bundles; evidence jsonb;
BEGIN
  binding=factory.m7_scope('registry',repository,source);
  IF binding.source_kind<>'registry' OR current_setting('transaction_isolation')<>'read committed'
    OR idempotency IS NULL OR octet_length(idempotency) NOT BETWEEN 1 AND 128 THEN RAISE EXCEPTION 'm7 registry context'; END IF;
  body=factory.m7_wire('M7BundleRegistrationV1',canonical);
  evidence=body#>'{bundle,evidence}';
  IF evidence#>>'{m5,repository_id}'<>repository THEN RAISE EXCEPTION 'm7 repository mismatch'; END IF;
  digest=factory.m7_hash('adaptive-factory.m7-bundle-registration/v1',canonical);
  PERFORM pg_advisory_xact_lock(hashtextextended('m7-source:'||repository||':'||source,0));
  PERFORM 1 FROM factory.tasks WHERE task_id=(evidence#>>'{m4,task_id}')::uuid FOR SHARE;
  response=factory.m7_registration_material(body);
  SELECT * INTO prior FROM factory.m7_command_results WHERE repository_id=repository AND source_id=source AND operation='register' AND idempotency_key=idempotency;
  IF FOUND THEN
    IF prior.request_digest<>digest OR prior.repository_id<>repository THEN RAISE EXCEPTION 'm7 replay conflict'; END IF;
    IF prior.response_canonical::jsonb IS DISTINCT FROM prior.response_body OR
      factory.m7_hash('adaptive-factory.m7-command-response/v1',prior.response_canonical) IS DISTINCT FROM prior.response_digest
      THEN RAISE EXCEPTION 'm7 corrupt replay'; END IF;
    RETURN prior.response_body;
  END IF;
  SELECT * INTO existing FROM factory.m7_bundles WHERE bundle_digest=register_command.body#>>'{bundle,bundle_digest}';
  IF FOUND AND (existing.registration_digest<>digest OR existing.source_id<>source OR existing.binding_digest<>binding.binding_digest)
    THEN RAISE EXCEPTION 'm7 bundle conflict'; END IF;
  IF NOT FOUND THEN
    INSERT INTO factory.m7_bundles(bundle_digest,registration_digest,repository_id,task_id,run_id,intent_digest,generation,
      workspace_result_digest,subject_digest,verdict_digest,profile_digest,source_id,binding_digest,source_mode,body,canonical_body,selector_digest)
    VALUES(body#>>'{bundle,bundle_digest}',digest,repository,(evidence#>>'{m4,task_id}')::uuid,(evidence#>>'{m4,run_id}')::uuid,
      evidence#>>'{m4,intent_digest}',(body->>'generation')::integer,evidence#>>'{m5,workspace_result_digest}',
      evidence#>>'{m6,subject_digest}',evidence#>>'{m6,verdict_digest}',
      CASE WHEN body->'profile'='null'::jsonb THEN NULL ELSE factory.m7_hash('adaptive-factory.m7-profile-metadata/v1',body->'profile') END,
      source,binding.binding_digest,binding.mode,body,canonical,
      factory.m7_hash('adaptive-factory.m7-selector/v1',factory.m7_metadata(body,binding.binding_digest,binding.mode)));
  END IF;
  INSERT INTO factory.m7_command_results VALUES(source,'register',idempotency,repository,digest,response,factory.m7_canonical_json(response),
    factory.m7_hash('adaptive-factory.m7-command-response/v1',response),clock_timestamp());
  RETURN response;
END $$;

-- Serialize at configured source before reading a stream; never filter latest by a desired head.
CREATE FUNCTION factory.m7_observe(source text,repository text,idempotency text,kind text,canonical text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory,pg_temp SET statement_timeout='10s' SET lock_timeout='3s' AS $$
<<observe_command>>
DECLARE binding factory.m7_source_bindings; capability text; contract text; domain text; relation text;
  body jsonb; provenance jsonb; digest text; stream text; prior factory.m7_command_results;
  latest record; registry factory.m7_bundles; issued timestamptz; observed timestamptz; expires timestamptz;
BEGIN
  IF kind='human_outcome' THEN capability='outcome'; contract='M7OutcomeObservationV1'; domain='outcome-observation'; relation='m7_outcomes';
  ELSIF kind='signed_ci' THEN capability='check_context'; contract='M7CheckObservationV1'; domain='check-observation'; relation='m7_checks';
  ELSIF kind='github_current' THEN capability='check_context'; contract='M7GitHubContextV1'; domain='github-context'; relation='m7_contexts';
  ELSIF kind='deployed_epoch' THEN capability='check_context'; contract='M7EpochContextV1'; domain='epoch-context'; relation='m7_contexts';
  ELSE RAISE EXCEPTION 'm7 source kind denied'; END IF;
  binding=factory.m7_scope(capability,repository,source);
  IF binding.source_kind<>kind OR current_setting('transaction_isolation')<>'read committed'
    OR idempotency IS NULL OR octet_length(idempotency) NOT BETWEEN 1 AND 128 THEN RAISE EXCEPTION 'm7 observation context'; END IF;
  body=factory.m7_wire(contract,canonical); provenance=body->'provenance';
  IF body->>'repository_id'<>repository OR provenance->>'source_id'<>source OR provenance->>'source_kind'<>kind
    OR provenance->>'trust_config_digest'<>binding.trust_config_digest OR provenance->>'evidence_ref' LIKE '%://%'
    OR provenance->>'evidence_ref' LIKE 'file:%' THEN RAISE EXCEPTION 'm7 source binding mismatch'; END IF;
  issued=(provenance->>'source_issued_at')::timestamptz; observed=(provenance->>'observed_at')::timestamptz;
  expires=(provenance->>'valid_until')::timestamptz;
  IF issued>observed OR observed>=expires OR observed>statement_timestamp()
    OR expires>observed+make_interval(secs=>binding.max_age_seconds)
    THEN RAISE EXCEPTION 'm7 observation time invalid'; END IF;
  digest=factory.m7_hash('adaptive-factory.m7-'||domain||'/v1',canonical);
  stream=repository||':'||kind||':'||COALESCE(body->>'bundle_digest',body->>'pr_number','0');
  PERFORM pg_advisory_xact_lock(hashtextextended('m7-source:'||repository||':'||source,0));
  IF kind='human_outcome' THEN
    SELECT * INTO registry FROM factory.m7_bundles WHERE bundle_digest=observe_command.body->>'bundle_digest' AND repository_id=repository;
    IF NOT FOUND OR registry.body#>>'{bundle,evidence,m5,result_exact_head_sha}'<>body->>'result_head_sha'
      THEN RAISE EXCEPTION 'm7 outcome subject mismatch'; END IF;
    PERFORM 1 FROM factory.tasks WHERE task_id=registry.task_id FOR SHARE;
    PERFORM factory.m7_registration_material(registry.body);
    IF body->'outcome'<>'null'::jsonb AND (
      body#>>'{outcome,bundle_digest}'<>registry.bundle_digest OR (body#>>'{outcome,human_decision}'='merged_accepted') IS DISTINCT FROM (body->>'decision'='accepted')
      OR body#>>'{outcome,first_pass_accepted}'='true' AND (body#>>'{outcome,rework_required}'='true' OR body#>>'{outcome,human_decision}'<>'merged_accepted')
      OR (body#>>'{outcome,injection_contained_count}')::bigint>(body#>>'{outcome,injection_attempt_count}')::bigint
    ) THEN RAISE EXCEPTION 'm7 nested outcome mismatch'; END IF;
    IF body->'profile'<>'null'::jsonb AND (
      body#>>'{profile,repository_id}' IS NOT NULL AND body#>>'{profile,repository_id}'<>repository
      OR registry.profile_digest IS NOT NULL AND registry.profile_digest<>factory.m7_hash('adaptive-factory.m7-profile-metadata/v1',body->'profile')
      OR body->'outcome'<>'null'::jsonb AND body#>>'{profile,m7_cohort_key_digest}' IS NOT NULL
        AND body#>>'{profile,m7_cohort_key_digest}'<>body#>>'{outcome,cohort_key_digest}'
    ) THEN RAISE EXCEPTION 'm7 outcome profile mismatch'; END IF;
    IF ((body#>>'{measurements,intervention_count}') IS NULL) IS DISTINCT FROM (body#>>'{measurements,intervention_coverage}'='unknown')
      OR body#>>'{measurements,intervention_count}' IS NOT NULL AND jsonb_array_length(body#>'{measurements,intervention_source_refs}')=0
      OR body#>>'{measurements,intervention_coverage}'='complete' AND (
        body#>>'{measurements,session_started_at}' IS NULL OR body#>>'{measurements,session_ended_at}' IS NULL)
      OR (body#>>'{measurements,session_started_at}')::timestamptz>(body#>>'{measurements,session_ended_at}')::timestamptz
      OR (body#>>'{measurements,session_started_at}')::timestamptz>observed
      OR (body#>>'{measurements,session_ended_at}')::timestamptz>observed
    THEN RAISE EXCEPTION 'm7 measurement coverage mismatch'; END IF;
  END IF;
  SELECT * INTO prior FROM factory.m7_command_results WHERE repository_id=repository AND source_id=source AND operation=kind AND idempotency_key=idempotency;
  IF FOUND THEN
    IF prior.request_digest<>digest OR prior.repository_id<>repository THEN RAISE EXCEPTION 'm7 replay conflict'; END IF;
    IF prior.response_canonical::jsonb IS DISTINCT FROM prior.response_body OR
      factory.m7_hash('adaptive-factory.m7-command-response/v1',prior.response_canonical) IS DISTINCT FROM prior.response_digest
      THEN RAISE EXCEPTION 'm7 corrupt replay'; END IF;
    RETURN prior.response_body;
  END IF;
  EXECUTE format('SELECT o.*,pg_catalog.to_jsonb(o) AS full_row FROM factory.%I o WHERE lookup_source=$1 AND lookup_stream=$2 AND lookup_repository=$3 ORDER BY lookup_revision DESC LIMIT 1',relation)
    INTO latest USING source,stream,repository;
  IF latest.source_revision IS NOT NULL AND NOT factory.m7_row_valid(kind,latest.full_row,binding)
    THEN RAISE EXCEPTION 'm7 corrupt predecessor'; END IF;
  IF latest.source_revision IS NULL THEN
    IF (provenance->>'source_revision')::bigint<>1 OR provenance->'predecessor_digest'<>'null'::jsonb THEN RAISE EXCEPTION 'm7 missing predecessor'; END IF;
  ELSIF latest.observation_digest<>provenance->>'predecessor_digest'
    OR latest.source_revision+1<>(provenance->>'source_revision')::bigint OR latest.observed_at>observed
    OR latest.binding_digest<>binding.binding_digest THEN RAISE EXCEPTION 'm7 stale predecessor'; END IF;
  IF kind='human_outcome' THEN
    INSERT INTO factory.m7_outcomes(observation_digest,repository_id,bundle_digest,source_id,source_event_id,stream_key,
      source_revision,predecessor_digest,binding_digest,source_mode,observed_at,valid_until,body,canonical_body,selector_digest)
    VALUES(digest,repository,body->>'bundle_digest',source,provenance->>'source_event_id',stream,
      (provenance->>'source_revision')::bigint,provenance->>'predecessor_digest',binding.binding_digest,binding.mode,observed,expires,body,canonical,
      factory.m7_hash('adaptive-factory.m7-selector/v1',factory.m7_metadata(body,binding.binding_digest,binding.mode)));
  ELSIF kind='signed_ci' THEN
    INSERT INTO factory.m7_checks(observation_digest,repository_id,pr_number,base_sha,head_sha,policy_digest,source_id,source_event_id,stream_key,
      source_revision,predecessor_digest,binding_digest,source_mode,observed_at,valid_until,body,canonical_body,selector_digest)
    VALUES(digest,repository,(body->>'pr_number')::bigint,body->>'base_sha',body->>'head_sha',body->>'policy_digest',source,provenance->>'source_event_id',stream,
      (provenance->>'source_revision')::bigint,provenance->>'predecessor_digest',binding.binding_digest,binding.mode,observed,expires,body,canonical,
      factory.m7_hash('adaptive-factory.m7-selector/v1',factory.m7_metadata(body,binding.binding_digest,binding.mode)));
  ELSE
    INSERT INTO factory.m7_contexts(observation_digest,repository_id,pr_number,source_kind,source_id,source_event_id,stream_key,
      source_revision,predecessor_digest,binding_digest,source_mode,observed_at,valid_until,body,canonical_body,selector_digest)
    VALUES(digest,repository,COALESCE((body->>'pr_number')::bigint,0),kind,source,provenance->>'source_event_id',stream,
      (provenance->>'source_revision')::bigint,provenance->>'predecessor_digest',binding.binding_digest,binding.mode,observed,expires,body,canonical,
      factory.m7_hash('adaptive-factory.m7-selector/v1',factory.m7_metadata(body,binding.binding_digest,binding.mode)));
  END IF;
  INSERT INTO factory.m7_command_results VALUES(source,kind,idempotency,repository,digest,body,canonical,
    factory.m7_hash('adaptive-factory.m7-command-response/v1',canonical),clock_timestamp());
  RETURN body;
END $$;

CREATE FUNCTION factory.m7_lookup(canonical text) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,factory,pg_temp SET statement_timeout='10s' SET lock_timeout='3s' AS $$
DECLARE request jsonb; principal oid; registry factory.m7_bundles; result jsonb; reasons jsonb='[]'; modes jsonb='[]';
  scope factory.m7_source_bindings; writer factory.m7_source_bindings; item record; kind text; field text; candidates integer; writer_count integer;
  now_at timestamptz=statement_timestamp(); selected jsonb; usable boolean; domain text; contract text;
BEGIN
  principal=factory.m7_principal('reader'); request=factory.m7_wire('M7LookupRequestV1',canonical);
  IF current_setting('transaction_isolation')<>'read committed' THEN RAISE EXCEPTION 'm7 lookup isolation'; END IF;
  result=jsonb_build_object('registration',NULL,'outcome',NULL,'check',NULL,'github',NULL,'epoch',NULL,
    'observed_at',replace(to_char(now_at AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),'.000000Z','Z'));
  FOR kind,field IN SELECT * FROM (VALUES('registry','registration'),('human_outcome','outcome'),('signed_ci','check'),('github_current','github'),('deployed_epoch','epoch')) kinds LOOP
    candidates=0; selected=NULL;
    FOR scope IN SELECT * FROM factory.m7_source_bindings s WHERE s.principal_oid=principal AND s.principal_name=session_user
      AND s.repository_id=request->>'repository_id' AND s.capability_kind='reader' AND s.source_kind=kind
      ORDER BY s.source_id LIMIT 33 LOOP
      candidates=candidates+1;
      IF candidates>1 THEN CONTINUE; END IF;
      usable=scope.enabled AND scope.valid_until>now_at AND scope.mode<>'imported';
      SELECT count(*) INTO writer_count FROM (SELECT 1 FROM factory.m7_source_bindings s WHERE s.repository_id=scope.repository_id
        AND s.source_id=scope.source_id AND s.source_kind=kind AND s.capability_kind=CASE kind WHEN 'registry' THEN 'registry' WHEN 'human_outcome' THEN 'outcome' ELSE 'check_context' END LIMIT 2) candidate;
      IF writer_count<>1 THEN selected=NULL; reasons=reasons||jsonb_build_array(field||'_source_conflict'); CONTINUE; END IF;
      SELECT * INTO writer FROM factory.m7_source_bindings s WHERE s.repository_id=scope.repository_id
        AND s.source_id=scope.source_id AND s.source_kind=kind AND s.capability_kind=CASE kind WHEN 'registry' THEN 'registry' WHEN 'human_outcome' THEN 'outcome' ELSE 'check_context' END
        AND EXISTS(SELECT 1 FROM pg_catalog.pg_roles r WHERE r.oid=s.principal_oid AND r.rolname=s.principal_name)
        ;
      IF NOT FOUND OR NOT factory.m7_binding_valid(writer) OR NOT factory.m7_binding_valid(scope) OR NOT writer.enabled OR writer.valid_until<=now_at OR writer.mode='imported'
        OR writer.trust_config_digest<>scope.trust_config_digest THEN usable=false; END IF;
      IF kind='registry' THEN
        SELECT * INTO registry FROM factory.m7_bundles WHERE bundle_digest=request->>'bundle_digest'
          AND repository_id=scope.repository_id AND source_id=scope.source_id;
        IF NOT FOUND THEN reasons=reasons||jsonb_build_array('registration_missing'); CONTINUE; END IF;
        IF registry.registration_digest<>factory.m7_hash('adaptive-factory.m7-bundle-registration/v1',registry.canonical_body)
          OR NOT factory.m7_row_valid('registry',pg_catalog.to_jsonb(registry),writer)
          OR registry.binding_digest<>writer.binding_digest OR registry.task_id::text<>request->>'task_id'
          OR registry.run_id::text<>request->>'run_id' OR registry.generation<>(request->>'generation')::integer
          OR registry.body#>>'{bundle,evidence,m5,result_exact_head_sha}'<>request->>'head_sha'
          OR request->>'profile_digest' IS NOT NULL AND registry.profile_digest IS DISTINCT FROM request->>'profile_digest'
          THEN usable=false; END IF;
        IF usable THEN
          BEGIN selected=factory.m7_registration_material(registry.body);
            IF selected#>>'{semantic,binding,exact_base_sha}' IS DISTINCT FROM request->>'base_sha'
              THEN usable=false; reasons=reasons||jsonb_build_array('registration_subject_mismatch'); END IF;
          EXCEPTION WHEN OTHERS THEN usable=false; reasons=reasons||jsonb_build_array('producer_stale'); END;
        END IF;
      ELSE
        IF kind='human_outcome' THEN
          SELECT o.*,pg_catalog.to_jsonb(o) AS full_row INTO item FROM factory.m7_outcomes o
            WHERE o.lookup_bundle=request->>'bundle_digest' AND o.lookup_source=scope.source_id AND o.lookup_repository=scope.repository_id
            ORDER BY o.lookup_revision DESC LIMIT 1;
        ELSIF kind='signed_ci' THEN
          SELECT o.*,pg_catalog.to_jsonb(o) AS full_row INTO item FROM factory.m7_checks o
            WHERE o.lookup_repository=scope.repository_id AND o.lookup_pr=(request->>'pr_number')::bigint AND o.lookup_source=scope.source_id
            ORDER BY o.lookup_revision DESC LIMIT 1;
        ELSE
          SELECT o.*,pg_catalog.to_jsonb(o) AS full_row INTO item FROM factory.m7_contexts o
            WHERE o.lookup_repository=scope.repository_id AND o.lookup_pr=CASE kind WHEN 'github_current' THEN (request->>'pr_number')::bigint ELSE 0 END
              AND o.lookup_source=scope.source_id AND o.lookup_kind=kind ORDER BY o.lookup_revision DESC LIMIT 1;
        END IF;
        IF NOT FOUND THEN reasons=reasons||jsonb_build_array(field||'_missing'); CONTINUE; END IF;
        IF item.binding_digest IS DISTINCT FROM writer.binding_digest OR item.observed_at>now_at OR item.valid_until<=now_at
          OR item.observed_at+make_interval(secs=>LEAST(writer.max_age_seconds,scope.max_age_seconds))<=now_at
          THEN usable=false;
          IF item.valid_until<=now_at OR item.observed_at+make_interval(secs=>LEAST(writer.max_age_seconds,scope.max_age_seconds))<=now_at
            THEN reasons=reasons||jsonb_build_array(field||'_expired'); END IF;
        END IF;
        selected=item.body;
        domain=CASE kind WHEN 'human_outcome' THEN 'outcome-observation' WHEN 'signed_ci' THEN 'check-observation'
          WHEN 'github_current' THEN 'github-context' ELSE 'epoch-context' END;
        contract=CASE kind WHEN 'human_outcome' THEN 'M7OutcomeObservationV1' WHEN 'signed_ci' THEN 'M7CheckObservationV1'
          WHEN 'github_current' THEN 'M7GitHubContextV1' ELSE 'M7EpochContextV1' END;
        IF NOT factory.m7_row_valid(kind,item.full_row,writer)
          OR factory.m7_hash('adaptive-factory.m7-'||domain||'/v1',item.canonical_body) IS DISTINCT FROM item.observation_digest
          OR NOT factory.m7_schema_valid(selected,factory.m7_wire_catalog()->contract)
          THEN usable=false; reasons=reasons||jsonb_build_array(field||'_corrupt'); END IF;
        IF usable AND (selected->>'result'='revoked' OR selected->>'revoked'='true')
          THEN reasons=reasons||jsonb_build_array(field||'_revoked'); END IF;
        IF usable AND kind='human_outcome' AND selected->>'decision'<>'accepted'
          THEN reasons=reasons||jsonb_build_array('outcome_'||(selected->>'decision')); END IF;
      END IF;
      IF usable THEN
        IF NOT modes ? writer.mode THEN modes=modes||jsonb_build_array(writer.mode); END IF;
      ELSE selected=NULL; reasons=reasons||jsonb_build_array(field||'_source_unavailable'); END IF;
    END LOOP;
    IF candidates=0 THEN reasons=reasons||jsonb_build_array(field||'_source_unconfigured');
    ELSIF candidates>1 THEN selected=NULL; reasons=reasons||jsonb_build_array(field||'_source_conflict'); END IF;
    result=jsonb_set(result,ARRAY[field],COALESCE(selected,'null'::jsonb));
  END LOOP;
  RETURN result||jsonb_build_object('unavailable_reasons',COALESCE((SELECT jsonb_agg(v ORDER BY v COLLATE "C") FROM (SELECT DISTINCT v FROM jsonb_array_elements_text(reasons) v) x),'[]'::jsonb),'source_modes',COALESCE((SELECT jsonb_agg(v ORDER BY v COLLATE "C") FROM jsonb_array_elements_text(modes) v),'[]'::jsonb));
END $$;

-- Evidence and command results are append-only; configuration is an owner operation.
DO $$ DECLARE relation text; routine record;
BEGIN
  FOREACH relation IN ARRAY ARRAY['m7_bundles','m7_outcomes','m7_checks','m7_contexts','m7_command_results'] LOOP
    EXECUTE format('CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON factory.%I FOR EACH ROW EXECUTE FUNCTION factory.semantic_reject_mutation()',relation||'_immutable',relation);
  END LOOP;
  FOREACH relation IN ARRAY ARRAY['m7_bundles','m7_outcomes','m7_checks','m7_contexts','m7_command_results','m7_source_bindings'] LOOP
    EXECUTE format('REVOKE ALL ON factory.%I FROM PUBLIC,factory_runtime,factory_m7_registry,factory_m7_outcome,factory_m7_check_context,factory_m7_reader',relation);
  END LOOP;
  FOR routine IN SELECT p.oid::regprocedure AS signature FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='factory' AND p.proname LIKE 'm7_%' LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC,factory_runtime',routine.signature);
  END LOOP;
END $$;
GRANT EXECUTE ON FUNCTION factory.m7_register(text,text,text,text) TO factory_m7_registry;
GRANT EXECUTE ON FUNCTION factory.m7_observe(text,text,text,text,text) TO factory_m7_outcome,factory_m7_check_context;
GRANT EXECUTE ON FUNCTION factory.m7_lookup(text) TO factory_m7_reader;

-- Only new objects are owned by this nonlogin capability; no memberships are seeded.
DO $$ BEGIN
  IF NOT EXISTS(SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='factory_evidence_owner') THEN
    CREATE ROLE factory_evidence_owner NOLOGIN NOINHERIT NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS;
  END IF;
  IF EXISTS(SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='factory_evidence_owner' AND
    (rolcanlogin OR rolinherit OR rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls
      OR COALESCE(array_length(rolconfig,1),0)>0)) OR EXISTS(
    SELECT 1 FROM pg_catalog.pg_auth_members m JOIN pg_catalog.pg_roles r ON r.oid=m.member OR r.oid=m.roleid
      WHERE r.rolname='factory_evidence_owner') THEN RAISE EXCEPTION 'unsafe evidence owner'; END IF;
END $$;
GRANT USAGE ON SCHEMA factory TO factory_evidence_owner;
GRANT SELECT ON factory.tasks,factory.runs,factory.accepted_intents,factory.semantic_subjects,factory.semantic_verdicts TO factory_evidence_owner;
-- PostgreSQL row-share locks require UPDATE on one column; no identity/state grant.
GRANT UPDATE(updated_at) ON factory.tasks TO factory_evidence_owner;
GRANT EXECUTE ON FUNCTION factory.semantic_execution_material(uuid,char),factory.semantic_subject_by_digest(uuid,char),
  factory.semantic_verdict_by_subject(uuid,char),factory.execution_canonical_json(jsonb),
  factory.execution_contract_hash(text,jsonb),factory.execution_contract_hash(text,text) TO factory_evidence_owner;
DO $$ DECLARE relation text; routine record;
BEGIN
  FOREACH relation IN ARRAY ARRAY['m7_bundles','m7_outcomes','m7_checks','m7_contexts','m7_command_results','m7_source_bindings'] LOOP
    EXECUTE format('ALTER TABLE factory.%I OWNER TO factory_evidence_owner',relation);
  END LOOP;
  FOR routine IN SELECT p.oid::regprocedure AS signature FROM pg_catalog.pg_proc p
    JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='factory' AND p.proname LIKE 'm7_%' LOOP
    EXECUTE format('ALTER FUNCTION %s OWNER TO factory_evidence_owner',routine.signature);
  END LOOP;
END $$;
