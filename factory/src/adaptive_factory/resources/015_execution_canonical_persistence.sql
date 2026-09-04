-- M5 canonical execution persistence is a forward-only overlay on immutable 014.
LOCK TABLE factory.execution_proposals, factory.workspace_results IN ACCESS EXCLUSIVE MODE;

DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM factory.workspace_results) THEN
    RAISE EXCEPTION 'migration 015 refuses legacy finalized workspace rows';
  END IF;
  IF EXISTS (
    SELECT 1 FROM factory.execution_proposals WHERE proposal_kind='artifact'
  ) THEN
    RAISE EXCEPTION 'migration 015 refuses unattested legacy artifact proposals';
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='factory_artifact_attestor') THEN
    CREATE ROLE factory_artifact_attestor NOLOGIN NOINHERIT;
  END IF;
  IF EXISTS (
    SELECT 1 FROM pg_roles r
    WHERE r.rolname IN ('factory_runtime','factory_artifact_attestor')
      AND (
        r.rolcanlogin OR r.rolinherit OR r.rolsuper OR r.rolcreaterole
        OR r.rolcreatedb OR r.rolreplication OR r.rolbypassrls
        OR (
          r.rolname='factory_runtime'
          AND r.rolconfig IS DISTINCT FROM ARRAY['search_path=factory, pg_catalog']::text[]
        )
        OR (
          r.rolname='factory_artifact_attestor'
          AND COALESCE(array_length(r.rolconfig,1),0)<>0
        )
      )
  ) OR EXISTS (
    SELECT 1 FROM pg_auth_members membership
    JOIN pg_roles member ON member.oid=membership.member
    WHERE member.rolname IN ('factory_runtime','factory_artifact_attestor')
  ) OR EXISTS (
    WITH RECURSIVE owner_memberships(roleid) AS (
      SELECT membership.roleid
      FROM pg_auth_members membership
      JOIN pg_roles member ON member.oid=membership.member
      WHERE member.rolname=current_user
      UNION
      SELECT membership.roleid
      FROM pg_auth_members membership
      JOIN owner_memberships inherited ON inherited.roleid=membership.member
    )
    SELECT 1 FROM owner_memberships inherited
    JOIN pg_roles parent ON parent.oid=inherited.roleid
    WHERE parent.rolname IN ('factory_runtime','factory_artifact_attestor')
  ) THEN
    RAISE EXCEPTION 'unsafe capability role topology';
  END IF;
END $$;

CREATE FUNCTION factory.execution_object_has_exact_keys(
  p_value jsonb,
  p_keys text[]
) RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE SET search_path=pg_catalog,factory AS $$
  SELECT CASE
    WHEN p_value IS NULL OR jsonb_typeof(p_value)<>'object' THEN false
    ELSE p_value ?& p_keys
      AND (SELECT count(*) FROM jsonb_object_keys(p_value))=cardinality(p_keys)
  END
$$;

