CREATE OR REPLACE FUNCTION factory.m0_observation_valid(
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
  FOR SHARE;
  RETURN valid;
END;
$$;

CREATE OR REPLACE FUNCTION factory.m0_exception_valid(
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
  FOR SHARE;
  RETURN valid;
END;
$$;

REVOKE ALL ON FUNCTION factory.m0_observation_valid(timestamptz,text,char,text,char) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.m0_exception_valid(text,text,text,timestamptz,text,char) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION factory.m0_observation_valid(timestamptz,text,char,text,char) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.m0_exception_valid(text,text,text,timestamptz,text,char) TO factory_runtime;

ALTER TABLE factory.task_events
  ADD COLUMN mandatory_cleanup boolean NOT NULL DEFAULT false;

WITH active_reservations AS (
  SELECT task_id,
    count(*) AS active_count,
    COALESCE(sum(cost_usd_micros),0) AS cost_reserved_micros,
    COALESCE(sum(token_units),0) AS tokens_reserved,
    COALESCE(sum(wall_seconds),0) AS wall_reserved_seconds
  FROM factory.budget_reservations
  WHERE released_at IS NULL
  GROUP BY task_id
)
UPDATE factory.tasks AS task
SET state='needs_human', accounting_blocked=true, updated_at=clock_timestamp()
FROM active_reservations AS reservation
WHERE task.task_id=reservation.task_id
  AND task.state IN ('queued','retry')
  AND (
    reservation.active_count>0
    OR task.cost_reserved_micros<>reservation.cost_reserved_micros
    OR task.tokens_reserved<>reservation.tokens_reserved
    OR task.wall_reserved_seconds<>reservation.wall_reserved_seconds
  );

UPDATE factory.tasks AS task
SET state='needs_human', accounting_blocked=true, updated_at=clock_timestamp()
WHERE task.state IN ('queued','retry')
  AND NOT EXISTS (
    SELECT 1 FROM factory.budget_reservations AS reservation
    WHERE reservation.task_id=task.task_id AND reservation.released_at IS NULL
  )
  AND (task.cost_reserved_micros<>0 OR task.tokens_reserved<>0 OR task.wall_reserved_seconds<>0);
