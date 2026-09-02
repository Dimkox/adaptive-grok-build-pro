DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='factory_artifact_attestor') THEN
    CREATE ROLE factory_artifact_attestor NOLOGIN NOINHERIT;
  END IF;
END $$;

CREATE TABLE factory.execution_packets (
  packet_digest char(64) PRIMARY KEY CHECK (packet_digest ~ '^[0-9a-f]{64}$'),
  task_id uuid NOT NULL,
  run_id uuid NOT NULL,
  legacy_packet_digest char(64) NOT NULL CHECK (legacy_packet_digest ~ '^[0-9a-f]{64}$'),
  provider_id text NOT NULL CHECK (octet_length(provider_id) BETWEEN 1 AND 128),
  body jsonb NOT NULL CHECK (octet_length(body::text) <= 1048576),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (run_id),
  UNIQUE (packet_digest, run_id),
  FOREIGN KEY (run_id, task_id) REFERENCES factory.runs(run_id, task_id) ON DELETE RESTRICT
);

CREATE TABLE factory.execution_manifests (
  manifest_digest char(64) PRIMARY KEY CHECK (manifest_digest ~ '^[0-9a-f]{64}$'),
  task_id uuid NOT NULL,
  run_id uuid NOT NULL UNIQUE,
  packet_digest char(64) NOT NULL,
  workspace_handle text NOT NULL CHECK (workspace_handle ~ '^workspace:[0-9a-f]{64}$'),
  stage text NOT NULL CHECK (stage IN ('prepared','running','collecting','completed','failed','needs_human','cancelled','orphaned')),
  body jsonb NOT NULL CHECK (octet_length(body::text) <= 65536),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  terminal_at timestamptz,
  UNIQUE (manifest_digest,run_id),
  FOREIGN KEY (packet_digest, run_id) REFERENCES factory.execution_packets(packet_digest, run_id) ON DELETE RESTRICT,
  FOREIGN KEY (run_id, task_id) REFERENCES factory.runs(run_id, task_id) ON DELETE RESTRICT,
  CHECK ((terminal_at IS NULL) = (stage NOT IN ('completed','failed','needs_human','cancelled','orphaned')))
);
CREATE INDEX execution_manifests_recovery ON factory.execution_manifests(updated_at,run_id)
  WHERE terminal_at IS NULL;

CREATE TABLE factory.execution_stage_events (
  stage_event_id bigserial PRIMARY KEY,
  manifest_digest char(64) NOT NULL REFERENCES factory.execution_manifests(manifest_digest) ON DELETE RESTRICT,
  stage_sequence bigint NOT NULL CHECK (stage_sequence > 0),
  stage text NOT NULL CHECK (stage IN ('prepared','running','collecting','completed','failed','needs_human','cancelled','orphaned')),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (manifest_digest,stage_sequence)
);

