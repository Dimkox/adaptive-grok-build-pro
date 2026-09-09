ALTER TABLE factory.m0_authority_observations
  ADD COLUMN repository_id text,
  ADD COLUMN policy_digest char(64) CHECK (policy_digest ~ '^[0-9a-f]{64}$');
ALTER TABLE factory.m0_bootstrap_exceptions
  ADD COLUMN repository_id text,
  ADD COLUMN policy_digest char(64) CHECK (policy_digest ~ '^[0-9a-f]{64}$'),
  ADD COLUMN action text CHECK (action IN ('task:intake'));

ALTER TABLE factory.m0_authority_observations
  ADD CONSTRAINT m0_observation_repository_bound CHECK (
    repository_id IS NULL OR octet_length(repository_id) BETWEEN 1 AND 128
  ),
  ADD CONSTRAINT m0_observation_policy_check_bound CHECK (
    policy_digest IS NULL OR check_name='adaptive-trust-ci/verified@' || left(policy_digest,12)
  );
ALTER TABLE factory.m0_bootstrap_exceptions
  ADD CONSTRAINT m0_exception_repository_bound CHECK (
    repository_id IS NULL OR octet_length(repository_id) BETWEEN 1 AND 128
  );

ALTER TABLE factory.audit_log
  ADD COLUMN digest_version smallint NOT NULL DEFAULT 1 CHECK (digest_version IN (1,2));
ALTER TABLE factory.audit_log ALTER COLUMN digest_version SET DEFAULT 2;

CREATE INDEX audit_log_task_order ON factory.audit_log(task_id,audit_id);
CREATE INDEX usage_observations_task_run ON factory.usage_observations(task_id,run_id);
CREATE INDEX budget_reservations_task_run_active
  ON factory.budget_reservations(task_id,run_id) WHERE released_at IS NULL;
CREATE INDEX runs_expired_reconcile
  ON factory.runs(lease_expires_at,task_id) WHERE released_at IS NULL;

CREATE FUNCTION factory.m0_observation_valid(
  p_observed_at timestamptz, p_check_name text, p_exact_head_sha char(40),
  p_repository_id text, p_policy_digest char(64)
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE valid boolean := false;
BEGIN
  SELECT true INTO valid FROM factory.m0_authority_observations
  WHERE observed_at=p_observed_at AND check_name=p_check_name AND exact_head_sha=p_exact_head_sha
    AND repository_id=p_repository_id AND policy_digest=p_policy_digest AND revoked_at IS NULL
    AND check_name='adaptive-trust-ci/verified@' || left(policy_digest,12)
  FOR KEY SHARE;
  RETURN valid;
END;
$$;

CREATE FUNCTION factory.m0_exception_valid(
  p_exception_id text, p_issuer text, p_scope text, p_expires_at timestamptz,
  p_repository_id text, p_policy_digest char(64)
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE valid boolean := false;
BEGIN
  SELECT true INTO valid FROM factory.m0_bootstrap_exceptions
  WHERE exception_id=p_exception_id AND issuer=p_issuer AND scope=p_scope AND expires_at=p_expires_at
    AND repository_id=p_repository_id AND policy_digest=p_policy_digest AND action='task:intake'
    AND revoked_at IS NULL AND expires_at>clock_timestamp()
  FOR KEY SHARE;
  RETURN valid;
END;
$$;

REVOKE ALL ON FUNCTION factory.m0_observation_valid(timestamptz,text,char,text,char) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.m0_exception_valid(text,text,text,timestamptz,text,char) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION factory.m0_observation_valid(timestamptz,text,char,text,char) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.m0_exception_valid(text,text,text,timestamptz,text,char) TO factory_runtime;
