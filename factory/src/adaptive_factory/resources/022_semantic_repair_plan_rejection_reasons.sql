-- Name existing planning refusals without changing predicates, locks, or lifecycle results.
-- Historical resources 001 through 021 remain immutable; recovery uses a later forward migration.

CREATE OR REPLACE FUNCTION factory.semantic_plan_repair(
  p_idempotency_key char(64),p_request_digest char(64),
  p_request_canonical text,p_task_id uuid
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_request jsonb;
  v_input jsonb;
  v_subject factory.semantic_subjects%ROWTYPE;
  v_verdict factory.semantic_verdicts%ROWTYPE;
  v_result factory.workspace_results%ROWTYPE;
  v_packet factory.execution_packets%ROWTYPE;
  v_manifest factory.execution_manifests%ROWTYPE;
  v_current_task factory.tasks%ROWTYPE;
  v_current_intent factory.accepted_intents%ROWTYPE;
  v_prior factory.semantic_command_results%ROWTYPE;
  v_previous factory.semantic_child_proposals%ROWTYPE;
  v_handoff factory.semantic_child_task_bindings%ROWTYPE;
  v_existing_directive factory.semantic_directives%ROWTYPE;
  v_existing_child factory.semantic_child_proposals%ROWTYPE;
  v_reason text;
  v_cycle integer;
  v_lineage_count integer := 0;
  v_budget integer;
  v_remaining_cost bigint;
  v_remaining_tokens bigint;
  v_remaining_output bigint;
  v_remaining_events bigint;
  v_remaining_infrastructure_retries integer;
  v_baseline_risk text;
  v_deadline text;
  v_finding_list text;
  v_previous_json text;
  v_directive_canonical text;
  v_directive jsonb;
  v_directive_digest char(64);
  v_child_canonical text;
  v_child jsonb;
  v_child_digest char(64);
  v_escalation_canonical text;
  v_escalation jsonb;
  v_escalation_digest char(64);
  v_response jsonb;
BEGIN
  IF current_setting('transaction_isolation') IS DISTINCT FROM 'read committed'
    OR p_idempotency_key IS NULL OR p_idempotency_key !~ '^[0-9a-f]{64}$'
    OR p_request_digest IS NULL OR p_request_digest !~ '^[0-9a-f]{64}$'
    OR p_request_canonical IS NULL OR octet_length(p_request_canonical)>262144
    OR p_task_id IS NULL
  THEN RETURN jsonb_build_object('repair_plan_rejection','command_input_invalid'); END IF;

  v_request=p_request_canonical::jsonb;
  v_input=v_request->'repair_request';
  IF trim(factory.execution_contract_hash(NULL,p_request_canonical))
      IS DISTINCT FROM trim(p_request_digest)
    OR jsonb_typeof(v_request) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_request))<>4
    OR v_request->>'contract' IS DISTINCT FROM
      'adaptive-factory.semantic-repair-command/v1'
    OR v_request->>'idempotency_key' IS DISTINCT FROM trim(p_idempotency_key)
    OR v_request->>'task_id' IS DISTINCT FROM p_task_id::text
    OR jsonb_typeof(v_input) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_input))<>15
    OR NOT (v_input ?& ARRAY[
      'schema_version','subject_digest','verdict_digest','requested_cycle',
      'previous_child_proposal_digest','writer_id','context_digest',
      'expected_workspace_result_digest','expected_fence','expected_head_sha',
      'expected_base_sha','expected_architecture_digest','expected_authority_digest',
      'expected_diff_digest','expected_risk_level'
    ])
    OR v_input->>'schema_version' IS DISTINCT FROM '1'
    OR jsonb_typeof(v_input->'requested_cycle') IS DISTINCT FROM 'number'
    OR v_input->>'requested_cycle' !~ '^(0|[1-9][0-9]{0,6})$'
    OR (v_input->>'requested_cycle')::integer>1000000
    OR jsonb_typeof(v_input->'expected_fence') IS DISTINCT FROM 'number'
    OR v_input->>'expected_fence' !~ '^[1-9][0-9]{0,18}$'
    OR v_input->>'subject_digest' !~ '^[0-9a-f]{64}$'
    OR v_input->>'verdict_digest' !~ '^[0-9a-f]{64}$'
    OR v_input->>'context_digest' !~ '^[0-9a-f]{64}$'
    OR v_input->>'expected_workspace_result_digest' !~ '^[0-9a-f]{64}$'
    OR v_input->>'expected_head_sha' !~ '^[0-9a-f]{40}$'
    OR v_input->>'expected_base_sha' !~ '^[0-9a-f]{40}$'
    OR v_input->>'expected_architecture_digest' !~ '^[0-9a-f]{64}$'
    OR v_input->>'expected_authority_digest' !~ '^[0-9a-f]{64}$'
    OR v_input->>'expected_diff_digest' !~ '^[0-9a-f]{64}$'
    OR COALESCE(octet_length(v_input->>'writer_id'),0) NOT BETWEEN 1 AND 128
    OR v_input->>'writer_id' !~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR v_input->>'expected_risk_level' NOT IN ('low','medium','high','critical')
    OR jsonb_typeof(v_input->'previous_child_proposal_digest')
      NOT IN ('null','string')
    OR (
      jsonb_typeof(v_input->'previous_child_proposal_digest')='string'
      AND v_input->>'previous_child_proposal_digest' !~ '^[0-9a-f]{64}$'
    )
  THEN RETURN jsonb_build_object('repair_plan_rejection','repair_payload_invalid'); END IF;

  v_cycle=(v_input->>'requested_cycle')::integer;
  IF (v_cycle=1 AND v_input->>'previous_child_proposal_digest' IS NOT NULL)
    OR (v_cycle>=2 AND v_input->>'previous_child_proposal_digest' IS NULL)
  THEN RETURN jsonb_build_object('repair_plan_rejection','cycle_lineage_invalid'); END IF;

  SELECT * INTO v_prior FROM factory.semantic_command_results
    WHERE operation='plan_repair' AND idempotency_key=p_idempotency_key;
  IF FOUND THEN
    RETURN CASE WHEN v_prior.request_digest=p_request_digest
      THEN v_prior.response_body ELSE jsonb_build_object('repair_plan_rejection','idempotency_conflict') END;
  END IF;

  SELECT * INTO v_subject FROM factory.semantic_subjects
    WHERE task_id=p_task_id
      AND subject_digest=(v_input->>'subject_digest')::char(64)
    FOR UPDATE;
  IF NOT FOUND THEN RETURN jsonb_build_object('repair_plan_rejection','subject_not_found'); END IF;
  SELECT * INTO v_verdict FROM factory.semantic_verdicts
    WHERE subject_digest=v_subject.subject_digest
      AND verdict_digest=(v_input->>'verdict_digest')::char(64);
  IF NOT FOUND OR v_verdict.body IS DISTINCT FROM
      factory.semantic_expected_verdict(v_subject.subject_digest)
  THEN RETURN jsonb_build_object('repair_plan_rejection','verdict_mismatch'); END IF;

  SELECT * INTO v_result FROM factory.workspace_results
    WHERE workspace_result_digest=v_subject.workspace_result_digest;
  SELECT * INTO v_packet FROM factory.execution_packets
    WHERE packet_digest=v_subject.task_packet_digest AND run_id=v_subject.run_id;
  SELECT * INTO v_manifest FROM factory.execution_manifests
    WHERE manifest_digest=v_subject.run_manifest_digest AND run_id=v_subject.run_id;
  SELECT * INTO v_current_task FROM factory.tasks
    WHERE task_id=v_subject.task_id;
  SELECT * INTO v_current_intent FROM factory.accepted_intents
    WHERE intent_id=v_current_task.intent_id;
  IF v_result.workspace_result_digest IS NULL OR v_packet.packet_digest IS NULL
    OR v_manifest.manifest_digest IS NULL OR v_current_task.task_id IS NULL
    OR v_current_intent.intent_id IS NULL
  THEN RETURN jsonb_build_object('repair_plan_rejection','execution_material_missing'); END IF;

  IF v_cycle BETWEEN 2 AND 3 THEN
    SELECT * INTO v_previous FROM factory.semantic_child_proposals
      WHERE child_proposal_digest=
        (v_input->>'previous_child_proposal_digest')::char(64);
    IF NOT FOUND OR v_previous.cycle<>v_cycle-1
      OR v_previous.body->>'proposal_state' IS DISTINCT FROM 'pending_handoff'
      OR v_previous.body->>'writer_id' IS DISTINCT FROM v_subject.owner_id
      OR v_previous.body->>'exact_base_sha' IS DISTINCT FROM
        v_subject.subject_body->>'exact_base_sha'
      OR v_previous.body->>'architecture_digest' IS DISTINCT FROM
        v_subject.subject_body->>'architecture_digest'
      OR NOT EXISTS (
        SELECT 1
        FROM factory.semantic_subjects previous_subject
        JOIN factory.execution_packets previous_packet
          ON previous_packet.packet_digest=previous_subject.task_packet_digest
            AND previous_packet.run_id=previous_subject.run_id
        WHERE previous_subject.subject_digest=v_previous.subject_digest
          AND (previous_packet.body->'authority')-'exact_head_sha'
            IS NOT DISTINCT FROM
              (v_packet.body->'authority')-'exact_head_sha'
      )
      OR (
        v_previous.subject_digest<>v_subject.subject_digest
        AND v_previous.body->>'context_digest' IS DISTINCT FROM
          v_subject.subject_body->>'original_writer_context_digest'
      )
    THEN RETURN jsonb_build_object('repair_plan_rejection','previous_proposal_mismatch'); END IF;
    IF v_previous.subject_digest<>v_subject.subject_digest THEN
      SELECT * INTO v_handoff FROM factory.semantic_child_task_bindings
        WHERE child_proposal_digest=v_previous.child_proposal_digest
          AND child_task_id=v_subject.task_id
          AND child_intent_digest=v_current_intent.intent_digest;
      IF NOT FOUND
        OR v_handoff.body->>'child_proposal_digest' IS DISTINCT FROM
          trim(v_previous.child_proposal_digest)
        OR v_handoff.body->>'child_task_id' IS DISTINCT FROM v_subject.task_id::text
        OR v_handoff.body->>'child_intent_digest' IS DISTINCT FROM
          trim(v_current_intent.intent_digest)
        OR v_current_task.repository_id IS DISTINCT FROM v_subject.repository_id
        OR v_current_intent.repository_id IS DISTINCT FROM v_subject.repository_id
        OR v_current_task.source_type IS DISTINCT FROM 'api'
        OR v_current_intent.source_type IS DISTINCT FROM 'api'
        OR v_current_task.source_id IS DISTINCT FROM trim(v_previous.child_proposal_digest)
        OR v_current_intent.source_id IS DISTINCT FROM trim(v_previous.child_proposal_digest)
        OR v_current_intent.source_digest IS DISTINCT FROM
          v_previous.child_proposal_digest
        OR trim(v_current_intent.exact_base_sha) IS DISTINCT FROM
          v_previous.body->>'exact_base_sha'
        OR trim(v_current_intent.architecture_digest) IS DISTINCT FROM
          v_previous.body->>'architecture_digest'
        OR trim(v_subject.input_head_sha) IS DISTINCT FROM
          v_previous.body->>'parent_exact_head_sha'
        OR v_packet.body#>>'{authority,exact_head_sha}' IS DISTINCT FROM
          v_previous.body->>'parent_exact_head_sha'
        OR v_current_intent.body#>>'{architecture,exact_head_sha}' IS DISTINCT FROM
          v_previous.body->>'parent_exact_head_sha'
        OR v_current_intent.body#>>'{governance,exact_head_sha}' IS DISTINCT FROM
          v_previous.body->>'parent_exact_head_sha'
        OR v_current_intent.body#>>'{m0_authority,exact_head_sha}' IS DISTINCT FROM
          v_previous.body->>'parent_exact_head_sha'
        OR v_current_task.accepted_at<v_previous.created_at
      THEN RETURN jsonb_build_object('repair_plan_rejection','child_handoff_mismatch'); END IF;
    END IF;
    WITH RECURSIVE lineage AS (
      SELECT child_proposal_digest,cycle,body,previous_child_proposal_digest
      FROM factory.semantic_child_proposals
      WHERE child_proposal_digest=
        (v_input->>'previous_child_proposal_digest')::char(64)
      UNION ALL
      SELECT prior.child_proposal_digest,prior.cycle,prior.body,
        prior.previous_child_proposal_digest
      FROM factory.semantic_child_proposals prior
      JOIN lineage child
        ON prior.child_proposal_digest=child.previous_child_proposal_digest
    )
    SELECT count(*) INTO v_lineage_count FROM lineage;
    IF v_lineage_count<>v_cycle-1 OR EXISTS (
      WITH RECURSIVE lineage AS (
        SELECT cycle,subject_digest,body,previous_child_proposal_digest
        FROM factory.semantic_child_proposals
        WHERE child_proposal_digest=
          (v_input->>'previous_child_proposal_digest')::char(64)
        UNION ALL
        SELECT prior.cycle,prior.subject_digest,prior.body,
          prior.previous_child_proposal_digest
        FROM factory.semantic_child_proposals prior JOIN lineage child
          ON prior.child_proposal_digest=child.previous_child_proposal_digest
      )
      SELECT 1 FROM lineage
      JOIN factory.semantic_subjects lineage_subject
        ON lineage_subject.subject_digest=lineage.subject_digest
      WHERE body->>'baseline_risk_level' IS DISTINCT FROM
        v_previous.body->>'baseline_risk_level'
        OR body->>'baseline_risk_level' NOT IN ('low','medium','high','critical')
        OR body->>'parent_exact_head_sha' IS DISTINCT FROM
          trim(lineage_subject.exact_head_sha)
        OR body->>'authority_digest' IS DISTINCT FROM
          lineage_subject.subject_body->>'authority_digest'
    ) THEN RETURN jsonb_build_object('repair_plan_rejection','lineage_mismatch'); END IF;
    v_baseline_risk=v_previous.body->>'baseline_risk_level';
    v_budget=LEAST(
      (v_packet.body#>>'{limits,semantic_repairs}')::integer,
      (v_previous.body->>'budget_remaining_units')::integer
    )-1;
    v_deadline=CASE
      WHEN (v_manifest.body->>'deadline')::timestamptz<=
        (v_previous.body->>'deadline_at')::timestamptz
      THEN v_manifest.body->>'deadline'
      ELSE v_previous.body->>'deadline_at'
    END;
  ELSE
    v_lineage_count=0;
    v_baseline_risk=v_subject.subject_body->>'risk_level';
    v_budget=(v_packet.body#>>'{limits,semantic_repairs}')::integer;
    v_deadline=v_manifest.body->>'deadline';
  END IF;
  IF v_baseline_risk NOT IN ('low','medium','high','critical') THEN RETURN jsonb_build_object('repair_plan_rejection','baseline_risk_invalid'); END IF;
  v_remaining_cost=GREATEST(
    v_current_task.cost_limit_micros-v_current_task.cost_observed_micros,0
  );
  v_remaining_tokens=GREATEST(
    v_current_task.token_limit-v_current_task.tokens_observed,0
  );
  SELECT GREATEST(
      v_current_task.output_limit_bytes-COALESCE(sum(output_bytes),0),0
    ) INTO v_remaining_output
    FROM factory.usage_observations WHERE task_id=v_current_task.task_id;
  SELECT GREATEST(
      v_current_task.event_limit-count(*) FILTER (WHERE NOT mandatory_cleanup),0
    ) INTO v_remaining_events
    FROM factory.task_events WHERE task_id=v_current_task.task_id;
  SELECT GREATEST(
      (v_packet.body#>>'{limits,infrastructure_retries}')::integer-
      count(*) FILTER (WHERE failure_class IN (
        'database_unavailable','worker_lost','provider_transport_unavailable',
        'temporary_resource_exhaustion'
      )),0
    ) INTO v_remaining_infrastructure_retries
    FROM factory.attempts WHERE task_id=v_current_task.task_id;
  SELECT '[' || COALESCE(string_agg(to_jsonb(value)::text,',' ORDER BY value),'') || ']'
    INTO v_finding_list
    FROM jsonb_array_elements_text(v_verdict.body->'finding_identity_digests') item(value);

  IF v_input->>'writer_id' IS DISTINCT FROM v_subject.owner_id THEN
    v_reason='original_writer_mismatch';
  ELSIF v_cycle NOT BETWEEN 1 AND 3 THEN
    v_reason='repair_cycle_out_of_bounds';
  ELSIF v_previous.child_proposal_digest IS NOT NULL AND (
    v_previous.subject_digest=v_subject.subject_digest
    OR v_previous.body->>'parent_workspace_result_digest'=
      trim(v_subject.workspace_result_digest)
  ) THEN
    v_reason='workspace_result_changed';
  ELSIF v_previous.child_proposal_digest IS NOT NULL
    AND v_previous.body->>'parent_exact_head_sha'=trim(v_subject.exact_head_sha)
  THEN
    v_reason='head_changed';
  ELSIF EXISTS (
    WITH RECURSIVE lineage AS (
      SELECT body,previous_child_proposal_digest
      FROM factory.semantic_child_proposals
      WHERE child_proposal_digest=
        (v_input->>'previous_child_proposal_digest')::char(64)
      UNION ALL
      SELECT prior.body,prior.previous_child_proposal_digest
      FROM factory.semantic_child_proposals prior JOIN lineage child
        ON prior.child_proposal_digest=child.previous_child_proposal_digest
    )
    SELECT 1 FROM lineage,
      jsonb_array_elements_text(lineage.body->'finding_identity_digests') prior(identity)
    JOIN jsonb_array_elements_text(v_verdict.body->'finding_identity_digests') current(identity)
      ON current.identity=prior.identity
  ) THEN
    v_reason='finding_recurrence';
  ELSIF v_input->>'expected_risk_level' IS DISTINCT FROM
      v_subject.subject_body->>'risk_level'
    OR (CASE v_subject.subject_body->>'risk_level'
        WHEN 'low' THEN 0 WHEN 'medium' THEN 1 WHEN 'high' THEN 2 ELSE 3 END
      > (CASE v_baseline_risk
        WHEN 'low' THEN 0 WHEN 'medium' THEN 1 WHEN 'high' THEN 2 ELSE 3 END)) THEN
    v_reason='risk_increased';
  ELSIF (v_subject.subject_body->>'diff_lines')::integer>
      (v_subject.subject_body->>'diff_limit')::integer THEN
    v_reason='diff_limit_exceeded';
  ELSIF v_input->>'expected_diff_digest' IS DISTINCT FROM
      v_subject.subject_body->>'diff_digest' THEN
    v_reason='diff_changed';
  ELSIF v_input->>'expected_architecture_digest' IS DISTINCT FROM
      v_subject.subject_body->>'architecture_digest' THEN
    v_reason='architecture_changed';
  ELSIF v_input->>'expected_authority_digest' IS DISTINCT FROM
      v_subject.subject_body->>'authority_digest' THEN
    v_reason='authority_changed';
  ELSIF v_input->>'expected_base_sha' IS DISTINCT FROM trim(v_subject.exact_base_sha)
  THEN
    v_reason='base_changed';
  ELSIF v_input->>'expected_workspace_result_digest' IS DISTINCT FROM
      trim(v_subject.workspace_result_digest) THEN
    v_reason='workspace_result_changed';
  ELSIF (v_input->>'expected_fence')::bigint<>v_subject.fence THEN
    v_reason='stale_fence';
  ELSIF v_input->>'expected_head_sha' IS DISTINCT FROM trim(v_subject.exact_head_sha)
  THEN
    v_reason='head_changed';
  ELSIF v_result.terminal_stage<>'completed' OR v_result.m4_status<>'ready_for_human'
    OR v_result.failure_class IS NOT NULL OR v_result.failure_reason IS NOT NULL
    OR v_packet.body->>'role'<>'writer'
  THEN
    v_reason='unsupported_result_disposition';
  ELSIF v_budget<=0 OR v_remaining_cost<=0 OR v_remaining_tokens<=0
    OR v_remaining_output<=0 OR v_remaining_events<=0 THEN
    v_reason='budget_exhausted';
  ELSIF v_deadline IS NULL OR v_deadline::timestamptz<=clock_timestamp() THEN
    v_reason='deadline_exhausted';
  ELSIF v_input->>'context_digest' IS NOT DISTINCT FROM
      v_subject.subject_body->>'original_writer_context_digest'
    OR EXISTS (
      WITH RECURSIVE lineage AS (
        SELECT body,previous_child_proposal_digest
        FROM factory.semantic_child_proposals
        WHERE child_proposal_digest=
          (v_input->>'previous_child_proposal_digest')::char(64)
        UNION ALL
        SELECT prior.body,prior.previous_child_proposal_digest
        FROM factory.semantic_child_proposals prior JOIN lineage child
          ON prior.child_proposal_digest=child.previous_child_proposal_digest
      )
      SELECT 1 FROM lineage
      WHERE body->>'context_digest'=v_input->>'context_digest'
    )
  THEN
    v_reason='context_not_fresh';
  ELSIF v_verdict.body->>'decision'<>'repair' THEN
    v_reason='verdict_not_repair';
  END IF;

  SELECT * INTO v_prior FROM factory.semantic_command_results
    WHERE operation='plan_repair' AND idempotency_key=p_idempotency_key;
  IF FOUND THEN
    RETURN CASE WHEN v_prior.request_digest=p_request_digest
      THEN v_prior.response_body ELSE jsonb_build_object('repair_plan_rejection','idempotency_conflict') END;
  END IF;

  IF v_reason IS NOT NULL THEN
    v_escalation_canonical='{"reason":' || to_jsonb(v_reason)::text ||
      ',"request_digest":' || to_jsonb(trim(p_request_digest))::text ||
      ',"requested_cycle":' || v_cycle::text ||
      ',"schema_version":1' ||
      ',"subject_digest":' || to_jsonb(trim(v_subject.subject_digest))::text ||
      ',"verdict_digest":' || to_jsonb(trim(v_verdict.verdict_digest))::text || '}';
    v_escalation=v_escalation_canonical::jsonb;
    v_escalation_digest=factory.execution_contract_hash(NULL,v_escalation_canonical);
    INSERT INTO factory.semantic_escalations(
      escalation_digest,subject_digest,verdict_digest,requested_cycle,reason,
      request_digest,body
    ) VALUES (
      v_escalation_digest,v_subject.subject_digest,v_verdict.verdict_digest,
      v_cycle,v_reason,p_request_digest,v_escalation
    ) ON CONFLICT (escalation_digest) DO NOTHING;
    v_response=jsonb_build_object(
      'decision','needs_human','reason',v_reason,
      'subject_digest',trim(v_subject.subject_digest),
      'verdict_digest',trim(v_verdict.verdict_digest),'cycle',v_cycle,
      'directive_digest',NULL,'directive',NULL,
      'child_proposal_digest',NULL,'child_proposal',NULL,
      'escalation_digest',trim(v_escalation_digest),'escalation',v_escalation
    );
    INSERT INTO factory.semantic_command_results(
      operation,idempotency_key,request_digest,resource_digest,response_body
    ) VALUES (
      'plan_repair',p_idempotency_key,p_request_digest,v_escalation_digest,v_response
    );
    RETURN v_response;
  END IF;

  v_directive_canonical='{"context_digest":' ||
    to_jsonb(v_input->>'context_digest')::text ||
    ',"cycle":' || v_cycle::text ||
    ',"exact_head_sha":' || to_jsonb(trim(v_subject.exact_head_sha))::text ||
    ',"finding_identity_digests":' || v_finding_list ||
    ',"schema_version":1' ||
    ',"subject_digest":' || to_jsonb(trim(v_subject.subject_digest))::text ||
    ',"verdict_digest":' || to_jsonb(trim(v_verdict.verdict_digest))::text ||
    ',"writer_id":' || to_jsonb(v_subject.owner_id)::text || '}';
  v_directive=v_directive_canonical::jsonb;
  v_directive_digest=factory.execution_contract_hash(NULL,v_directive_canonical);
  v_previous_json=COALESCE(
    to_jsonb(v_input->>'previous_child_proposal_digest')::text,'null'
  );
  v_child_canonical='{"architecture_digest":' ||
    to_jsonb(v_subject.subject_body->>'architecture_digest')::text ||
    ',"authority_digest":' || to_jsonb(v_subject.subject_body->>'authority_digest')::text ||
    ',"baseline_risk_level":' || to_jsonb(v_baseline_risk)::text ||
    ',"budget_remaining_units":' || v_budget::text ||
    ',"context_digest":' || to_jsonb(v_input->>'context_digest')::text ||
    ',"cycle":' || v_cycle::text ||
    ',"deadline_at":' || to_jsonb(v_deadline)::text ||
    ',"diff_digest":' || to_jsonb(v_subject.subject_body->>'diff_digest')::text ||
    ',"directive_digest":' || to_jsonb(trim(v_directive_digest))::text ||
    ',"exact_base_sha":' || to_jsonb(trim(v_subject.exact_base_sha))::text ||
    ',"finding_identity_digests":' || v_finding_list ||
    ',"infrastructure_retries_remaining":' ||
      v_remaining_infrastructure_retries::text ||
    ',"max_cost_usd_micros":' || v_remaining_cost::text ||
    ',"max_events":' || v_remaining_events::text ||
    ',"max_output_bytes":' || v_remaining_output::text ||
    ',"max_token_units":' || v_remaining_tokens::text ||
    ',"parent_exact_head_sha":' || to_jsonb(trim(v_subject.exact_head_sha))::text ||
    ',"parent_fence":' || v_subject.fence::text ||
    ',"parent_run_id":' || to_jsonb(v_subject.run_id::text)::text ||
    ',"parent_run_manifest_digest":' || to_jsonb(trim(v_subject.run_manifest_digest))::text ||
    ',"parent_task_id":' || to_jsonb(v_subject.task_id::text)::text ||
    ',"parent_task_packet_digest":' || to_jsonb(trim(v_subject.task_packet_digest))::text ||
    ',"parent_workspace_result_digest":' || to_jsonb(trim(v_subject.workspace_result_digest))::text ||
    ',"previous_child_proposal_digest":' || v_previous_json ||
    ',"proposal_state":"pending_handoff"' ||
    ',"requires_new_semantic_subject":true' ||
    ',"requires_new_workspace_result":true' ||
    ',"schema_version":1' ||
    ',"subject_digest":' || to_jsonb(trim(v_subject.subject_digest))::text ||
    ',"verdict_digest":' || to_jsonb(trim(v_verdict.verdict_digest))::text ||
    ',"writer_id":' || to_jsonb(v_subject.owner_id)::text || '}';
  v_child=v_child_canonical::jsonb;
  v_child_digest=factory.execution_contract_hash(NULL,v_child_canonical);

  SELECT * INTO v_existing_directive FROM factory.semantic_directives
    WHERE directive_digest=v_directive_digest
      OR verdict_digest=v_verdict.verdict_digest;
  IF FOUND AND (
    v_existing_directive.directive_digest<>v_directive_digest
    OR v_existing_directive.subject_digest<>v_subject.subject_digest
    OR v_existing_directive.body IS DISTINCT FROM v_directive
  ) THEN RETURN jsonb_build_object('repair_plan_rejection','directive_conflict'); END IF;
  IF NOT FOUND THEN
    INSERT INTO factory.semantic_directives(
      directive_digest,subject_digest,verdict_digest,request_digest,body
    ) VALUES (
      v_directive_digest,v_subject.subject_digest,v_verdict.verdict_digest,
      p_request_digest,v_directive
    );
  END IF;

  SELECT * INTO v_existing_child FROM factory.semantic_child_proposals
    WHERE child_proposal_digest=v_child_digest
      OR (subject_digest=v_subject.subject_digest AND cycle=v_cycle);
  IF FOUND AND (
    v_existing_child.child_proposal_digest<>v_child_digest
    OR v_existing_child.directive_digest<>v_directive_digest
    OR v_existing_child.body IS DISTINCT FROM v_child
  ) THEN RETURN jsonb_build_object('repair_plan_rejection','child_proposal_conflict'); END IF;
  IF NOT FOUND THEN
    INSERT INTO factory.semantic_child_proposals(
      child_proposal_digest,subject_digest,directive_digest,parent_task_id,
      parent_run_id,parent_fence,cycle,previous_child_proposal_digest,
      proposal_state,request_digest,body
    ) VALUES (
      v_child_digest,v_subject.subject_digest,v_directive_digest,v_subject.task_id,
      v_subject.run_id,v_subject.fence,v_cycle,
      (v_input->>'previous_child_proposal_digest')::char(64),
      'pending_handoff',p_request_digest,v_child
    );
  END IF;

  v_response=jsonb_build_object(
    'decision','repair','reason','repair_allowed',
    'subject_digest',trim(v_subject.subject_digest),
    'verdict_digest',trim(v_verdict.verdict_digest),'cycle',v_cycle,
    'directive_digest',trim(v_directive_digest),'directive',v_directive,
    'child_proposal_digest',trim(v_child_digest),'child_proposal',v_child,
    'escalation_digest',NULL,'escalation',NULL
  );
  INSERT INTO factory.semantic_command_results(
    operation,idempotency_key,request_digest,resource_digest,response_body
  ) VALUES (
    'plan_repair',p_idempotency_key,p_request_digest,v_child_digest,v_response
  );
  RETURN v_response;
EXCEPTION WHEN unique_violation OR check_violation OR foreign_key_violation
  OR invalid_text_representation OR numeric_value_out_of_range OR data_exception THEN
  RETURN jsonb_build_object('repair_plan_rejection','store_operation_rejected');
END;
$$;

REVOKE ALL ON FUNCTION factory.semantic_plan_repair(char,char,text,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION factory.semantic_plan_repair(char,char,text,uuid)
  TO factory_semantic_coordinator;