CREATE FUNCTION factory.execution_sorted_unique_identifiers(
  p_value jsonb,
  p_maximum integer
) RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE SET search_path=pg_catalog,factory AS $$
  SELECT CASE
    WHEN p_value IS NULL OR jsonb_typeof(p_value)<>'array'
      OR jsonb_array_length(p_value)>p_maximum
    THEN false
    ELSE NOT EXISTS (
      SELECT 1
      FROM jsonb_array_elements(p_value) WITH ORDINALITY AS item(value,position)
      WHERE jsonb_typeof(value)<>'string'
        OR value#>>'{}'!~'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    ) AND (
      SELECT array_agg(value#>>'{}' ORDER BY position)
      FROM jsonb_array_elements(p_value) WITH ORDINALITY AS item(value,position)
    ) IS NOT DISTINCT FROM (
      SELECT array_agg(value#>>'{}' ORDER BY value#>>'{}')
      FROM jsonb_array_elements(p_value) AS item(value)
    ) AND (
      SELECT count(*)=count(DISTINCT value#>>'{}')
      FROM jsonb_array_elements(p_value) AS item(value)
    )
  END
$$;

CREATE FUNCTION factory.execution_canonical_json(p_value jsonb) RETURNS text
LANGUAGE plpgsql IMMUTABLE STRICT PARALLEL SAFE SET search_path=pg_catalog,factory AS $$
DECLARE
  canonical text;
BEGIN
  CASE jsonb_typeof(p_value)
    WHEN 'object' THEN
      SELECT '{'||COALESCE(string_agg(
        to_jsonb(key)::text||':'||factory.execution_canonical_json(value),
        ',' ORDER BY key
      ),'')||'}'
      INTO canonical
      FROM jsonb_each(p_value);
    WHEN 'array' THEN
      SELECT '['||COALESCE(string_agg(
        factory.execution_canonical_json(value),
        ',' ORDER BY position
      ),'')||']'
      INTO canonical
      FROM jsonb_array_elements(p_value) WITH ORDINALITY AS item(value,position);
    ELSE
      canonical=p_value::text;
  END CASE;
  RETURN canonical;
END;
$$;

CREATE FUNCTION factory.execution_contract_hash(p_domain text,p_value jsonb) RETURNS text
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE SET search_path=pg_catalog,factory AS $$
  SELECT encode(
    sha256(
      convert_to(p_domain,'UTF8')||decode('00','hex')||
        convert_to(factory.execution_canonical_json(p_value),'UTF8')
    ),
    'hex'
  )
$$;

CREATE FUNCTION factory.execution_contract_hash(p_domain text,p_canonical text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE SET search_path=pg_catalog,factory AS $$
  SELECT encode(
    sha256(
      CASE WHEN p_domain IS NULL THEN convert_to(p_canonical,'UTF8')
        ELSE convert_to(p_domain,'UTF8')||decode('00','hex')||convert_to(p_canonical,'UTF8')
      END
    ),
    'hex'
  )
$$;

ALTER TABLE factory.execution_manifests
  ADD CONSTRAINT execution_manifests_manifest_digest_run_id_key
  UNIQUE (manifest_digest,run_id);

ALTER TABLE factory.execution_proposals
  ADD CONSTRAINT execution_proposals_canonical_body_check
    CHECK (octet_length(body::text) <= 1048576),
  ADD CONSTRAINT execution_proposals_run_id_idempotency_key_proposal_kind_key
    UNIQUE (run_id,idempotency_key,proposal_kind);

CREATE TABLE factory.execution_artifact_attestations (
  artifact_attestation_digest char(64) PRIMARY KEY
    CHECK (artifact_attestation_digest ~ '^[0-9a-f]{64}$'),
  task_id uuid NOT NULL,
  run_id uuid NOT NULL,
  packet_digest char(64) NOT NULL,
  producer_sequence bigint NOT NULL CHECK (producer_sequence BETWEEN 1 AND 100000),
  fence bigint NOT NULL CHECK (fence > 0),
  author_role text NOT NULL CHECK (author_role='writer'),
  repository_id text NOT NULL CHECK (octet_length(repository_id) BETWEEN 1 AND 128),
  workspace_handle text NOT NULL CHECK (workspace_handle ~ '^workspace:[0-9a-f]{64}$'),
  artifact_class text NOT NULL CHECK (artifact_class ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'),
  path text NOT NULL CHECK (octet_length(path) BETWEEN 1 AND 1024),
  sha256 char(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  size_bytes bigint NOT NULL CHECK (size_bytes BETWEEN 0 AND 1000000000),
  media_type text NOT NULL CHECK (media_type ~ '^[a-z0-9.+-]+/[a-z0-9.+-]+$'),
  body jsonb NOT NULL CHECK (octet_length(body::text) <= 16384),
  issued_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  consumed_at timestamptz,
  consumed_proposal_digest char(64),
  UNIQUE (run_id,producer_sequence),
  FOREIGN KEY (packet_digest,run_id)
    REFERENCES factory.execution_packets(packet_digest,run_id) ON DELETE RESTRICT,
  FOREIGN KEY (run_id,task_id) REFERENCES factory.runs(run_id,task_id) ON DELETE RESTRICT,
  CHECK ((consumed_at IS NULL) = (consumed_proposal_digest IS NULL)),
  CHECK (consumed_proposal_digest IS NULL OR consumed_proposal_digest ~ '^[0-9a-f]{64}$')
);

ALTER TABLE factory.workspace_results
  ADD COLUMN terminal_proposal_kind text,
  ADD COLUMN m4_status text,
  ADD COLUMN failure_class text,
  ADD COLUMN failure_reason text;

ALTER TABLE factory.workspace_results
  ALTER COLUMN terminal_proposal_kind SET NOT NULL,
  ALTER COLUMN m4_status SET NOT NULL,
  ADD CONSTRAINT workspace_results_terminal_proposal_kind_check
    CHECK (terminal_proposal_kind='terminal'),
  ADD CONSTRAINT workspace_results_m4_status_check
    CHECK (m4_status IN ('ready_for_human','retry','needs_human','dead')),
  ADD CONSTRAINT workspace_results_failure_reason_check
    CHECK (failure_reason IS NULL OR octet_length(failure_reason) BETWEEN 1 AND 4096),
  ADD CONSTRAINT workspace_results_disposition_check CHECK (
    (terminal_stage='completed' AND m4_status='ready_for_human'
      AND failure_class IS NULL AND failure_reason IS NULL)
    OR (terminal_stage='failed' AND m4_status IN ('retry','needs_human','dead')
      AND failure_class IS NOT NULL AND failure_reason IS NOT NULL)
    OR (terminal_stage='needs_human' AND m4_status='needs_human'
      AND failure_class IS NULL AND failure_reason IS NOT NULL)
  ),
  ADD CONSTRAINT workspace_results_run_manifest_digest_run_id_fkey
    FOREIGN KEY (run_manifest_digest,run_id)
    REFERENCES factory.execution_manifests(manifest_digest,run_id) ON DELETE RESTRICT,
  ADD CONSTRAINT workspace_results_terminal_proposal_fkey
    FOREIGN KEY (run_id,terminal_proposal_digest,terminal_proposal_kind)
    REFERENCES factory.execution_proposals(run_id,idempotency_key,proposal_kind)
    ON DELETE RESTRICT;

CREATE OR REPLACE FUNCTION factory.execution_start(
  p_task_id uuid,
  p_run_id uuid,
  p_owner text,
  p_fence bigint,
  p_legacy_packet_digest char(64),
  p_packet_digest char(64),
  p_manifest_digest char(64),
  p_workspace_handle text,
  p_provider_id text,
  p_packet jsonb,
  p_manifest jsonb
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  authoritative_intent jsonb;
  authoritative_repository text;
  authoritative_role text;
  authoritative_intent_digest text;
  authoritative_deadline timestamptz;
  authoritative_deadline_wire text;
  expected_stage_names text[] := ARRAY['prepare','invoke','collect','finalize'];
  expected_stage_owners text[] := ARRAY['broker','adapter','broker','control_plane'];
  stage_wall_seconds bigint;
BEGIN
  IF p_packet IS NULL OR p_manifest IS NULL
    OR octet_length(p_packet::text)>1048576 OR octet_length(p_manifest::text)>65536
    OR p_packet_digest IS NULL OR trim(p_packet_digest)!~'^[0-9a-f]{64}$'
    OR p_manifest_digest IS NULL OR trim(p_manifest_digest)!~'^[0-9a-f]{64}$'
    OR p_legacy_packet_digest IS NULL OR trim(p_legacy_packet_digest)!~'^[0-9a-f]{64}$'
    OR p_workspace_handle IS NULL OR p_workspace_handle!~'^workspace:[0-9a-f]{64}$'
    OR p_provider_id IS NULL OR p_provider_id!~'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
  THEN
    RETURN false;
  END IF;

  IF NOT factory.execution_object_has_exact_keys(p_packet,ARRAY[
      'contract_version','protocol_version','task_id','run_id','owner','fence','role',
      'repository_id','legacy_intent_digest','authority','provider','capability_policy',
      'plan','workspace_handle','acceptance_ids','limits','packet_digest'
    ])
    OR NOT factory.execution_object_has_exact_keys(p_packet->'authority',ARRAY[
      'exact_base_sha','exact_head_sha','route_id','change_id','spec_digest',
      'architecture_digest','governance_digest','policy_digest','prompt_template_digest',
      'role_definition_digest','tool_policy_digest','output_schema_digest'
    ])
    OR NOT factory.execution_object_has_exact_keys(p_packet->'provider',ARRAY[
      'provider_id','adapter_id','adapter_version','adapter_digest','native_version',
      'native_digest','model_id','capabilities','eligible'
    ])
    OR NOT factory.execution_object_has_exact_keys(p_packet->'capability_policy',ARRAY[
      'allowed_paths','allowed_tools','network_destinations','artifact_classes','environment_names'
    ])
    OR NOT factory.execution_object_has_exact_keys(p_packet->'plan',ARRAY['stages'])
    OR NOT factory.execution_object_has_exact_keys(p_packet->'limits',ARRAY[
      'wall_seconds','max_cost_usd_micros','max_token_units','max_output_bytes',
      'max_events','infrastructure_retries','semantic_repairs'
    ])
    OR NOT factory.execution_object_has_exact_keys(p_manifest,ARRAY[
      'contract_version','task_id','run_id','packet_digest','provider_id','adapter_id',
      'native_version','model_id','workspace_handle','deadline','stage','manifest_digest'
    ])
  THEN RETURN false; END IF;

  IF p_packet->>'contract_version'<>'1'
    OR p_packet->>'protocol_version'<>'adaptive-factory.execution/v1'
    OR p_packet->>'task_id' IS NULL OR p_packet->>'task_id'!~'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR p_packet->>'run_id' IS NULL OR p_packet->>'run_id'!~'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR p_packet->>'owner' IS NULL OR p_packet->>'owner'!~'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR jsonb_typeof(p_packet->'fence')<>'number' OR p_packet->>'fence'!~'^[1-9][0-9]*$'
    OR p_packet->>'role' NOT IN ('reader','writer')
    OR p_packet->>'repository_id' IS NULL OR p_packet->>'repository_id'!~'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR p_packet->>'legacy_intent_digest' IS NULL OR p_packet->>'legacy_intent_digest'!~'^[0-9a-f]{64}$'
    OR p_packet->>'workspace_handle' IS NULL OR p_packet->>'workspace_handle'!~'^workspace:[0-9a-f]{64}$'
    OR p_packet->>'packet_digest' IS NULL OR p_packet->>'packet_digest'!~'^[0-9a-f]{64}$'
    OR p_packet->>'packet_digest'<>trim(p_packet_digest)
  THEN RETURN false; END IF;

  IF p_packet#>>'{authority,exact_base_sha}' IS NULL OR p_packet#>>'{authority,exact_base_sha}'!~'^[0-9a-f]{40}$'
    OR p_packet#>>'{authority,exact_head_sha}' IS NULL OR p_packet#>>'{authority,exact_head_sha}'!~'^[0-9a-f]{40}$'
    OR p_packet#>>'{authority,route_id}' IS NULL OR p_packet#>>'{authority,route_id}'!~'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR p_packet#>>'{authority,change_id}' IS NULL OR p_packet#>>'{authority,change_id}'!~'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR EXISTS (
      SELECT 1 FROM unnest(ARRAY[
        p_packet#>>'{authority,spec_digest}',
        p_packet#>>'{authority,architecture_digest}',
        p_packet#>>'{authority,governance_digest}',
        p_packet#>>'{authority,policy_digest}',
        p_packet#>>'{authority,prompt_template_digest}',
        p_packet#>>'{authority,role_definition_digest}',
        p_packet#>>'{authority,tool_policy_digest}',
        p_packet#>>'{authority,output_schema_digest}'
      ]) AS digest_value(value)
      WHERE value IS NULL OR value!~'^[0-9a-f]{64}$'
    )
  THEN RETURN false; END IF;

  IF p_packet#>>'{provider,provider_id}' IS NULL OR p_packet#>>'{provider,provider_id}'!~'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR p_packet#>>'{provider,adapter_id}' IS NULL OR p_packet#>>'{provider,adapter_id}'!~'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR p_packet#>>'{provider,model_id}' IS NULL OR p_packet#>>'{provider,model_id}'!~'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR p_packet#>>'{provider,adapter_version}' IS NULL OR p_packet#>>'{provider,adapter_version}'!~'^[0-9]+(\.[0-9]+){1,2}([-+][A-Za-z0-9.-]+)?$'
    OR p_packet#>>'{provider,native_version}' IS NULL OR p_packet#>>'{provider,native_version}'!~'^[0-9]+(\.[0-9]+){1,2}([-+][A-Za-z0-9.-]+)?$'
    OR p_packet#>>'{provider,adapter_digest}' IS NULL OR p_packet#>>'{provider,adapter_digest}'!~'^[0-9a-f]{64}$'
    OR p_packet#>>'{provider,native_digest}' IS NULL OR p_packet#>>'{provider,native_digest}'!~'^[0-9a-f]{64}$'
    OR p_packet#>'{provider,eligible}'<>'true'::jsonb
    OR NOT factory.execution_sorted_unique_identifiers(p_packet#>'{provider,capabilities}',64)
    OR NOT factory.execution_sorted_unique_identifiers(p_packet#>'{capability_policy,allowed_paths}',64)
    OR NOT factory.execution_sorted_unique_identifiers(p_packet#>'{capability_policy,allowed_tools}',64)
    OR NOT factory.execution_sorted_unique_identifiers(p_packet#>'{capability_policy,artifact_classes}',64)
    OR NOT factory.execution_sorted_unique_identifiers(p_packet#>'{capability_policy,environment_names}',64)
    OR p_packet#>'{capability_policy,network_destinations}'<>'[]'::jsonb
    OR EXISTS (
      SELECT 1 FROM jsonb_array_elements_text(p_packet#>'{capability_policy,allowed_paths}') AS path(value)
      WHERE value~'(^|/)(\.\.|\.git)(/|$)' OR value~'//|/$'
    )
    OR NOT factory.execution_sorted_unique_identifiers(p_packet->'acceptance_ids',64)
  THEN RETURN false; END IF;

  IF jsonb_typeof(p_packet#>'{plan,stages}')<>'array'
    OR jsonb_array_length(p_packet#>'{plan,stages}')<>4
    OR EXISTS (
      SELECT 1
      FROM jsonb_array_elements(p_packet#>'{plan,stages}') WITH ORDINALITY AS stage(value,position)
      WHERE NOT factory.execution_object_has_exact_keys(value,ARRAY['name','owner','wall_seconds'])
        OR value->>'name' IS DISTINCT FROM expected_stage_names[position]
        OR value->>'owner' IS DISTINCT FROM expected_stage_owners[position]
        OR jsonb_typeof(value->'wall_seconds')<>'number'
        OR value->>'wall_seconds'!~'^[1-9][0-9]{0,4}$'
        OR (value->>'wall_seconds')::bigint>14400
    )
    OR EXISTS (
      SELECT 1 FROM jsonb_each(p_packet->'limits') AS item(name,value)
      WHERE jsonb_typeof(value)<>'number' OR value#>>'{}'!~'^(0|[1-9][0-9]*)$'
    )
  THEN RETURN false; END IF;

  IF (p_packet#>>'{limits,wall_seconds}')::bigint>14400
    OR (p_packet#>>'{limits,max_cost_usd_micros}')::bigint>25000000
    OR (p_packet#>>'{limits,max_token_units}')::bigint>2000000
    OR (p_packet#>>'{limits,max_output_bytes}')::bigint>10000000
    OR (p_packet#>>'{limits,max_events}')::bigint>100000
    OR (p_packet#>>'{limits,infrastructure_retries}')::bigint>2
    OR (p_packet#>>'{limits,semantic_repairs}')::bigint NOT BETWEEN 1 AND 3
  THEN RETURN false; END IF;
  SELECT sum((value->>'wall_seconds')::bigint)
    INTO stage_wall_seconds
    FROM jsonb_array_elements(p_packet#>'{plan,stages}') AS stage(value);
  IF stage_wall_seconds>(p_packet#>>'{limits,wall_seconds}')::bigint THEN RETURN false; END IF;

  IF p_manifest->>'contract_version'<>'1'
    OR p_manifest->>'task_id' IS NULL OR p_manifest->>'task_id'!~'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR p_manifest->>'run_id' IS NULL OR p_manifest->>'run_id'!~'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR p_manifest->>'packet_digest' IS NULL OR p_manifest->>'packet_digest'!~'^[0-9a-f]{64}$'
    OR p_manifest->>'provider_id' IS NULL OR p_manifest->>'provider_id'!~'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR p_manifest->>'adapter_id' IS NULL OR p_manifest->>'adapter_id'!~'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR p_manifest->>'native_version' IS NULL OR p_manifest->>'native_version'!~'^[0-9]+(\.[0-9]+){1,2}([-+][A-Za-z0-9.-]+)?$'
    OR p_manifest->>'model_id' IS NULL OR p_manifest->>'model_id'!~'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR p_manifest->>'workspace_handle' IS NULL OR p_manifest->>'workspace_handle'!~'^workspace:[0-9a-f]{64}$'
    OR p_manifest->>'deadline' IS NULL OR p_manifest->>'deadline'!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$'
    OR p_manifest->>'stage'<>'prepared'
    OR p_manifest->>'manifest_digest' IS NULL OR p_manifest->>'manifest_digest'!~'^[0-9a-f]{64}$'
    OR p_manifest->>'manifest_digest'<>trim(p_manifest_digest)
  THEN RETURN false; END IF;

  SELECT i.body,t.repository_id,r.role,trim(i.intent_digest),t.deadline_at,
    regexp_replace(
      to_char(t.deadline_at AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US'),
      '\.000000$',''
    )||'Z'
    INTO authoritative_intent,authoritative_repository,authoritative_role,
      authoritative_intent_digest,authoritative_deadline,authoritative_deadline_wire
  FROM factory.tasks t
    JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
    JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
      AND a.repository_id=t.repository_id AND a.role=r.role
    JOIN factory.accepted_intents i ON i.intent_id=t.intent_id
    WHERE t.task_id=p_task_id AND r.run_id=p_run_id AND r.owner_id=p_owner
      AND r.fence=p_fence AND r.packet_digest=p_legacy_packet_digest
      AND t.packet_digest=p_legacy_packet_digest AND t.current_fence=p_fence
      AND t.state='leased' AND r.state='leased' AND r.released_at IS NULL
      AND a.released_at IS NULL AND r.lease_expires_at>clock_timestamp()
      AND t.deadline_at>clock_timestamp()
    FOR UPDATE OF t,r;
  IF NOT FOUND THEN RETURN false; END IF;

  IF p_packet->>'task_id'<>p_task_id::text
    OR p_packet->>'run_id'<>p_run_id::text
    OR p_packet->>'owner'<>p_owner
    OR (p_packet->>'fence')::bigint<>p_fence
    OR p_packet->>'role'<>authoritative_role
    OR p_packet->>'repository_id'<>authoritative_repository
    OR p_packet->>'legacy_intent_digest'<>authoritative_intent_digest
    OR p_packet->>'workspace_handle'<>p_workspace_handle
    OR p_packet#>>'{provider,provider_id}'<>p_provider_id
    OR p_packet->'acceptance_ids' IS DISTINCT FROM authoritative_intent->'acceptance_ids'
    OR p_packet->'limits' IS DISTINCT FROM authoritative_intent->'limits'
    OR p_packet#>>'{authority,exact_base_sha}' IS DISTINCT FROM authoritative_intent->>'exact_base_sha'
    OR p_packet#>>'{authority,exact_head_sha}' IS DISTINCT FROM authoritative_intent#>>'{governance,exact_head_sha}'
    OR p_packet#>>'{authority,route_id}' IS DISTINCT FROM authoritative_intent->>'route_id'
    OR p_packet#>>'{authority,change_id}' IS DISTINCT FROM authoritative_intent->>'change_id'
    OR p_packet#>>'{authority,spec_digest}' IS DISTINCT FROM authoritative_intent->>'spec_digest'
    OR p_packet#>>'{authority,architecture_digest}' IS DISTINCT FROM authoritative_intent#>>'{architecture,architecture_digest}'
    OR p_packet#>>'{authority,governance_digest}' IS DISTINCT FROM authoritative_intent#>>'{governance,governance_digest}'
    OR p_packet#>>'{authority,policy_digest}' IS DISTINCT FROM authoritative_intent->>'policy_digest'
  THEN RETURN false; END IF;

  IF p_manifest->>'task_id'<>p_task_id::text
    OR p_manifest->>'run_id'<>p_run_id::text
    OR p_manifest->>'packet_digest'<>trim(p_packet_digest)
    OR p_manifest->>'provider_id'<>p_packet#>>'{provider,provider_id}'
    OR p_manifest->>'adapter_id'<>p_packet#>>'{provider,adapter_id}'
    OR p_manifest->>'native_version'<>p_packet#>>'{provider,native_version}'
    OR p_manifest->>'model_id'<>p_packet#>>'{provider,model_id}'
    OR p_manifest->>'workspace_handle'<>p_workspace_handle
    OR p_manifest->>'deadline'<>authoritative_deadline_wire
    OR (p_manifest->>'deadline')::timestamptz<>authoritative_deadline
    OR factory.execution_contract_hash(
      'adaptive-factory.task-packet/v1',p_packet-'packet_digest'
    )<>trim(p_packet_digest)
    OR factory.execution_contract_hash(
      'adaptive-factory.run-manifest/v1',p_manifest-'manifest_digest'
    )<>trim(p_manifest_digest)
  THEN RETURN false; END IF;

  INSERT INTO factory.execution_packets(
    packet_digest,task_id,run_id,legacy_packet_digest,provider_id,body
  ) VALUES (
    p_packet_digest,p_task_id,p_run_id,p_legacy_packet_digest,p_provider_id,p_packet
  );
  INSERT INTO factory.execution_manifests(
    manifest_digest,task_id,run_id,packet_digest,workspace_handle,stage,body
  ) VALUES (
    p_manifest_digest,p_task_id,p_run_id,p_packet_digest,p_workspace_handle,'prepared',p_manifest
  );
  INSERT INTO factory.execution_stage_events(manifest_digest,stage_sequence,stage)
    VALUES (p_manifest_digest,1,'prepared');
  RETURN true;
EXCEPTION WHEN unique_violation OR check_violation OR foreign_key_violation THEN
  RETURN false;
WHEN invalid_text_representation OR numeric_value_out_of_range OR datetime_field_overflow THEN
  RETURN false;
END;
$$;

CREATE OR REPLACE FUNCTION factory.execution_advance(
  p_task_id uuid,
  p_run_id uuid,
  p_owner text,
  p_fence bigint,
  p_legacy_packet_digest char(64),
  p_packet_digest char(64),
  p_stage text
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  current_stage text;
  manifest char(64);
  next_sequence bigint;
BEGIN
  PERFORM 1 FROM factory.tasks t
    JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
    JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
    WHERE t.task_id=p_task_id AND r.run_id=p_run_id AND r.owner_id=p_owner
      AND r.fence=p_fence AND r.packet_digest=p_legacy_packet_digest
      AND t.packet_digest=p_legacy_packet_digest AND t.current_fence=p_fence
      AND t.state='leased' AND r.state='leased' AND r.released_at IS NULL
      AND a.released_at IS NULL AND r.lease_expires_at>clock_timestamp()
      AND t.deadline_at>clock_timestamp()
    FOR UPDATE OF t,r;
  IF NOT FOUND THEN RETURN false; END IF;

  SELECT m.stage,m.manifest_digest INTO current_stage,manifest
    FROM factory.execution_manifests m
    WHERE m.task_id=p_task_id AND m.run_id=p_run_id AND m.packet_digest=p_packet_digest
      AND m.terminal_at IS NULL
    FOR UPDATE;
  IF NOT FOUND THEN RETURN false; END IF;
  IF NOT (
    (current_stage='prepared' AND p_stage='running') OR
    (current_stage='running' AND p_stage='collecting')
  ) THEN RETURN false; END IF;

  SELECT COALESCE(max(stage_sequence),0)+1 INTO next_sequence
    FROM factory.execution_stage_events WHERE manifest_digest=manifest;
  UPDATE factory.execution_manifests SET stage=p_stage,updated_at=clock_timestamp(),
    terminal_at=NULL
    WHERE manifest_digest=manifest;
  INSERT INTO factory.execution_stage_events(manifest_digest,stage_sequence,stage)
    VALUES (manifest,next_sequence,p_stage);
  RETURN true;
END;
$$;

CREATE OR REPLACE FUNCTION factory.execution_propose(
  p_task_id uuid,
  p_run_id uuid,
  p_owner text,
  p_fence bigint,
  p_legacy_packet_digest char(64),
  p_packet_digest char(64),
  p_sequence bigint,
  p_idempotency_key char(64),
  p_kind text,
  p_body jsonb
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_existing_exact boolean;
  v_max_sequence bigint;
  v_max_events bigint;
  v_authoritative_max_events bigint;
  v_role text;
  v_repository_id text;
  v_workspace_handle text;
  v_packet jsonb;
  v_allowed_paths jsonb;
  v_expected_attestation char(64);
  v_expected_key char(64);
  v_canonical text;
  v_evidence text;
  v_secret_pattern CONSTANT text := '(-----BEGIN|-----END|sk-|ghp_|github_pat_|(AKIA|ASIA)[A-Z0-9]{16}|bearer[ \t]+|authorization[ \t]*[=:]|["'']?([a-z0-9]+[_-])*(api[_-]?key|access[_-]?token|session[_-]?token|client[_-]?secret|refresh[_-]?token|password|credential|secret[_-]?key|private[_-]?key|token|secret)([_-][a-z0-9]+)*["'']?[ \t]*[:=])';
BEGIN
  IF current_setting('transaction_isolation') IS DISTINCT FROM 'read committed' THEN
    RETURN false;
  END IF;
  IF p_task_id IS NULL OR p_run_id IS NULL OR p_owner IS NULL OR p_fence IS NULL
    OR p_legacy_packet_digest IS NULL OR p_packet_digest IS NULL OR p_sequence IS NULL
    OR p_idempotency_key IS NULL OR p_kind IS NULL OR p_body IS NULL
    OR jsonb_typeof(p_body) IS DISTINCT FROM 'object'
    OR octet_length(p_body::text)>1048576
    OR p_kind NOT IN ('note','artifact','usage','terminal')
    OR trim(p_idempotency_key)!~'^[0-9a-f]{64}$'
    OR p_sequence NOT BETWEEN 1 AND 100000
  THEN RETURN false; END IF;
  SELECT r.role,t.repository_id,m.workspace_handle,p.body,t.event_limit
    INTO v_role,v_repository_id,v_workspace_handle,v_packet,v_authoritative_max_events
    FROM factory.tasks t
    JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
    JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
      AND a.repository_id=t.repository_id AND a.role=r.role
    JOIN factory.execution_packets p ON p.run_id=r.run_id AND p.task_id=t.task_id
      AND p.packet_digest=p_packet_digest AND p.legacy_packet_digest=p_legacy_packet_digest
    JOIN factory.execution_manifests m ON m.run_id=r.run_id AND m.task_id=t.task_id
      AND m.packet_digest=p.packet_digest
    WHERE t.task_id=p_task_id AND r.run_id=p_run_id AND r.owner_id=p_owner
      AND r.fence=p_fence AND r.packet_digest=p_legacy_packet_digest
      AND t.packet_digest=p_legacy_packet_digest AND t.current_fence=p_fence
      AND t.state='leased' AND r.state='leased'
      AND r.released_at IS NULL AND a.released_at IS NULL
      AND m.terminal_at IS NULL AND r.lease_expires_at>clock_timestamp()
      AND t.deadline_at>clock_timestamp()
    FOR UPDATE OF t,r,m;
  IF NOT FOUND THEN RETURN false; END IF;
  v_max_events=(v_packet#>>'{limits,max_events}')::bigint;
  v_allowed_paths=v_packet#>'{capability_policy,allowed_paths}';
  IF v_max_events IS NULL OR v_max_events NOT BETWEEN 1 AND 100000
    OR v_max_events IS DISTINCT FROM v_authoritative_max_events
    OR jsonb_typeof(v_allowed_paths) IS DISTINCT FROM 'array'
    OR jsonb_typeof(v_packet#>'{provider,capabilities}') IS DISTINCT FROM 'array'
    OR NOT (v_packet#>'{provider,capabilities}' ? CASE p_kind
      WHEN 'note' THEN 'notes' WHEN 'artifact' THEN 'artifacts'
      WHEN 'usage' THEN 'usage' ELSE 'structured_output' END)
    OR p_body->>'task_id' IS DISTINCT FROM p_task_id::text
    OR p_body->>'run_id' IS DISTINCT FROM p_run_id::text
    OR p_body->>'packet_digest' IS DISTINCT FROM trim(p_packet_digest)
    OR p_body->>'fence' IS DISTINCT FROM p_fence::text
    OR p_body->>'sequence' IS DISTINCT FROM p_sequence::text
    OR p_body->>'author_role' IS DISTINCT FROM v_role
    OR p_body->>'idempotency_key' IS DISTINCT FROM trim(p_idempotency_key)
    OR jsonb_typeof(p_body->'task_id') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_body->'run_id') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_body->'packet_digest') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_body->'fence') IS DISTINCT FROM 'number'
    OR jsonb_typeof(p_body->'sequence') IS DISTINCT FROM 'number'
    OR jsonb_typeof(p_body->'author_role') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_body->'idempotency_key') IS DISTINCT FROM 'string'
    OR p_body->>'fence' !~ '^[1-9][0-9]{0,18}$'
    OR p_body->>'sequence' !~ '^[1-9][0-9]{0,5}$'
  THEN RETURN false;
  END IF;

  IF p_kind='note' THEN
    IF NOT (p_body ?& ARRAY[
        'task_id','run_id','packet_digest','fence','sequence','author_role',
        'note_type','body','evidence','idempotency_key'
      ]) OR (SELECT count(*) FROM jsonb_object_keys(p_body))<>10
      OR jsonb_typeof(p_body->'fence') IS DISTINCT FROM 'number'
      OR jsonb_typeof(p_body->'sequence') IS DISTINCT FROM 'number'
      OR jsonb_typeof(p_body->'note_type') IS DISTINCT FROM 'string'
      OR jsonb_typeof(p_body->'body') IS DISTINCT FROM 'string'
      OR jsonb_typeof(p_body->'evidence') IS DISTINCT FROM 'array'
      OR COALESCE(octet_length(p_body->>'note_type'),0) NOT BETWEEN 1 AND 64
      OR p_body->>'note_type' NOT IN ('finding','conclusion','decision.record')
      OR COALESCE(octet_length(p_body->>'body'),0)>
         LEAST(65536,(v_packet#>>'{limits,max_output_bytes}')::bigint)
      OR p_body->>'note_type' ~* v_secret_pattern
      OR p_body->>'body' ~* v_secret_pattern
      OR p_body->>'body' LIKE '#!%' OR p_body->>'body' LIKE E'%\ngit push%'
      OR jsonb_array_length(p_body->'evidence')>64
      OR EXISTS (
        SELECT 1 FROM jsonb_array_elements(p_body->'evidence') item
        WHERE jsonb_typeof(item) IS DISTINCT FROM 'string'
      )
      OR EXISTS (
        SELECT 1 FROM jsonb_array_elements_text(p_body->'evidence') path
        WHERE COALESCE(octet_length(path),0) NOT BETWEEN 1 AND 1024
          OR path LIKE '/%' OR path LIKE '%//%' OR path LIKE '%/'
          OR path ~ '(^|/)(\.|\.\.|\.git)(/|$)'
          OR NOT EXISTS (
            SELECT 1 FROM jsonb_array_elements_text(v_allowed_paths) root
            WHERE path=root OR (
              left(path,length(root))=root AND substr(path,length(root)+1,1)='/'
            )
          )
          OR path ~* v_secret_pattern
      )
    THEN RETURN false; END IF;
    SELECT '[' || COALESCE(string_agg(to_jsonb(value)::text,',' ORDER BY ordinal),'') || ']'
      INTO v_evidence
      FROM jsonb_array_elements_text(p_body->'evidence') WITH ORDINALITY AS e(value,ordinal);
    v_canonical='{"body":' || (p_body->'body')::text ||
      ',"evidence":' || v_evidence ||
      ',"note_type":' || (p_body->'note_type')::text || '}';
  ELSIF p_kind='artifact' THEN
    IF NOT (p_body ?& ARRAY[
        'task_id','run_id','packet_digest','fence','sequence','author_role','artifact_class',
        'path','sha256','size_bytes','media_type','artifact_attestation_digest','idempotency_key'
      ]) OR (SELECT count(*) FROM jsonb_object_keys(p_body))<>13
      OR jsonb_typeof(p_body->'fence') IS DISTINCT FROM 'number'
      OR jsonb_typeof(p_body->'sequence') IS DISTINCT FROM 'number'
      OR jsonb_typeof(p_body->'artifact_class') IS DISTINCT FROM 'string'
      OR jsonb_typeof(p_body->'path') IS DISTINCT FROM 'string'
      OR jsonb_typeof(p_body->'sha256') IS DISTINCT FROM 'string'
      OR jsonb_typeof(p_body->'size_bytes') IS DISTINCT FROM 'number'
      OR jsonb_typeof(p_body->'media_type') IS DISTINCT FROM 'string'
      OR jsonb_typeof(p_body->'artifact_attestation_digest') IS DISTINCT FROM 'string'
      OR p_body->>'sha256' !~ '^[0-9a-f]{64}$'
      OR p_body->>'artifact_attestation_digest' !~ '^[0-9a-f]{64}$'
      OR p_body->>'size_bytes' !~ '^(0|[1-9][0-9]{0,9})$'
      OR (p_body->>'size_bytes')::bigint>(v_packet#>>'{limits,max_output_bytes}')::bigint
      OR p_body->>'media_type' !~ '^[a-z0-9.+-]+/[a-z0-9.+-]+$'
      OR NOT (v_packet#>'{capability_policy,artifact_classes}' ? (p_body->>'artifact_class'))
      OR p_body->>'path'='' OR p_body->>'path' LIKE '/%'
      OR p_body->>'path' LIKE '%//%' OR p_body->>'path' LIKE '%/'
      OR p_body->>'path' ~ '(^|/)(\.|\.\.|\.git)(/|$)'
      OR NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements_text(v_allowed_paths) root
        WHERE p_body->>'path'=root OR (
          left(p_body->>'path',length(root))=root
          AND substr(p_body->>'path',length(root)+1,1)='/'
        )
      )
      OR p_body->>'path' ~* v_secret_pattern
    THEN RETURN false; END IF;
    v_canonical='{"artifact_class":' || (p_body->'artifact_class')::text ||
      ',"author_role":' || to_jsonb(v_role)::text ||
      ',"contract":' || to_jsonb('adaptive-factory.artifact-attestation/v1'::text)::text ||
      ',"contract_version":1' ||
      ',"fence":' || p_fence::text ||
      ',"media_type":' || (p_body->'media_type')::text ||
      ',"packet_digest":' || to_jsonb(trim(p_packet_digest))::text ||
      ',"path":' || (p_body->'path')::text ||
      ',"producer_sequence":' || p_sequence::text ||
      ',"repository_id":' || to_jsonb(v_repository_id)::text ||
      ',"run_id":' || to_jsonb(p_run_id::text)::text ||
      ',"sha256":' || (p_body->'sha256')::text ||
      ',"size_bytes":' || (p_body->>'size_bytes') ||
      ',"source":' || to_jsonb('trusted_workspace_broker'::text)::text ||
      ',"task_id":' || to_jsonb(p_task_id::text)::text ||
      ',"workspace_handle":' || to_jsonb(v_workspace_handle)::text || '}';
    v_expected_attestation=factory.execution_contract_hash(NULL,v_canonical);
    IF p_body->>'artifact_attestation_digest' IS DISTINCT FROM trim(v_expected_attestation)
    THEN RETURN false; END IF;
    v_canonical='{"artifact_attestation_digest":' || (p_body->'artifact_attestation_digest')::text ||
      ',"artifact_class":' || (p_body->'artifact_class')::text ||
      ',"author_role":' || to_jsonb(v_role)::text ||
      ',"media_type":' || (p_body->'media_type')::text ||
      ',"path":' || (p_body->'path')::text ||
      ',"sha256":' || (p_body->'sha256')::text ||
      ',"size_bytes":' || (p_body->>'size_bytes') || '}';
  ELSIF p_kind='usage' THEN
    IF NOT (p_body ?& ARRAY[
        'task_id','run_id','packet_digest','fence','sequence','author_role','provider_call_id',
        'price_table_digest','input_tokens','output_tokens','reasoning_tokens','cost_usd_micros',
        'output_bytes','idempotency_key'
      ]) OR (SELECT count(*) FROM jsonb_object_keys(p_body))<>14
      OR jsonb_typeof(p_body->'provider_call_id') IS DISTINCT FROM 'string'
      OR jsonb_typeof(p_body->'price_table_digest') IS DISTINCT FROM 'string'
      OR p_body->>'price_table_digest' !~ '^[0-9a-f]{64}$'
      OR COALESCE(octet_length(p_body->>'provider_call_id'),0) NOT BETWEEN 1 AND 128
      OR p_body->>'provider_call_id' ~* v_secret_pattern
      OR EXISTS (
        SELECT 1 FROM jsonb_array_elements(jsonb_build_array(
          p_body->'input_tokens',p_body->'output_tokens',p_body->'reasoning_tokens',
          p_body->'cost_usd_micros',p_body->'output_bytes'
        )) value
        WHERE jsonb_typeof(value) IS DISTINCT FROM 'number'
          OR value#>>'{}' !~ '^(0|[1-9][0-9]{0,18})$'
      )
      OR (p_body->>'input_tokens')::numeric+(p_body->>'output_tokens')::numeric+
         (p_body->>'reasoning_tokens')::numeric>(v_packet#>>'{limits,max_token_units}')::numeric
      OR (p_body->>'cost_usd_micros')::numeric>(v_packet#>>'{limits,max_cost_usd_micros}')::numeric
      OR (p_body->>'output_bytes')::numeric>(v_packet#>>'{limits,max_output_bytes}')::numeric
    THEN RETURN false; END IF;
    v_canonical='{"author_role":' || to_jsonb(v_role)::text ||
      ',"cost_usd_micros":' || (p_body->>'cost_usd_micros') ||
      ',"input_tokens":' || (p_body->>'input_tokens') ||
      ',"output_bytes":' || (p_body->>'output_bytes') ||
      ',"output_tokens":' || (p_body->>'output_tokens') ||
      ',"price_table_digest":' || (p_body->'price_table_digest')::text ||
      ',"provider_call_id":' || (p_body->'provider_call_id')::text ||
      ',"reasoning_tokens":' || (p_body->>'reasoning_tokens') || '}';
  ELSE
    IF NOT (p_body ?& ARRAY[
        'task_id','run_id','packet_digest','fence','sequence','author_role','terminal_type',
        'summary','failure_class','reason','diagnostic','idempotency_key'
      ]) OR (SELECT count(*) FROM jsonb_object_keys(p_body))<>12
      OR jsonb_typeof(p_body->'terminal_type') IS DISTINCT FROM 'string'
      OR jsonb_typeof(p_body->'summary') IS DISTINCT FROM 'string'
      OR COALESCE(octet_length(p_body->>'summary'),0) NOT BETWEEN 1 AND
         LEAST(65536,(v_packet#>>'{limits,max_output_bytes}')::bigint)
      OR p_body->>'summary' ~* v_secret_pattern
      OR NOT (
        (p_body->>'terminal_type'='run.completed' AND p_body->'failure_class'='null'::jsonb
          AND p_body->'reason'='null'::jsonb AND p_body->'diagnostic'='null'::jsonb)
        OR (p_body->>'terminal_type'='run.failed'
          AND jsonb_typeof(p_body->'failure_class')='string' AND p_body->'reason'='null'::jsonb
          AND jsonb_typeof(p_body->'diagnostic')='string'
          AND p_body->>'failure_class' IN (
            'database_unavailable','worker_lost','provider_transport_unavailable',
            'temporary_resource_exhaustion','validation','policy','authentication',
            'unsupported_capability','budget','security','stale_input','protocol','provider_quality'
          )
          AND p_body->>'summary'=(p_body->>'failure_class') || ': ' || (p_body->>'diagnostic')
          AND p_body->>'diagnostic'=normalize(p_body->>'diagnostic',NFC)
          AND p_body->>'diagnostic' !~ '[[:cntrl:]]'
          AND COALESCE(octet_length(p_body->>'diagnostic'),0) BETWEEN 1 AND
              LEAST(4096,(v_packet#>>'{limits,max_output_bytes}')::bigint))
        OR (p_body->>'terminal_type'='run.needs_human' AND p_body->'failure_class'='null'::jsonb
          AND jsonb_typeof(p_body->'reason')='string' AND jsonb_typeof(p_body->'diagnostic')='string'
          AND p_body->>'summary'=(p_body->>'reason') || ': ' || (p_body->>'diagnostic')
          AND p_body->>'reason'=normalize(p_body->>'reason',NFC)
          AND p_body->>'reason' !~ '[[:cntrl:]]'
          AND COALESCE(octet_length(p_body->>'reason'),0) BETWEEN 1 AND
              LEAST(4096,(v_packet#>>'{limits,max_output_bytes}')::bigint)
          AND COALESCE(octet_length(p_body->>'diagnostic'),0) BETWEEN 1 AND
              LEAST(65536,(v_packet#>>'{limits,max_output_bytes}')::bigint))
      )
      OR COALESCE(p_body->>'reason','') ~* v_secret_pattern
      OR COALESCE(p_body->>'diagnostic','') ~* v_secret_pattern
    THEN RETURN false; END IF;
    v_canonical='{"author_role":' || to_jsonb(v_role)::text ||
      ',"diagnostic":' || (p_body->'diagnostic')::text ||
      ',"failure_class":' || (p_body->'failure_class')::text ||
      ',"reason":' || (p_body->'reason')::text ||
      ',"summary":' || (p_body->'summary')::text ||
      ',"terminal_type":' || (p_body->'terminal_type')::text || '}';
  END IF;

  v_canonical='{"author_role":' || to_jsonb(v_role)::text ||
    ',"body":' || v_canonical ||
    ',"contract":' || to_jsonb('adaptive-factory.execution-proposal/v1'::text)::text ||
    ',"event_type":' || to_jsonb(CASE p_kind
      WHEN 'note' THEN 'note.proposed' WHEN 'artifact' THEN 'artifact.proposed'
      WHEN 'usage' THEN 'usage.reported' ELSE p_body->>'terminal_type' END)::text ||
    ',"fence":' || p_fence::text ||
    ',"packet_digest":' || to_jsonb(trim(p_packet_digest))::text ||
    ',"run_id":' || to_jsonb(p_run_id::text)::text ||
    ',"sequence":' || p_sequence::text ||
    ',"task_id":' || to_jsonb(p_task_id::text)::text || '}';
  v_expected_key=factory.execution_contract_hash(NULL,v_canonical);
  IF trim(p_idempotency_key) IS DISTINCT FROM trim(v_expected_key)
    OR p_body->>'idempotency_key' IS DISTINCT FROM trim(v_expected_key)
  THEN RETURN false; END IF;

  SELECT task_id=p_task_id AND packet_digest=p_packet_digest
      AND trim(idempotency_key)=trim(p_idempotency_key)
      AND proposal_kind=p_kind AND body=p_body
    INTO v_existing_exact
    FROM factory.execution_proposals
    WHERE run_id=p_run_id AND producer_sequence=p_sequence;
  IF FOUND THEN RETURN v_existing_exact; END IF;
  PERFORM 1 FROM factory.execution_proposals
    WHERE run_id=p_run_id AND idempotency_key=p_idempotency_key;
  IF FOUND THEN RETURN false; END IF;

  IF p_sequence>v_max_events THEN RETURN false; END IF;
  IF EXISTS (
    SELECT 1 FROM factory.execution_proposals
    WHERE run_id=p_run_id AND proposal_kind='terminal'
  ) THEN RETURN false; END IF;
  SELECT producer_sequence
    INTO v_max_sequence
    FROM factory.execution_proposals
    WHERE run_id=p_run_id
    ORDER BY producer_sequence DESC
    LIMIT 1;
  v_max_sequence=COALESCE(v_max_sequence,0);
  IF p_sequence<>v_max_sequence+1 THEN
    RETURN false;
  END IF;

  IF p_kind<>'artifact' AND EXISTS (
    SELECT 1 FROM factory.execution_artifact_attestations a
    WHERE a.run_id=p_run_id AND a.producer_sequence=p_sequence
      AND a.consumed_at IS NULL
  ) THEN
    RETURN false;
  END IF;

  IF p_kind='artifact' THEN
    UPDATE factory.execution_artifact_attestations a
      SET consumed_at=clock_timestamp(),consumed_proposal_digest=p_idempotency_key
      WHERE a.artifact_attestation_digest=v_expected_attestation
        AND a.task_id=p_task_id AND a.run_id=p_run_id
        AND a.packet_digest=p_packet_digest AND a.producer_sequence=p_sequence
        AND a.fence=p_fence AND a.author_role=v_role
        AND a.repository_id=v_repository_id AND a.workspace_handle=v_workspace_handle
        AND a.artifact_class=p_body->>'artifact_class' AND a.path=p_body->>'path'
        AND a.sha256=p_body->>'sha256' AND a.size_bytes=(p_body->>'size_bytes')::bigint
        AND a.media_type=p_body->>'media_type' AND a.consumed_at IS NULL;
    IF NOT FOUND THEN RETURN false; END IF;
  END IF;

  INSERT INTO factory.execution_proposals(
    proposal_id,task_id,run_id,packet_digest,producer_sequence,idempotency_key,proposal_kind,body
  ) VALUES (
    gen_random_uuid(),p_task_id,p_run_id,p_packet_digest,p_sequence,p_idempotency_key,p_kind,p_body
  );
  RETURN true;
END;
$$;

CREATE OR REPLACE FUNCTION factory.execution_proposal_context(
  p_task_id uuid,
  p_run_id uuid,
  p_owner text,
  p_fence bigint,
  p_legacy_packet_digest char(64),
  p_packet_digest char(64)
) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT p.body FROM factory.tasks t
  JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
  JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
  JOIN factory.execution_packets p ON p.run_id=r.run_id AND p.task_id=t.task_id
  JOIN factory.execution_manifests m ON m.run_id=p.run_id AND m.packet_digest=p.packet_digest
  WHERE t.task_id=p_task_id AND r.run_id=p_run_id AND r.owner_id=p_owner
    AND r.fence=p_fence AND r.packet_digest=p_legacy_packet_digest
    AND t.packet_digest=p_legacy_packet_digest AND t.current_fence=p_fence
    AND p.packet_digest=p_packet_digest AND t.state='leased' AND r.state='leased'
    AND r.released_at IS NULL AND a.released_at IS NULL AND m.terminal_at IS NULL
    AND r.lease_expires_at>clock_timestamp() AND t.deadline_at>clock_timestamp()
$$;

CREATE OR REPLACE FUNCTION factory.execution_proposal_by_key(
  p_task_id uuid,p_run_id uuid,p_idempotency_key char(64)
) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT jsonb_build_object(
    'task_id',x.task_id,'run_id',x.run_id,'packet_digest',trim(x.packet_digest),
    'producer_sequence',x.producer_sequence,'proposal_kind',x.proposal_kind,
    'idempotency_key',trim(x.idempotency_key),'body',x.body
  )
  FROM factory.execution_proposals x
  WHERE x.task_id=p_task_id AND x.run_id=p_run_id AND x.idempotency_key=p_idempotency_key
$$;

CREATE OR REPLACE FUNCTION factory.execution_result_for_run(p_task_id uuid,p_run_id uuid) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT jsonb_build_object(
    'result',w.body,
    'snapshot',w.workspace_snapshot,
    'packet',p.body,
    'manifest',m.body,
    'row',jsonb_build_object(
      'workspace_result_digest',trim(w.workspace_result_digest),'task_id',w.task_id,
      'run_id',w.run_id,'task_packet_digest',trim(w.task_packet_digest),
      'run_manifest_digest',trim(w.run_manifest_digest),'exact_head_sha',trim(w.exact_head_sha),
      'workspace_snapshot_digest',trim(w.workspace_snapshot_digest),
      'terminal_stage',w.terminal_stage,
      'terminal_proposal_digest',trim(w.terminal_proposal_digest),
      'terminal_proposal_kind',w.terminal_proposal_kind,
      'artifact_manifest_digest',trim(w.artifact_manifest_digest),
      'note_manifest_digest',trim(w.note_manifest_digest),
      'usage_evidence_digest',trim(w.usage_evidence_digest),
      'diagnostics_digest',trim(w.diagnostics_digest),'m4_status',w.m4_status,
      'failure_class',w.failure_class,'failure_reason',w.failure_reason
    )
  )
  FROM factory.workspace_results w
  JOIN factory.execution_packets p ON p.run_id=w.run_id AND p.packet_digest=w.task_packet_digest
  JOIN factory.execution_manifests m ON m.run_id=w.run_id AND m.manifest_digest=w.run_manifest_digest
  WHERE w.task_id=p_task_id AND w.run_id=p_run_id
$$;

CREATE OR REPLACE FUNCTION factory.execution_m4_status(
  p_task_id uuid,p_run_id uuid,p_terminal_type text,p_failure_class text,p_attempt_no bigint
) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_status text;
  v_accounting_blocked boolean;
  v_reserved_cost bigint;
  v_reserved_tokens bigint;
  v_reserved_wall bigint;
  v_has_usage boolean;
  v_has_reservation boolean;
  v_event_limit bigint;
  v_ordinary_events bigint;
  v_infrastructure_retries smallint;
BEGIN
  SELECT t.accounting_blocked,t.cost_reserved_micros,t.tokens_reserved,
    t.wall_reserved_seconds,
    EXISTS(
      SELECT 1 FROM factory.usage_observations u
      WHERE u.task_id=p_task_id AND u.run_id=p_run_id
    ),
    EXISTS(
      SELECT 1 FROM factory.budget_reservations b
      WHERE b.task_id=p_task_id AND b.run_id=p_run_id AND b.released_at IS NULL
    ),
    t.event_limit,
    (
      SELECT count(*) FROM factory.task_events e
      WHERE e.task_id=p_task_id AND NOT e.mandatory_cleanup
    ),
    t.infrastructure_retries
    INTO v_accounting_blocked,v_reserved_cost,v_reserved_tokens,v_reserved_wall,
      v_has_usage,v_has_reservation,v_event_limit,v_ordinary_events,
      v_infrastructure_retries
    FROM factory.tasks t WHERE t.task_id=p_task_id;
  IF NOT FOUND OR p_attempt_no<1 OR v_infrastructure_retries NOT BETWEEN 0 AND 2
  THEN RETURN NULL; END IF;
  IF p_terminal_type='run.completed' THEN
    IF v_accounting_blocked OR NOT v_has_usage OR v_has_reservation
      OR v_reserved_cost<>0 OR v_reserved_tokens<>0 OR v_reserved_wall<>0
    THEN RETURN NULL; END IF;
    RETURN 'ready_for_human';
  END IF;
  IF p_terminal_type NOT IN ('run.failed','run.needs_human') THEN RETURN NULL; END IF;
  IF v_accounting_blocked OR v_reserved_cost<>0 OR v_reserved_tokens<>0
    OR v_reserved_wall<>0
  THEN RETURN 'needs_human'; END IF;
  IF p_terminal_type='run.needs_human' THEN RETURN 'needs_human'; END IF;
  IF p_failure_class IN (
    'database_unavailable','worker_lost','provider_transport_unavailable',
    'temporary_resource_exhaustion'
  ) THEN
    v_status=CASE WHEN p_attempt_no>v_infrastructure_retries THEN 'dead' ELSE 'retry' END;
  ELSIF p_failure_class IN (
    'validation','policy','authentication','unsupported_capability','budget','security',
    'stale_input','protocol','provider_quality'
  ) THEN
    v_status='needs_human';
  ELSE
    RETURN NULL;
  END IF;
  IF v_has_reservation OR (v_status='retry' AND v_ordinary_events>=v_event_limit) THEN
    RETURN 'needs_human';
  END IF;
  RETURN v_status;
END;
$$;

CREATE OR REPLACE FUNCTION factory.execution_record_artifact_attestation(p_request jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_packet jsonb;
  v_repository_id text;
  v_workspace_handle text;
  v_role text;
  v_fence bigint;
  v_digest char(64);
  v_body jsonb;
  v_canonical text;
  v_existing jsonb;
  v_max_sequence bigint;
  v_max_events bigint;
  v_authoritative_max_events bigint;
  v_secret_pattern CONSTANT text := '(-----BEGIN|-----END|sk-|ghp_|github_pat_|(AKIA|ASIA)[A-Z0-9]{16}|bearer[ \t]+|authorization[ \t]*[=:]|["'']?([a-z0-9]+[_-])*(api[_-]?key|access[_-]?token|session[_-]?token|client[_-]?secret|refresh[_-]?token|password|credential|secret[_-]?key|private[_-]?key|token|secret)([_-][a-z0-9]+)*["'']?[ \t]*[:=])';
BEGIN
  IF current_setting('transaction_isolation') IS DISTINCT FROM 'read committed' THEN
    RETURN NULL;
  END IF;
  IF p_request IS NULL OR jsonb_typeof(p_request) IS DISTINCT FROM 'object'
    OR NOT (p_request ?& ARRAY[
      'task_id','run_id','repository_id','packet_digest','workspace_handle',
      'producer_sequence','fence','author_role','artifact_class','path','sha256',
      'size_bytes','media_type','contract_version','source','artifact_attestation_digest'
    ]) OR (SELECT count(*) FROM jsonb_object_keys(p_request))<>16
    OR p_request->'contract_version' IS DISTINCT FROM '1'::jsonb
    OR p_request->>'source' IS DISTINCT FROM 'trusted_workspace_broker'
    OR jsonb_typeof(p_request->'artifact_attestation_digest') IS DISTINCT FROM 'string'
    OR p_request->>'artifact_attestation_digest' !~ '^[0-9a-f]{64}$'
    OR jsonb_typeof(p_request->'task_id') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_request->'run_id') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_request->'repository_id') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_request->'packet_digest') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_request->'workspace_handle') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_request->'producer_sequence') IS DISTINCT FROM 'number'
    OR jsonb_typeof(p_request->'fence') IS DISTINCT FROM 'number'
    OR jsonb_typeof(p_request->'author_role') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_request->'artifact_class') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_request->'path') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_request->'sha256') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_request->'size_bytes') IS DISTINCT FROM 'number'
    OR jsonb_typeof(p_request->'media_type') IS DISTINCT FROM 'string'
    OR p_request->>'task_id' !~ '^[0-9a-f-]{36}$'
    OR p_request->>'run_id' !~ '^[0-9a-f-]{36}$'
    OR NOT pg_input_is_valid(p_request->>'task_id','uuid')
    OR NOT pg_input_is_valid(p_request->>'run_id','uuid')
    OR p_request->>'packet_digest' !~ '^[0-9a-f]{64}$'
    OR p_request->>'producer_sequence' !~ '^[1-9][0-9]{0,5}$'
    OR p_request->>'fence' !~ '^[1-9][0-9]{0,18}$'
    OR p_request->>'size_bytes' !~ '^(0|[1-9][0-9]{0,9})$'
    OR NOT pg_input_is_valid(p_request->>'producer_sequence','bigint')
    OR NOT pg_input_is_valid(p_request->>'fence','bigint')
    OR NOT pg_input_is_valid(p_request->>'size_bytes','bigint')
    OR p_request->>'sha256' !~ '^[0-9a-f]{64}$'
    OR p_request->>'media_type' !~ '^[a-z0-9.+-]+/[a-z0-9.+-]+$'
    OR COALESCE(octet_length(p_request->>'path'),0) NOT BETWEEN 1 AND 1024
    OR p_request->>'path' LIKE '/%' OR p_request->>'path' LIKE '%//%'
    OR p_request->>'path' LIKE '%/' OR p_request->>'path' ~ '(^|/)(\.|\.\.|\.git)(/|$)'
    OR p_request->>'path' ~* v_secret_pattern
  THEN RETURN NULL; END IF;

  -- Exact attestation replay is a read of already-authorized durable evidence.
  -- It remains available after finalization; every changed field fails closed.
  SELECT body INTO v_existing FROM factory.execution_artifact_attestations
    WHERE run_id=(p_request->>'run_id')::uuid
      AND producer_sequence=(p_request->>'producer_sequence')::bigint;
  IF FOUND THEN
    RETURN CASE WHEN v_existing=p_request THEN v_existing ELSE NULL END;
  END IF;

  SELECT p.body,t.repository_id,m.workspace_handle,r.role,r.fence,t.event_limit
    INTO v_packet,v_repository_id,v_workspace_handle,v_role,v_fence,
      v_authoritative_max_events
    FROM factory.tasks t
    JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
    JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
      AND a.repository_id=t.repository_id AND a.role=r.role
    JOIN factory.execution_packets p ON p.run_id=r.run_id AND p.task_id=t.task_id
    JOIN factory.execution_manifests m ON m.run_id=r.run_id AND m.task_id=t.task_id
      AND m.packet_digest=p.packet_digest
    WHERE t.task_id=(p_request->>'task_id')::uuid
      AND r.run_id=(p_request->>'run_id')::uuid
      AND p.packet_digest=p_request->>'packet_digest'
      AND t.state='leased' AND r.state='leased' AND r.released_at IS NULL
      AND a.released_at IS NULL AND m.terminal_at IS NULL
      AND r.lease_expires_at>clock_timestamp() AND t.deadline_at>clock_timestamp()
    FOR UPDATE OF t,r,m;
  IF NOT FOUND
    OR p_request->>'repository_id' IS DISTINCT FROM v_repository_id
    OR p_request->>'workspace_handle' IS DISTINCT FROM v_workspace_handle
    OR p_request->>'author_role' IS DISTINCT FROM v_role OR v_role IS DISTINCT FROM 'writer'
    OR (p_request->>'fence')::bigint IS DISTINCT FROM v_fence
    OR NOT (v_packet#>'{provider,capabilities}' ? 'artifacts')
    OR NOT (v_packet#>'{capability_policy,artifact_classes}' ? (p_request->>'artifact_class'))
    OR (p_request->>'size_bytes')::bigint>(v_packet#>>'{limits,max_output_bytes}')::bigint
    OR NOT EXISTS (
      SELECT 1 FROM jsonb_array_elements_text(v_packet#>'{capability_policy,allowed_paths}') root
      WHERE p_request->>'path'=root OR (
        left(p_request->>'path',length(root))=root
        AND substr(p_request->>'path',length(root)+1,1)='/'
      )
    )
  THEN RETURN NULL; END IF;

  v_canonical='{"artifact_class":' || (p_request->'artifact_class')::text ||
    ',"author_role":' || to_jsonb(v_role)::text ||
    ',"contract":' || to_jsonb('adaptive-factory.artifact-attestation/v1'::text)::text ||
    ',"contract_version":1' ||
    ',"fence":' || v_fence::text ||
    ',"media_type":' || (p_request->'media_type')::text ||
    ',"packet_digest":' || (p_request->'packet_digest')::text ||
    ',"path":' || (p_request->'path')::text ||
    ',"producer_sequence":' || (p_request->>'producer_sequence') ||
    ',"repository_id":' || to_jsonb(v_repository_id)::text ||
    ',"run_id":' || (p_request->'run_id')::text ||
    ',"sha256":' || (p_request->'sha256')::text ||
    ',"size_bytes":' || (p_request->>'size_bytes') ||
    ',"source":' || to_jsonb('trusted_workspace_broker'::text)::text ||
    ',"task_id":' || (p_request->'task_id')::text ||
    ',"workspace_handle":' || to_jsonb(v_workspace_handle)::text || '}';
  v_digest=factory.execution_contract_hash(NULL,v_canonical);
  IF p_request->>'artifact_attestation_digest' IS DISTINCT FROM trim(v_digest) THEN
    RETURN NULL;
  END IF;
  v_body=jsonb_build_object(
    'contract_version',1,'task_id',p_request->>'task_id','run_id',p_request->>'run_id',
    'repository_id',v_repository_id,'packet_digest',p_request->>'packet_digest',
    'workspace_handle',v_workspace_handle,'producer_sequence',(p_request->>'producer_sequence')::bigint,
    'fence',v_fence,'author_role',v_role,'artifact_class',p_request->>'artifact_class',
    'path',p_request->>'path','sha256',p_request->>'sha256',
    'size_bytes',(p_request->>'size_bytes')::bigint,'media_type',p_request->>'media_type',
    'source','trusted_workspace_broker','artifact_attestation_digest',trim(v_digest)
  );
  v_max_events=(v_packet#>>'{limits,max_events}')::bigint;
  IF v_max_events IS NULL OR v_max_events NOT BETWEEN 1 AND 100000
    OR v_max_events IS DISTINCT FROM v_authoritative_max_events
    OR (p_request->>'producer_sequence')::bigint>v_max_events
  THEN RETURN NULL; END IF;
  IF EXISTS (
    SELECT 1 FROM factory.execution_proposals
    WHERE run_id=(p_request->>'run_id')::uuid AND proposal_kind='terminal'
  ) THEN RETURN NULL; END IF;
  SELECT producer_sequence INTO v_max_sequence
    FROM factory.execution_proposals
    WHERE run_id=(p_request->>'run_id')::uuid
    ORDER BY producer_sequence DESC
    LIMIT 1;
  v_max_sequence=COALESCE(v_max_sequence,0);
  IF (p_request->>'producer_sequence')::bigint<>v_max_sequence+1 THEN RETURN NULL; END IF;
  INSERT INTO factory.execution_artifact_attestations(
    artifact_attestation_digest,task_id,run_id,packet_digest,producer_sequence,fence,
    author_role,repository_id,workspace_handle,artifact_class,path,sha256,size_bytes,media_type,body
  ) VALUES (
    v_digest,(p_request->>'task_id')::uuid,(p_request->>'run_id')::uuid,
    (p_request->>'packet_digest')::char(64),(p_request->>'producer_sequence')::bigint,
    v_fence,v_role,v_repository_id,v_workspace_handle,p_request->>'artifact_class',
    p_request->>'path',(p_request->>'sha256')::char(64),(p_request->>'size_bytes')::bigint,
    p_request->>'media_type',v_body
  );
  RETURN v_body;
END;
$$;


CREATE OR REPLACE FUNCTION factory.execution_result_by_digest(
  p_task_id uuid,p_workspace_result_digest char(64)
) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT jsonb_build_object(
    'result',w.body,
    'snapshot',w.workspace_snapshot,
    'packet',p.body,
    'manifest',m.body,
    'row',jsonb_build_object(
      'workspace_result_digest',trim(w.workspace_result_digest),'task_id',w.task_id,
      'run_id',w.run_id,'task_packet_digest',trim(w.task_packet_digest),
      'run_manifest_digest',trim(w.run_manifest_digest),'exact_head_sha',trim(w.exact_head_sha),
      'workspace_snapshot_digest',trim(w.workspace_snapshot_digest),
      'terminal_stage',w.terminal_stage,
      'terminal_proposal_digest',trim(w.terminal_proposal_digest),
      'terminal_proposal_kind',w.terminal_proposal_kind,
      'artifact_manifest_digest',trim(w.artifact_manifest_digest),
      'note_manifest_digest',trim(w.note_manifest_digest),
      'usage_evidence_digest',trim(w.usage_evidence_digest),
      'diagnostics_digest',trim(w.diagnostics_digest),'m4_status',w.m4_status,
      'failure_class',w.failure_class,'failure_reason',w.failure_reason
    )
  )
  FROM factory.workspace_results w
  JOIN factory.execution_packets p ON p.run_id=w.run_id AND p.packet_digest=w.task_packet_digest
  JOIN factory.execution_manifests m ON m.run_id=w.run_id AND m.manifest_digest=w.run_manifest_digest
  WHERE w.task_id=p_task_id AND w.workspace_result_digest=p_workspace_result_digest
$$;

CREATE OR REPLACE FUNCTION factory.execution_finalize_context(
  p_task_id uuid,
  p_run_id uuid,
  p_owner text,
  p_fence bigint,
  p_legacy_packet_digest char(64),
  p_packet_digest char(64)
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  result jsonb;
  v_terminal_sequence bigint;
  v_max_events bigint;
  v_authoritative_max_events bigint;
BEGIN
  IF NOT factory.capacity_lock_run(p_run_id) THEN RETURN NULL; END IF;
  PERFORM 1 FROM factory.tasks t
    JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
    JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
    JOIN factory.execution_packets p ON p.run_id=r.run_id AND p.task_id=t.task_id
    JOIN factory.execution_manifests m ON m.run_id=p.run_id AND m.packet_digest=p.packet_digest
    WHERE t.task_id=p_task_id AND r.run_id=p_run_id AND r.owner_id=p_owner
      AND r.fence=p_fence AND r.packet_digest=p_legacy_packet_digest
      AND t.packet_digest=p_legacy_packet_digest AND t.current_fence=p_fence
      AND p.packet_digest=p_packet_digest AND t.state='leased' AND r.state='leased'
      AND r.released_at IS NULL AND a.released_at IS NULL AND m.terminal_at IS NULL
      AND r.lease_expires_at>clock_timestamp() AND t.deadline_at>clock_timestamp()
    FOR UPDATE OF t,r,m;
  IF NOT FOUND THEN RETURN NULL; END IF;
  SELECT jsonb_build_object(
    'repository_id',t.repository_id,
    'workspace_handle',m.workspace_handle,
    'input_head_sha',p.body#>>'{authority,exact_head_sha}',
    'run_manifest_digest',m.manifest_digest,
    'terminal_stage',CASE terminal.body->>'terminal_type'
      WHEN 'run.completed' THEN 'completed'
      WHEN 'run.failed' THEN 'failed'
      WHEN 'run.needs_human' THEN 'needs_human'
      ELSE NULL END,
    'm4_status',factory.execution_m4_status(
      p_task_id,p_run_id,terminal.body->>'terminal_type',
      terminal.body->>'failure_class',attempt.attempt_no
    ),
    'failure_class',CASE WHEN terminal.body->>'terminal_type'='run.failed'
      THEN terminal.body->>'failure_class' ELSE NULL END,
    'failure_reason',CASE terminal.body->>'terminal_type'
      WHEN 'run.failed' THEN terminal.body->>'diagnostic'
      WHEN 'run.needs_human' THEN terminal.body->>'reason'
      ELSE NULL END,
    'terminal_proposal_digest',trim(terminal.idempotency_key),
    'artifact_digests',COALESCE((SELECT jsonb_agg(trim(x.idempotency_key) ORDER BY trim(x.idempotency_key)) FROM factory.execution_proposals x WHERE x.run_id=p_run_id AND x.proposal_kind='artifact'),'[]'::jsonb),
    'note_digests',COALESCE((SELECT jsonb_agg(trim(x.idempotency_key) ORDER BY trim(x.idempotency_key)) FROM factory.execution_proposals x WHERE x.run_id=p_run_id AND x.proposal_kind='note'),'[]'::jsonb),
    'usage_digests',COALESCE((SELECT jsonb_agg(trim(x.idempotency_key) ORDER BY trim(x.idempotency_key)) FROM factory.execution_proposals x WHERE x.run_id=p_run_id AND x.proposal_kind='usage'),'[]'::jsonb),
    'diagnostic_digests','[]'::jsonb
  ),terminal.producer_sequence,(p.body#>>'{limits,max_events}')::bigint,t.event_limit
    INTO result,v_terminal_sequence,v_max_events,v_authoritative_max_events
  FROM factory.tasks t
  JOIN factory.execution_packets p ON p.task_id=t.task_id AND p.run_id=p_run_id AND p.packet_digest=p_packet_digest
  JOIN factory.execution_manifests m ON m.run_id=p.run_id AND m.packet_digest=p.packet_digest
  JOIN factory.attempts attempt ON attempt.run_id=p.run_id
  JOIN factory.execution_proposals terminal ON terminal.run_id=p.run_id AND terminal.proposal_kind='terminal'
  WHERE t.task_id=p_task_id;
  IF result->>'terminal_stage' IS NULL OR result->>'m4_status' IS NULL
    OR v_max_events NOT BETWEEN 1 AND 100000
    OR v_max_events IS DISTINCT FROM v_authoritative_max_events
    OR v_terminal_sequence>v_max_events
  THEN RETURN NULL; END IF;
  IF result->>'terminal_stage'='failed' AND (
    result->>'failure_class' NOT IN (
      'database_unavailable','worker_lost','provider_transport_unavailable',
      'temporary_resource_exhaustion','validation','policy','authentication',
      'unsupported_capability','budget','security','stale_input','protocol','provider_quality'
    ) OR COALESCE(octet_length(result->>'failure_reason'),0) NOT BETWEEN 1 AND 4096
  ) THEN RETURN NULL; END IF;
  IF result->>'terminal_stage'='needs_human'
    AND COALESCE(octet_length(result->>'failure_reason'),0) NOT BETWEEN 1 AND 4096
  THEN RETURN NULL; END IF;
  IF EXISTS (
    SELECT 1 FROM factory.execution_proposals proposal
    LEFT JOIN factory.execution_artifact_attestations attestation
      ON attestation.run_id=proposal.run_id
      AND attestation.producer_sequence=proposal.producer_sequence
      AND attestation.consumed_proposal_digest=proposal.idempotency_key
    WHERE proposal.run_id=p_run_id AND proposal.proposal_kind='artifact'
      AND (
        attestation.artifact_attestation_digest IS NULL
        OR attestation.consumed_at IS NULL
        OR trim(attestation.artifact_attestation_digest)
          IS DISTINCT FROM proposal.body->>'artifact_attestation_digest'
        OR attestation.task_id IS DISTINCT FROM proposal.task_id
        OR attestation.packet_digest IS DISTINCT FROM proposal.packet_digest
        OR attestation.author_role IS DISTINCT FROM proposal.body->>'author_role'
        OR attestation.artifact_class IS DISTINCT FROM proposal.body->>'artifact_class'
        OR attestation.path IS DISTINCT FROM proposal.body->>'path'
        OR trim(attestation.sha256) IS DISTINCT FROM proposal.body->>'sha256'
        OR attestation.size_bytes::text IS DISTINCT FROM proposal.body->>'size_bytes'
        OR attestation.media_type IS DISTINCT FROM proposal.body->>'media_type'
      )
  ) THEN RETURN NULL; END IF;
  IF EXISTS (
    SELECT 1 FROM factory.execution_proposals proposal
    LEFT JOIN factory.usage_observations usage
      ON usage.run_id=proposal.run_id
      AND usage.provider_call_id=proposal.body->>'provider_call_id'
    WHERE proposal.run_id=p_run_id AND proposal.proposal_kind='usage'
      AND (
        usage.observation_id IS NULL
        OR usage.task_id IS DISTINCT FROM proposal.task_id
        OR trim(usage.price_table_digest) IS DISTINCT FROM proposal.body->>'price_table_digest'
        OR usage.cost_usd_micros::text IS DISTINCT FROM proposal.body->>'cost_usd_micros'
        OR usage.token_units IS DISTINCT FROM (
          (proposal.body->>'input_tokens')::bigint
          +(proposal.body->>'output_tokens')::bigint
          +(proposal.body->>'reasoning_tokens')::bigint
        )
        OR usage.output_bytes::text IS DISTINCT FROM proposal.body->>'output_bytes'
      )
  ) OR EXISTS (
    SELECT 1 FROM factory.usage_observations usage
    WHERE usage.run_id=p_run_id AND NOT EXISTS (
      SELECT 1 FROM factory.execution_proposals proposal
      WHERE proposal.run_id=usage.run_id AND proposal.proposal_kind='usage'
        AND proposal.body->>'provider_call_id'=usage.provider_call_id
    )
  ) OR EXISTS (
    SELECT 1 FROM factory.execution_proposals proposal
    WHERE proposal.run_id=p_run_id AND proposal.proposal_kind='usage'
    GROUP BY proposal.body->>'provider_call_id' HAVING count(*)<>1
  ) THEN RETURN NULL; END IF;
  RETURN result;
END;
$$;

CREATE OR REPLACE FUNCTION factory.execution_finalize_commit(
  p_task_id uuid,
  p_run_id uuid,
  p_owner text,
  p_fence bigint,
  p_legacy_packet_digest char(64),
  p_packet_digest char(64),
  p_workspace_result_digest char(64),
  p_snapshot jsonb,
  p_result jsonb
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  current_stage text;
  v_manifest_digest char(64);
  manifest_workspace text;
  repository text;
  input_head text;
  terminal_type text;
  terminal_digest char(64);
  target_stage text;
  target_m4_status text;
  terminal_failure_class text;
  terminal_failure_reason text;
  v_context jsonb;
  v_artifact_digest text;
  v_note_digest text;
  v_usage_digest text;
  v_diagnostics_digest text;
  v_snapshot_digest text;
  v_result_digest text;
  v_snapshot_facts jsonb;
  v_expected_result jsonb;
  next_sequence bigint;
BEGIN
  IF jsonb_typeof(p_snapshot) IS DISTINCT FROM 'object'
    OR jsonb_typeof(p_result) IS DISTINCT FROM 'object'
    OR octet_length(p_snapshot::text)>65536 OR octet_length(p_result::text)>65536
  THEN RETURN false; END IF;
  v_context=factory.execution_finalize_context(
    p_task_id,p_run_id,p_owner,p_fence,p_legacy_packet_digest,p_packet_digest
  );
  IF v_context IS NULL THEN RETURN false; END IF;
  SELECT m.stage,m.manifest_digest,m.workspace_handle,t.repository_id,
    p.body#>>'{authority,exact_head_sha}',terminal.body->>'terminal_type',
    terminal.idempotency_key
    INTO current_stage,v_manifest_digest,manifest_workspace,repository,input_head,
      terminal_type,terminal_digest
  FROM factory.tasks t
  JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
  JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
  JOIN factory.execution_packets p ON p.run_id=r.run_id AND p.task_id=t.task_id
  JOIN factory.execution_manifests m ON m.run_id=p.run_id AND m.packet_digest=p.packet_digest
  JOIN factory.execution_proposals terminal ON terminal.run_id=p.run_id AND terminal.proposal_kind='terminal'
  WHERE t.task_id=p_task_id AND r.run_id=p_run_id AND r.owner_id=p_owner
    AND r.fence=p_fence AND r.packet_digest=p_legacy_packet_digest
    AND t.packet_digest=p_legacy_packet_digest AND t.current_fence=p_fence
    AND p.packet_digest=p_packet_digest AND t.state='leased' AND r.state='leased'
    AND r.released_at IS NULL AND a.released_at IS NULL AND m.terminal_at IS NULL
    AND r.lease_expires_at>clock_timestamp() AND t.deadline_at>clock_timestamp()
  FOR UPDATE OF t,r,m,terminal;
  IF NOT FOUND THEN RETURN false; END IF;
  target_stage=v_context->>'terminal_stage';
  target_m4_status=v_context->>'m4_status';
  terminal_failure_class=v_context->>'failure_class';
  terminal_failure_reason=v_context->>'failure_reason';
  IF target_stage IS NULL OR target_m4_status IS NULL
    OR (target_stage='completed' AND current_stage<>'collecting')
    OR v_context->>'run_manifest_digest' IS DISTINCT FROM trim(v_manifest_digest)
    OR v_context->>'terminal_proposal_digest' IS DISTINCT FROM trim(terminal_digest)
  THEN RETURN false; END IF;
  SELECT factory.execution_contract_hash(
    'adaptive-factory.workspace-artifacts/v1',
    COALESCE(jsonb_agg(trim(proposal.idempotency_key) ORDER BY trim(proposal.idempotency_key)),
      '[]'::jsonb)
  ) INTO v_artifact_digest FROM factory.execution_proposals proposal
    WHERE proposal.run_id=p_run_id AND proposal.proposal_kind='artifact';
  SELECT factory.execution_contract_hash(
    'adaptive-factory.workspace-notes/v1',
    COALESCE(jsonb_agg(trim(proposal.idempotency_key) ORDER BY trim(proposal.idempotency_key)),
      '[]'::jsonb)
  ) INTO v_note_digest FROM factory.execution_proposals proposal
    WHERE proposal.run_id=p_run_id AND proposal.proposal_kind='note';
  SELECT factory.execution_contract_hash(
    'adaptive-factory.workspace-usage/v1',
    COALESCE(jsonb_agg(trim(proposal.idempotency_key) ORDER BY trim(proposal.idempotency_key)),
      '[]'::jsonb)
  ) INTO v_usage_digest FROM factory.execution_proposals proposal
    WHERE proposal.run_id=p_run_id AND proposal.proposal_kind='usage';
  v_diagnostics_digest=factory.execution_contract_hash(
    'adaptive-factory.workspace-diagnostics/v1','[]'::jsonb
  );
  IF NOT factory.execution_object_has_exact_keys(p_snapshot,ARRAY[
      'contract_version','repository_id','workspace_handle','input_head_sha','result_head_sha',
      'diff_digest','diff_lines','source','workspace_snapshot_digest'
    ]) OR p_snapshot->'contract_version' IS DISTINCT FROM '1'::jsonb
    OR jsonb_typeof(p_snapshot->'diff_lines') IS DISTINCT FROM 'number'
    OR p_snapshot->>'diff_lines' !~ '^(0|[1-9][0-9]{0,6})$'
    OR (p_snapshot->>'diff_lines')::bigint>1000000
    OR p_snapshot->>'result_head_sha' !~ '^[0-9a-f]{40}$'
    OR p_snapshot->>'diff_digest' !~ '^[0-9a-f]{64}$'
  THEN RETURN false; END IF;
  v_snapshot_facts=(p_snapshot-'workspace_snapshot_digest')
    || jsonb_build_object('contract','adaptive-factory.workspace-snapshot/v1');
  v_snapshot_digest=factory.execution_contract_hash(
    NULL,factory.execution_canonical_json(v_snapshot_facts)
  );
  IF NOT factory.execution_object_has_exact_keys(p_result,ARRAY[
      'contract_version','task_id','run_id','task_packet_digest','run_manifest_digest',
      'exact_head_sha','workspace_snapshot_digest','terminal_stage','terminal_proposal_digest',
      'artifact_manifest_digest','note_manifest_digest','usage_evidence_digest',
      'diagnostics_digest','m4_status','failure_class','failure_reason','workspace_result_digest'
    ]) OR p_result->'contract_version' IS DISTINCT FROM '1'::jsonb
    OR p_snapshot->>'source' IS DISTINCT FROM 'trusted_git_broker'
    OR p_snapshot->>'repository_id' IS DISTINCT FROM repository
    OR p_snapshot->>'workspace_handle' IS DISTINCT FROM manifest_workspace
    OR p_snapshot->>'input_head_sha' IS DISTINCT FROM input_head
    OR p_snapshot->>'workspace_snapshot_digest' IS DISTINCT FROM v_snapshot_digest
    OR p_result->>'task_id' IS DISTINCT FROM p_task_id::text
    OR p_result->>'run_id' IS DISTINCT FROM p_run_id::text
    OR p_result->>'task_packet_digest' IS DISTINCT FROM trim(p_packet_digest)
    OR p_result->>'run_manifest_digest' IS DISTINCT FROM trim(v_manifest_digest)
    OR p_result->>'exact_head_sha' IS DISTINCT FROM p_snapshot->>'result_head_sha'
    OR p_result->>'workspace_snapshot_digest' IS DISTINCT FROM v_snapshot_digest
    OR p_result->>'terminal_stage' IS DISTINCT FROM target_stage
    OR p_result->>'terminal_proposal_digest' IS DISTINCT FROM trim(terminal_digest)
    OR p_result->>'m4_status' IS DISTINCT FROM target_m4_status
    OR p_result->>'failure_class' IS DISTINCT FROM terminal_failure_class
    OR p_result->>'failure_reason' IS DISTINCT FROM terminal_failure_reason
    OR p_result->>'artifact_manifest_digest' IS DISTINCT FROM v_artifact_digest
    OR p_result->>'note_manifest_digest' IS DISTINCT FROM v_note_digest
    OR p_result->>'usage_evidence_digest' IS DISTINCT FROM v_usage_digest
    OR p_result->>'diagnostics_digest' IS DISTINCT FROM v_diagnostics_digest
  THEN RETURN false; END IF;
  v_expected_result=jsonb_build_object(
    'contract_version',1,'task_id',p_task_id::text,'run_id',p_run_id::text,
    'task_packet_digest',trim(p_packet_digest),
    'run_manifest_digest',trim(v_manifest_digest),
    'exact_head_sha',p_snapshot->>'result_head_sha',
    'workspace_snapshot_digest',v_snapshot_digest,
    'terminal_stage',target_stage,'terminal_proposal_digest',trim(terminal_digest),
    'artifact_manifest_digest',v_artifact_digest,'note_manifest_digest',v_note_digest,
    'usage_evidence_digest',v_usage_digest,'diagnostics_digest',v_diagnostics_digest,
    'm4_status',target_m4_status,'failure_class',terminal_failure_class,
    'failure_reason',terminal_failure_reason
  );
  v_result_digest=factory.execution_contract_hash(
    'adaptive-factory.workspace-result/v1',v_expected_result
  );
  IF trim(p_workspace_result_digest) IS DISTINCT FROM v_result_digest
    OR p_result->>'workspace_result_digest' IS DISTINCT FROM v_result_digest
    OR (p_result-'workspace_result_digest') IS DISTINCT FROM v_expected_result
  THEN RETURN false; END IF;
  INSERT INTO factory.workspace_results(
    workspace_result_digest,task_id,run_id,task_packet_digest,run_manifest_digest,exact_head_sha,
    workspace_snapshot_digest,terminal_stage,terminal_proposal_digest,terminal_proposal_kind,
    artifact_manifest_digest,note_manifest_digest,usage_evidence_digest,diagnostics_digest,
    m4_status,failure_class,failure_reason,workspace_snapshot,body
  ) VALUES (
    p_workspace_result_digest,p_task_id,p_run_id,p_packet_digest,v_manifest_digest,
    p_result->>'exact_head_sha',v_snapshot_digest,target_stage,terminal_digest,'terminal',
    v_artifact_digest,v_note_digest,v_usage_digest,v_diagnostics_digest,target_m4_status,
    terminal_failure_class,terminal_failure_reason,p_snapshot,p_result
  );
  SELECT COALESCE(max(stage_sequence),0)+1 INTO next_sequence
    FROM factory.execution_stage_events WHERE execution_stage_events.manifest_digest=v_manifest_digest;
  UPDATE factory.execution_manifests SET stage=target_stage,updated_at=clock_timestamp(),terminal_at=clock_timestamp()
    WHERE execution_manifests.manifest_digest=v_manifest_digest;
  INSERT INTO factory.execution_stage_events(manifest_digest,stage_sequence,stage)
    VALUES (v_manifest_digest,next_sequence,target_stage);
  UPDATE factory.attempts SET
    failure_class=CASE WHEN target_stage='failed' THEN terminal_failure_class ELSE NULL END,
    failure_code=CASE WHEN target_stage='failed' THEN terminal_failure_class ELSE NULL END,
    failure_digest=CASE WHEN target_stage='failed' THEN factory.execution_contract_hash(
      NULL,factory.execution_canonical_json(jsonb_build_object('failure',terminal_failure_class))
    ) ELSE NULL END,
    finished_at=clock_timestamp()
    WHERE run_id=p_run_id;
  IF target_stage<>'completed' AND EXISTS (
    SELECT 1 FROM factory.tasks task
    WHERE task.task_id=p_task_id AND (
      task.accounting_blocked OR task.cost_reserved_micros<>0
      OR task.tokens_reserved<>0 OR task.wall_reserved_seconds<>0
      OR EXISTS (
        SELECT 1 FROM factory.budget_reservations reservation
        WHERE reservation.task_id=p_task_id AND reservation.run_id=p_run_id
          AND reservation.released_at IS NULL
      )
    )
  ) THEN
    UPDATE factory.tasks SET accounting_blocked=true WHERE task_id=p_task_id;
  END IF;
  UPDATE factory.runs
    SET state=CASE WHEN target_stage='completed' THEN 'completed' ELSE 'failed' END,
      released_at=clock_timestamp()
    WHERE run_id=p_run_id;
  IF NOT factory.capacity_release(p_run_id) THEN RETURN false; END IF;
  UPDATE factory.tasks SET state=target_m4_status,current_run_id=NULL,current_fence=NULL,
    updated_at=clock_timestamp(),
    terminal_at=CASE WHEN target_m4_status IN ('ready_for_human','dead')
      THEN clock_timestamp() ELSE terminal_at END
    WHERE task_id=p_task_id;
  RETURN true;
END;
$$;

REVOKE ALL ON factory.execution_packets,factory.execution_manifests,
  factory.execution_stage_events,factory.execution_proposals,factory.workspace_results FROM PUBLIC,factory_runtime;
REVOKE ALL ON factory.execution_artifact_attestations
  FROM PUBLIC,factory_runtime,factory_artifact_attestor;
REVOKE ALL ON FUNCTION factory.execution_object_has_exact_keys(jsonb,text[]) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_sorted_unique_identifiers(jsonb,integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_canonical_json(jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_contract_hash(text,jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_contract_hash(text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_start(uuid,uuid,text,bigint,char,char,char,text,text,jsonb,jsonb)
  FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_advance(uuid,uuid,text,bigint,char,char,text)
  FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_propose(uuid,uuid,text,bigint,char,char,bigint,char,text,jsonb)
  FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_proposal_context(uuid,uuid,text,bigint,char,char)
  FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_proposal_by_key(uuid,uuid,char) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_m4_status(uuid,uuid,text,text,bigint) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_record_artifact_attestation(jsonb)
  FROM PUBLIC,factory_runtime,factory_artifact_attestor;
REVOKE ALL ON FUNCTION factory.execution_result_for_run(uuid,uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_result_by_digest(uuid,char) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_finalize_context(uuid,uuid,text,bigint,char,char) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_finalize_commit(uuid,uuid,text,bigint,char,char,char,jsonb,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION factory.execution_start(uuid,uuid,text,bigint,char,char,char,text,text,jsonb,jsonb)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_advance(uuid,uuid,text,bigint,char,char,text)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_propose(uuid,uuid,text,bigint,char,char,bigint,char,text,jsonb)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_proposal_context(uuid,uuid,text,bigint,char,char)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_proposal_by_key(uuid,uuid,char) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_result_for_run(uuid,uuid) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_result_by_digest(uuid,char) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_finalize_context(uuid,uuid,text,bigint,char,char) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_finalize_commit(uuid,uuid,text,bigint,char,char,char,jsonb,jsonb) TO factory_runtime;
GRANT USAGE ON SCHEMA factory TO factory_artifact_attestor;
GRANT EXECUTE ON FUNCTION factory.execution_record_artifact_attestation(jsonb)
  TO factory_artifact_attestor;