CREATE TABLE factory.execution_proposals (
  proposal_id uuid PRIMARY KEY,
  task_id uuid NOT NULL,
  run_id uuid NOT NULL,
  packet_digest char(64) NOT NULL,
  producer_sequence bigint NOT NULL CHECK (producer_sequence > 0),
  idempotency_key char(64) NOT NULL CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
  proposal_kind text NOT NULL CHECK (proposal_kind IN ('note','artifact','usage','terminal')),
  body jsonb NOT NULL CHECK (octet_length(body::text) <= 65536),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (run_id,producer_sequence),
  UNIQUE (run_id,idempotency_key),
  UNIQUE (run_id,idempotency_key,proposal_kind),
  FOREIGN KEY (packet_digest,run_id) REFERENCES factory.execution_packets(packet_digest,run_id) ON DELETE RESTRICT,
  FOREIGN KEY (run_id,task_id) REFERENCES factory.runs(run_id,task_id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX execution_proposals_one_terminal
  ON factory.execution_proposals(run_id) WHERE proposal_kind='terminal';

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
  artifact_class text NOT NULL CHECK (artifact_class ~ '^[A-Za-z][A-Za-z0-9._-]{0,127}$'),
  path text NOT NULL CHECK (octet_length(path) BETWEEN 1 AND 4096),
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

CREATE TABLE factory.workspace_results (
  workspace_result_digest char(64) PRIMARY KEY CHECK (workspace_result_digest ~ '^[0-9a-f]{64}$'),
  task_id uuid NOT NULL,
  run_id uuid NOT NULL UNIQUE,
  task_packet_digest char(64) NOT NULL,
  run_manifest_digest char(64) NOT NULL UNIQUE,
  exact_head_sha char(40) NOT NULL CHECK (exact_head_sha ~ '^[0-9a-f]{40}$'),
  workspace_snapshot_digest char(64) NOT NULL CHECK (workspace_snapshot_digest ~ '^[0-9a-f]{64}$'),
  terminal_stage text NOT NULL CHECK (terminal_stage IN ('completed','failed','needs_human')),
  terminal_proposal_digest char(64) NOT NULL,
  terminal_proposal_kind text NOT NULL CHECK (terminal_proposal_kind='terminal'),
  artifact_manifest_digest char(64) NOT NULL CHECK (artifact_manifest_digest ~ '^[0-9a-f]{64}$'),
  note_manifest_digest char(64) NOT NULL CHECK (note_manifest_digest ~ '^[0-9a-f]{64}$'),
  usage_evidence_digest char(64) NOT NULL CHECK (usage_evidence_digest ~ '^[0-9a-f]{64}$'),
  diagnostics_digest char(64) NOT NULL CHECK (diagnostics_digest ~ '^[0-9a-f]{64}$'),
  m4_status text NOT NULL CHECK (m4_status IN ('ready_for_human','retry','needs_human','dead')),
  failure_class text,
  failure_reason text CHECK (failure_reason IS NULL OR octet_length(failure_reason) BETWEEN 1 AND 4096),
  workspace_snapshot jsonb NOT NULL CHECK (octet_length(workspace_snapshot::text) <= 65536),
  body jsonb NOT NULL CHECK (octet_length(body::text) <= 65536),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  FOREIGN KEY (task_packet_digest,run_id) REFERENCES factory.execution_packets(packet_digest,run_id) ON DELETE RESTRICT,
  FOREIGN KEY (run_manifest_digest,run_id) REFERENCES factory.execution_manifests(manifest_digest,run_id) ON DELETE RESTRICT,
  FOREIGN KEY (run_id,terminal_proposal_digest,terminal_proposal_kind) REFERENCES factory.execution_proposals(run_id,idempotency_key,proposal_kind) ON DELETE RESTRICT,
  FOREIGN KEY (run_id,task_id) REFERENCES factory.runs(run_id,task_id) ON DELETE RESTRICT
  ,CHECK (
    (terminal_stage='completed' AND m4_status='ready_for_human' AND failure_class IS NULL AND failure_reason IS NULL)
    OR (terminal_stage='failed' AND m4_status IN ('retry','needs_human','dead') AND failure_class IS NOT NULL AND failure_reason IS NOT NULL)
    OR (terminal_stage='needs_human' AND m4_status='needs_human' AND failure_class IS NULL AND failure_reason IS NOT NULL)
  )
);

CREATE FUNCTION factory.execution_start(
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
BEGIN
  IF octet_length(p_packet::text)>1048576 OR octet_length(p_manifest::text)>65536 THEN
    RETURN false;
  END IF;
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
END;
$$;

CREATE FUNCTION factory.execution_advance(
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

CREATE FUNCTION factory.execution_propose(
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
  v_existing_count bigint;
  v_existing_exact boolean;
  v_event_count bigint;
  v_max_sequence bigint;
  v_has_terminal boolean;
  v_max_events bigint;
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
  IF p_task_id IS NULL OR p_run_id IS NULL OR p_owner IS NULL OR p_fence IS NULL
    OR p_legacy_packet_digest IS NULL OR p_packet_digest IS NULL OR p_sequence IS NULL
    OR p_idempotency_key IS NULL OR p_kind IS NULL OR p_body IS NULL
    OR jsonb_typeof(p_body) IS DISTINCT FROM 'object'
    OR octet_length(p_body::text)>65536
    OR p_kind NOT IN ('note','artifact','usage','terminal')
  THEN RETURN false; END IF;
  SELECT r.role,t.repository_id,m.workspace_handle,p.body
    INTO v_role,v_repository_id,v_workspace_handle,v_packet
    FROM factory.tasks t
    JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
    JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
    JOIN factory.execution_packets p ON p.run_id=r.run_id AND p.task_id=t.task_id
    JOIN factory.execution_manifests m ON m.run_id=r.run_id AND m.packet_digest=p_packet_digest
    WHERE t.task_id=p_task_id AND r.run_id=p_run_id AND r.owner_id=p_owner
      AND r.fence=p_fence AND r.packet_digest=p_legacy_packet_digest
      AND t.packet_digest=p_legacy_packet_digest AND t.current_fence=p_fence
      AND p.packet_digest=p_packet_digest AND p.legacy_packet_digest=p_legacy_packet_digest
      AND t.state='leased' AND r.state='leased'
      AND r.released_at IS NULL AND a.released_at IS NULL
      AND m.terminal_at IS NULL AND r.lease_expires_at>clock_timestamp()
      AND t.deadline_at>clock_timestamp()
    FOR UPDATE OF t,r,m;
  IF NOT FOUND THEN RETURN false; END IF;
  v_max_events=(v_packet#>>'{limits,max_events}')::bigint;
  v_allowed_paths=v_packet#>'{capability_policy,allowed_paths}';
  IF v_max_events IS NULL OR v_max_events NOT BETWEEN 1 AND 100000
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
      OR p_body->>'note_type' !~ '^[A-Za-z][A-Za-z0-9._-]{0,63}$'
      OR EXISTS (
        SELECT 1 FROM unnest(ARRAY[
          'analysis','reasoning','scratchpad','chainofthought','rawprompt',
          'prompt','stdout','stderr','nativestream'
        ]) marker
        WHERE regexp_replace(lower(p_body->>'note_type'),'[^a-z0-9]+','','g') LIKE '%' || marker || '%'
      )
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
        WHERE path='' OR path LIKE '/%' OR path LIKE '%//%' OR path LIKE '%/'
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
          AND COALESCE(octet_length(p_body->>'diagnostic'),0) BETWEEN 1 AND
              LEAST(65536,(v_packet#>>'{limits,max_output_bytes}')::bigint))
        OR (p_body->>'terminal_type'='run.needs_human' AND p_body->'failure_class'='null'::jsonb
          AND jsonb_typeof(p_body->'reason')='string' AND jsonb_typeof(p_body->'diagnostic')='string'
          AND p_body->>'summary'=(p_body->>'reason') || ': ' || (p_body->>'diagnostic')
          AND COALESCE(octet_length(p_body->>'reason'),0) BETWEEN 1 AND
              LEAST(65536,(v_packet#>>'{limits,max_output_bytes}')::bigint)
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

  SELECT count(*),COALESCE(bool_and(
      task_id=p_task_id AND run_id=p_run_id AND packet_digest=p_packet_digest
      AND producer_sequence=p_sequence AND idempotency_key=p_idempotency_key
      AND proposal_kind=p_kind AND body=p_body
    ),false)
    INTO v_existing_count,v_existing_exact
    FROM factory.execution_proposals
    WHERE run_id=p_run_id AND (producer_sequence=p_sequence OR idempotency_key=p_idempotency_key);
  IF v_existing_count>0 THEN
    RETURN v_existing_count=1 AND v_existing_exact;
  END IF;

  SELECT count(*),COALESCE(max(producer_sequence),0),
         COALESCE(bool_or(proposal_kind='terminal'),false)
    INTO v_event_count,v_max_sequence,v_has_terminal
    FROM factory.execution_proposals
    WHERE run_id=p_run_id;
  IF v_has_terminal OR v_event_count>=v_max_events OR p_sequence<>v_max_sequence+1 THEN
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
EXCEPTION WHEN unique_violation OR check_violation OR foreign_key_violation OR data_exception THEN
  RETURN false;
END;
$$;

CREATE FUNCTION factory.execution_proposal_context(
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
    AND NOT EXISTS (
      SELECT 1 FROM factory.execution_proposals terminal
      WHERE terminal.run_id=p_run_id AND terminal.proposal_kind='terminal'
    )
    AND r.lease_expires_at>clock_timestamp() AND t.deadline_at>clock_timestamp()
$$;

CREATE FUNCTION factory.execution_proposal_by_key(
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

CREATE FUNCTION factory.execution_result_for_run(p_task_id uuid,p_run_id uuid) RETURNS jsonb
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
      'workspace_snapshot_digest',trim(w.workspace_snapshot_digest),'terminal_stage',w.terminal_stage,
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

CREATE FUNCTION factory.execution_has_packet(p_run_id uuid) RETURNS boolean
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT EXISTS(SELECT 1 FROM factory.execution_packets WHERE run_id=p_run_id)
$$;

CREATE FUNCTION factory.execution_m4_status(
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
BEGIN
  SELECT t.accounting_blocked,t.cost_reserved_micros,t.tokens_reserved,t.wall_reserved_seconds,
    EXISTS(SELECT 1 FROM factory.usage_observations u WHERE u.task_id=p_task_id AND u.run_id=p_run_id),
    EXISTS(SELECT 1 FROM factory.budget_reservations b WHERE b.task_id=p_task_id AND b.run_id=p_run_id AND b.released_at IS NULL),
    t.event_limit,
    (SELECT count(*) FROM factory.task_events e WHERE e.task_id=p_task_id AND NOT e.mandatory_cleanup)
    INTO v_accounting_blocked,v_reserved_cost,v_reserved_tokens,v_reserved_wall,
      v_has_usage,v_has_reservation,v_event_limit,v_ordinary_events
    FROM factory.tasks t WHERE t.task_id=p_task_id;
  IF NOT FOUND THEN RETURN NULL; END IF;
  IF p_terminal_type='run.completed' THEN
    IF v_accounting_blocked OR NOT v_has_usage OR v_has_reservation
      OR v_reserved_cost<>0 OR v_reserved_tokens<>0 OR v_reserved_wall<>0
    THEN RETURN NULL; END IF;
    RETURN 'ready_for_human';
  END IF;
  IF p_terminal_type='run.needs_human' THEN RETURN 'needs_human'; END IF;
  IF p_terminal_type<>'run.failed' THEN RETURN NULL; END IF;
  IF p_failure_class IN (
    'database_unavailable','worker_lost','provider_transport_unavailable','temporary_resource_exhaustion'
  ) THEN
    v_status=CASE WHEN p_attempt_no>=3 THEN 'dead' ELSE 'retry' END;
  ELSE
    v_status='needs_human';
  END IF;
  IF v_has_reservation OR (v_status='retry' AND v_ordinary_events>=v_event_limit) THEN
    RETURN 'needs_human';
  END IF;
  RETURN v_status;
END;
$$;

CREATE FUNCTION factory.execution_contract_hash(p_domain text,p_canonical text) RETURNS char(64)
LANGUAGE sql IMMUTABLE SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT encode(sha256(
    CASE WHEN p_domain IS NULL THEN convert_to(p_canonical,'UTF8')
      ELSE convert_to(p_domain,'UTF8') || decode('00','hex') || convert_to(p_canonical,'UTF8') END
  ),'hex')::char(64)
$$;

CREATE FUNCTION factory.execution_record_artifact_attestation(p_request jsonb) RETURNS jsonb
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
BEGIN
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
    OR p_request->>'packet_digest' !~ '^[0-9a-f]{64}$'
    OR p_request->>'producer_sequence' !~ '^[1-9][0-9]{0,5}$'
    OR p_request->>'fence' !~ '^[1-9][0-9]{0,18}$'
    OR p_request->>'size_bytes' !~ '^(0|[1-9][0-9]{0,9})$'
    OR p_request->>'sha256' !~ '^[0-9a-f]{64}$'
    OR p_request->>'media_type' !~ '^[a-z0-9.+-]+/[a-z0-9.+-]+$'
  THEN RETURN NULL; END IF;

  SELECT p.body,t.repository_id,m.workspace_handle,r.role,r.fence
    INTO v_packet,v_repository_id,v_workspace_handle,v_role,v_fence
    FROM factory.tasks t
    JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
    JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
    JOIN factory.execution_packets p ON p.run_id=r.run_id AND p.task_id=t.task_id
    JOIN factory.execution_manifests m ON m.run_id=r.run_id AND m.packet_digest=p.packet_digest
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
  SELECT body INTO v_existing FROM factory.execution_artifact_attestations
    WHERE run_id=(p_request->>'run_id')::uuid
      AND producer_sequence=(p_request->>'producer_sequence')::bigint;
  IF FOUND THEN RETURN CASE WHEN v_existing=v_body THEN v_existing ELSE NULL END; END IF;
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
EXCEPTION WHEN unique_violation OR check_violation OR foreign_key_violation OR data_exception THEN
  RETURN NULL;
END;
$$;

CREATE FUNCTION factory.execution_result_by_digest(
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
      'workspace_snapshot_digest',trim(w.workspace_snapshot_digest),'terminal_stage',w.terminal_stage,
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

CREATE FUNCTION factory.execution_finalize_context(
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
  IF (SELECT count(*) FROM factory.execution_proposals WHERE run_id=p_run_id)>1000 THEN
    RETURN NULL;
  END IF;
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
      p_task_id,p_run_id,terminal.body->>'terminal_type',terminal.body->>'failure_class',at.attempt_no
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
  ) INTO result
  FROM factory.tasks t
  JOIN factory.execution_packets p ON p.task_id=t.task_id AND p.run_id=p_run_id AND p.packet_digest=p_packet_digest
  JOIN factory.execution_manifests m ON m.run_id=p.run_id AND m.packet_digest=p.packet_digest
  JOIN factory.attempts at ON at.run_id=p.run_id
  JOIN factory.execution_proposals terminal ON terminal.run_id=p.run_id AND terminal.proposal_kind='terminal'
  WHERE t.task_id=p_task_id;
  IF result->>'terminal_stage' IS NULL OR result->>'m4_status' IS NULL THEN RETURN NULL; END IF;
  IF result->>'terminal_stage'='failed' AND (
    result->>'failure_class' NOT IN (
      'database_unavailable','worker_lost','provider_transport_unavailable','temporary_resource_exhaustion',
      'validation','policy','authentication','unsupported_capability','budget','security',
      'stale_input','protocol','provider_quality'
    ) OR COALESCE(octet_length(result->>'failure_reason'),0) NOT BETWEEN 1 AND 4096
  ) THEN RETURN NULL; END IF;
  IF result->>'terminal_stage'='needs_human'
    AND COALESCE(octet_length(result->>'failure_reason'),0) NOT BETWEEN 1 AND 4096
  THEN RETURN NULL; END IF;
  RETURN result;
END;
$$;

CREATE FUNCTION factory.execution_finalize_commit(
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
  v_attempt_no bigint;
  v_artifact_digest char(64);
  v_note_digest char(64);
  v_usage_digest char(64);
  v_diagnostics_digest char(64);
  v_snapshot_digest char(64);
  v_result_digest char(64);
  v_canonical text;
  next_sequence bigint;
BEGIN
  IF jsonb_typeof(p_snapshot) IS DISTINCT FROM 'object'
    OR jsonb_typeof(p_result) IS DISTINCT FROM 'object'
  THEN RETURN false; END IF;
  IF octet_length(p_snapshot::text)>65536 OR octet_length(p_result::text)>65536 THEN RETURN false; END IF;
  IF NOT factory.capacity_lock_run(p_run_id) THEN RETURN false; END IF;
  SELECT m.stage,m.manifest_digest,m.workspace_handle,t.repository_id,
    p.body#>>'{authority,exact_head_sha}',terminal.body->>'terminal_type',terminal.idempotency_key,
    terminal.body->>'failure_class',
    CASE terminal.body->>'terminal_type'
      WHEN 'run.failed' THEN terminal.body->>'diagnostic'
      WHEN 'run.needs_human' THEN terminal.body->>'reason'
      ELSE NULL END,
    at.attempt_no
    INTO current_stage,v_manifest_digest,manifest_workspace,repository,input_head,terminal_type,
      terminal_digest,terminal_failure_class,terminal_failure_reason,v_attempt_no
  FROM factory.tasks t
  JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
  JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
  JOIN factory.execution_packets p ON p.run_id=r.run_id AND p.task_id=t.task_id
  JOIN factory.execution_manifests m ON m.run_id=p.run_id AND m.packet_digest=p.packet_digest
  JOIN factory.execution_proposals terminal ON terminal.run_id=p.run_id AND terminal.proposal_kind='terminal'
  JOIN factory.attempts at ON at.run_id=r.run_id
  WHERE t.task_id=p_task_id AND r.run_id=p_run_id AND r.owner_id=p_owner
    AND r.fence=p_fence AND r.packet_digest=p_legacy_packet_digest
    AND t.packet_digest=p_legacy_packet_digest AND t.current_fence=p_fence
    AND p.packet_digest=p_packet_digest AND t.state='leased' AND r.state='leased'
    AND r.released_at IS NULL AND a.released_at IS NULL AND m.terminal_at IS NULL
    AND r.lease_expires_at>clock_timestamp() AND t.deadline_at>clock_timestamp()
  FOR UPDATE OF t,r,m,terminal;
  IF NOT FOUND THEN RETURN false; END IF;
  target_stage=CASE terminal_type
    WHEN 'run.completed' THEN 'completed'
    WHEN 'run.failed' THEN 'failed'
    WHEN 'run.needs_human' THEN 'needs_human'
    ELSE NULL END;
  target_m4_status=factory.execution_m4_status(
    p_task_id,p_run_id,terminal_type,terminal_failure_class,v_attempt_no
  );
  IF target_stage IS NULL OR (target_stage='completed' AND current_stage<>'collecting') THEN RETURN false; END IF;
  IF target_stage='failed' AND (
    terminal_failure_class NOT IN (
      'database_unavailable','worker_lost','provider_transport_unavailable','temporary_resource_exhaustion',
      'validation','policy','authentication','unsupported_capability','budget','security',
      'stale_input','protocol','provider_quality'
    ) OR COALESCE(octet_length(terminal_failure_reason),0) NOT BETWEEN 1 AND 4096
  ) THEN RETURN false; END IF;
  IF target_stage='needs_human'
    AND COALESCE(octet_length(terminal_failure_reason),0) NOT BETWEEN 1 AND 4096
  THEN RETURN false; END IF;
  IF target_stage='completed' AND NOT EXISTS (
    SELECT 1 FROM factory.usage_observations u WHERE u.task_id=p_task_id AND u.run_id=p_run_id
  ) THEN RETURN false; END IF;
  IF target_stage='completed' AND EXISTS (
    SELECT 1 FROM factory.budget_reservations b WHERE b.task_id=p_task_id AND b.released_at IS NULL
  ) THEN RETURN false; END IF;
  SELECT factory.execution_contract_hash(
    'adaptive-factory.workspace-artifacts/v1',
    '[' || COALESCE(string_agg(to_jsonb(trim(x.idempotency_key))::text,',' ORDER BY trim(x.idempotency_key)),'') || ']'
  ) INTO v_artifact_digest FROM factory.execution_proposals x
    WHERE x.run_id=p_run_id AND x.proposal_kind='artifact';
  SELECT factory.execution_contract_hash(
    'adaptive-factory.workspace-notes/v1',
    '[' || COALESCE(string_agg(to_jsonb(trim(x.idempotency_key))::text,',' ORDER BY trim(x.idempotency_key)),'') || ']'
  ) INTO v_note_digest FROM factory.execution_proposals x
    WHERE x.run_id=p_run_id AND x.proposal_kind='note';
  SELECT factory.execution_contract_hash(
    'adaptive-factory.workspace-usage/v1',
    '[' || COALESCE(string_agg(to_jsonb(trim(x.idempotency_key))::text,',' ORDER BY trim(x.idempotency_key)),'') || ']'
  ) INTO v_usage_digest FROM factory.execution_proposals x
    WHERE x.run_id=p_run_id AND x.proposal_kind='usage';
  v_diagnostics_digest=factory.execution_contract_hash(
    'adaptive-factory.workspace-diagnostics/v1','[]'
  );
  IF NOT (p_snapshot ?& ARRAY[
      'contract_version','repository_id','workspace_handle','input_head_sha','result_head_sha',
      'diff_digest','diff_lines','source','workspace_snapshot_digest'
    ]) OR (SELECT count(*) FROM jsonb_object_keys(p_snapshot))<>9
    OR p_snapshot->'contract_version' IS DISTINCT FROM '1'::jsonb
    OR jsonb_typeof(p_snapshot->'diff_lines') IS DISTINCT FROM 'number'
    OR p_snapshot->>'diff_lines' !~ '^(0|[1-9][0-9]{0,6})$'
    OR (p_snapshot->>'diff_lines')::bigint>1000000
    OR p_snapshot->>'result_head_sha' !~ '^[0-9a-f]{40}$'
    OR p_snapshot->>'diff_digest' !~ '^[0-9a-f]{64}$'
  THEN RETURN false; END IF;
  v_canonical='{' ||
    '"contract":' || to_jsonb('adaptive-factory.workspace-snapshot/v1'::text)::text ||
    ',"contract_version":1' ||
    ',"diff_digest":' || to_jsonb(p_snapshot->>'diff_digest')::text ||
    ',"diff_lines":' || (p_snapshot->>'diff_lines') ||
    ',"input_head_sha":' || to_jsonb(p_snapshot->>'input_head_sha')::text ||
    ',"repository_id":' || to_jsonb(p_snapshot->>'repository_id')::text ||
    ',"result_head_sha":' || to_jsonb(p_snapshot->>'result_head_sha')::text ||
    ',"source":' || to_jsonb(p_snapshot->>'source')::text ||
    ',"workspace_handle":' || to_jsonb(p_snapshot->>'workspace_handle')::text || '}';
  v_snapshot_digest=factory.execution_contract_hash(NULL,v_canonical);
  IF p_snapshot->>'source' IS DISTINCT FROM 'trusted_git_broker'
    OR p_snapshot->>'repository_id' IS DISTINCT FROM repository
    OR p_snapshot->>'workspace_handle' IS DISTINCT FROM manifest_workspace
    OR p_snapshot->>'input_head_sha' IS DISTINCT FROM input_head
    OR p_result->>'task_id' IS DISTINCT FROM p_task_id::text
    OR p_result->>'run_id' IS DISTINCT FROM p_run_id::text
    OR p_result->>'task_packet_digest' IS DISTINCT FROM trim(p_packet_digest)
    OR p_result->>'run_manifest_digest' IS DISTINCT FROM trim(v_manifest_digest)
    OR p_result->>'exact_head_sha' IS DISTINCT FROM p_snapshot->>'result_head_sha'
    OR p_result->>'workspace_snapshot_digest' IS DISTINCT FROM p_snapshot->>'workspace_snapshot_digest'
    OR p_result->>'workspace_result_digest' IS DISTINCT FROM trim(p_workspace_result_digest)
    OR p_result->>'terminal_stage' IS DISTINCT FROM target_stage
    OR p_result->>'terminal_proposal_digest' IS DISTINCT FROM trim(terminal_digest)
    OR p_result->>'m4_status' IS DISTINCT FROM target_m4_status
    OR p_result->>'failure_class' IS DISTINCT FROM terminal_failure_class
    OR p_result->>'failure_reason' IS DISTINCT FROM terminal_failure_reason
    OR p_snapshot->>'workspace_snapshot_digest' IS DISTINCT FROM trim(v_snapshot_digest)
    OR p_result->>'artifact_manifest_digest' IS DISTINCT FROM trim(v_artifact_digest)
    OR p_result->>'note_manifest_digest' IS DISTINCT FROM trim(v_note_digest)
    OR p_result->>'usage_evidence_digest' IS DISTINCT FROM trim(v_usage_digest)
    OR p_result->>'diagnostics_digest' IS DISTINCT FROM trim(v_diagnostics_digest)
  THEN RETURN false; END IF;
  IF NOT (p_result ?& ARRAY[
      'contract_version','task_id','run_id','task_packet_digest','run_manifest_digest',
      'exact_head_sha','workspace_snapshot_digest','terminal_stage','terminal_proposal_digest',
      'artifact_manifest_digest','note_manifest_digest','usage_evidence_digest',
      'diagnostics_digest','m4_status','failure_class','failure_reason','workspace_result_digest'
    ]) OR (SELECT count(*) FROM jsonb_object_keys(p_result))<>17
    OR p_result->'contract_version' IS DISTINCT FROM '1'::jsonb
  THEN RETURN false; END IF;
  v_canonical='{' ||
    '"artifact_manifest_digest":' || to_jsonb(trim(v_artifact_digest))::text ||
    ',"contract_version":1' ||
    ',"diagnostics_digest":' || to_jsonb(trim(v_diagnostics_digest))::text ||
    ',"exact_head_sha":' || to_jsonb(p_snapshot->>'result_head_sha')::text ||
    ',"failure_class":' || COALESCE(to_jsonb(terminal_failure_class)::text,'null') ||
    ',"failure_reason":' || COALESCE(to_jsonb(terminal_failure_reason)::text,'null') ||
    ',"m4_status":' || to_jsonb(target_m4_status)::text ||
    ',"note_manifest_digest":' || to_jsonb(trim(v_note_digest))::text ||
    ',"run_id":' || to_jsonb(p_run_id::text)::text ||
    ',"run_manifest_digest":' || to_jsonb(trim(v_manifest_digest))::text ||
    ',"task_id":' || to_jsonb(p_task_id::text)::text ||
    ',"task_packet_digest":' || to_jsonb(trim(p_packet_digest))::text ||
    ',"terminal_proposal_digest":' || to_jsonb(trim(terminal_digest))::text ||
    ',"terminal_stage":' || to_jsonb(target_stage)::text ||
    ',"usage_evidence_digest":' || to_jsonb(trim(v_usage_digest))::text ||
    ',"workspace_snapshot_digest":' || to_jsonb(trim(v_snapshot_digest))::text || '}';
  v_result_digest=factory.execution_contract_hash('adaptive-factory.workspace-result/v1',v_canonical);
  IF trim(p_workspace_result_digest) IS DISTINCT FROM trim(v_result_digest)
    OR p_result->>'workspace_result_digest' IS DISTINCT FROM trim(v_result_digest)
  THEN RETURN false; END IF;
  INSERT INTO factory.workspace_results(
    workspace_result_digest,task_id,run_id,task_packet_digest,run_manifest_digest,exact_head_sha,
    workspace_snapshot_digest,terminal_stage,terminal_proposal_digest,terminal_proposal_kind,
    artifact_manifest_digest,note_manifest_digest,usage_evidence_digest,diagnostics_digest,
    m4_status,failure_class,failure_reason,workspace_snapshot,body
  ) VALUES (
    p_workspace_result_digest,p_task_id,p_run_id,p_packet_digest,v_manifest_digest,
    p_result->>'exact_head_sha',p_result->>'workspace_snapshot_digest',target_stage,terminal_digest,'terminal',
    p_result->>'artifact_manifest_digest',p_result->>'note_manifest_digest',
    p_result->>'usage_evidence_digest',p_result->>'diagnostics_digest',target_m4_status,
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
      NULL,'{"failure":' || to_jsonb(terminal_failure_class)::text || '}'
    ) ELSE NULL END,
    finished_at=clock_timestamp()
    WHERE run_id=p_run_id;
  IF target_stage='failed' AND EXISTS (
    SELECT 1 FROM factory.budget_reservations b
    WHERE b.task_id=p_task_id AND b.run_id=p_run_id AND b.released_at IS NULL
  ) THEN
    UPDATE factory.tasks SET accounting_blocked=true WHERE task_id=p_task_id;
  END IF;
  UPDATE factory.runs SET state=CASE WHEN target_stage='completed' THEN 'completed' ELSE 'failed' END,
    released_at=clock_timestamp() WHERE run_id=p_run_id;
  IF NOT factory.capacity_release(p_run_id) THEN RETURN false; END IF;
  UPDATE factory.tasks SET state=target_m4_status,current_run_id=NULL,current_fence=NULL,
    updated_at=clock_timestamp(),
    terminal_at=CASE WHEN target_m4_status IN ('ready_for_human','dead') THEN clock_timestamp() ELSE terminal_at END
    WHERE task_id=p_task_id;
  RETURN true;
EXCEPTION WHEN unique_violation OR check_violation OR foreign_key_violation THEN
  RETURN false;
END;
$$;

REVOKE ALL ON factory.execution_packets,factory.execution_manifests,
  factory.execution_stage_events,factory.execution_proposals,factory.workspace_results FROM PUBLIC,factory_runtime;
REVOKE ALL ON factory.execution_artifact_attestations FROM PUBLIC,factory_runtime,factory_artifact_attestor;
REVOKE ALL ON FUNCTION factory.execution_start(uuid,uuid,text,bigint,char,char,char,text,text,jsonb,jsonb)
  FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_advance(uuid,uuid,text,bigint,char,char,text)
  FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_propose(uuid,uuid,text,bigint,char,char,bigint,char,text,jsonb)
  FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_proposal_context(uuid,uuid,text,bigint,char,char)
  FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_proposal_by_key(uuid,uuid,char) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_result_for_run(uuid,uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_has_packet(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_m4_status(uuid,uuid,text,text,bigint) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_contract_hash(text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_record_artifact_attestation(jsonb)
  FROM PUBLIC,factory_runtime;
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
GRANT EXECUTE ON FUNCTION factory.execution_has_packet(uuid) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_result_by_digest(uuid,char) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_finalize_context(uuid,uuid,text,bigint,char,char) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_finalize_commit(uuid,uuid,text,bigint,char,char,char,jsonb,jsonb) TO factory_runtime;
GRANT USAGE ON SCHEMA factory TO factory_artifact_attestor;
GRANT EXECUTE ON FUNCTION factory.execution_record_artifact_attestation(jsonb)
  TO factory_artifact_attestor;
