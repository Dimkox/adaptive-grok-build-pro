LOCK TABLE factory.tasks, factory.task_events, factory.runs,
  factory.capacity_allocations, factory.usage_observations,
  factory.kill_switches, factory.reconciliation_runs
  IN SHARE ROW EXCLUSIVE MODE;

ALTER TABLE factory.metric_counters RENAME TO metric_counters_pre_012_untrusted;
REVOKE ALL ON factory.metric_counters_pre_012_untrusted FROM factory_runtime, PUBLIC;

CREATE TABLE factory.metric_counters (
  singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
  accepted bigint NOT NULL DEFAULT 0 CHECK (accepted >= 0),
  superseded bigint NOT NULL DEFAULT 0 CHECK (superseded >= 0),
  queued bigint NOT NULL DEFAULT 0 CHECK (queued >= 0),
  retry bigint NOT NULL DEFAULT 0 CHECK (retry >= 0),
  dead bigint NOT NULL DEFAULT 0 CHECK (dead >= 0),
  transition_events bigint NOT NULL DEFAULT 0 CHECK (transition_events >= 0),
  live_leases bigint NOT NULL DEFAULT 0 CHECK (live_leases >= 0),
  reclaimed bigint NOT NULL DEFAULT 0 CHECK (reclaimed >= 0),
  fence_rejected bigint NOT NULL DEFAULT 0 CHECK (fence_rejected >= 0),
  active_capacity bigint NOT NULL DEFAULT 0 CHECK (active_capacity >= 0),
  cost_reserved_micros bigint NOT NULL DEFAULT 0 CHECK (cost_reserved_micros >= 0),
  cost_observed_micros bigint NOT NULL DEFAULT 0 CHECK (cost_observed_micros >= 0),
  tokens_reserved bigint NOT NULL DEFAULT 0 CHECK (tokens_reserved >= 0),
  tokens_observed bigint NOT NULL DEFAULT 0 CHECK (tokens_observed >= 0),
  wall_reserved_seconds bigint NOT NULL DEFAULT 0 CHECK (wall_reserved_seconds >= 0),
  output_observed_bytes bigint NOT NULL DEFAULT 0 CHECK (output_observed_bytes >= 0),
  accounting_blocked bigint NOT NULL DEFAULT 0 CHECK (accounting_blocked >= 0),
  active_kills bigint NOT NULL DEFAULT 0 CHECK (active_kills >= 0),
  reconciliation_runs bigint NOT NULL DEFAULT 0 CHECK (reconciliation_runs >= 0),
  reconciliation_candidates bigint NOT NULL DEFAULT 0 CHECK (reconciliation_candidates >= 0),
  repaired bigint NOT NULL DEFAULT 0 CHECK (repaired >= 0)
);

CREATE TABLE factory.kill_switch_heads (
  scope_key text PRIMARY KEY,
  switch_id uuid UNIQUE NOT NULL,
  created_at timestamptz NOT NULL,
  enabled boolean NOT NULL
);
INSERT INTO factory.kill_switch_heads(scope_key,switch_id,created_at,enabled)
SELECT DISTINCT ON (scope_key) scope_key,switch_id,created_at,enabled
FROM factory.kill_switches ORDER BY scope_key,created_at DESC,switch_id DESC;

INSERT INTO factory.metric_counters (
  singleton, accepted, superseded, queued, retry, dead, transition_events,
  live_leases, reclaimed, fence_rejected, active_capacity,
  cost_reserved_micros, cost_observed_micros, tokens_reserved, tokens_observed,
  wall_reserved_seconds, output_observed_bytes, accounting_blocked, active_kills,
  reconciliation_runs, reconciliation_candidates, repaired
)
SELECT true,
  (SELECT count(*) FROM factory.tasks),
  (SELECT count(*) FROM factory.tasks WHERE state='superseded'),
  (SELECT count(*) FROM factory.tasks WHERE state='queued'),
  (SELECT count(*) FROM factory.tasks WHERE state='retry'),
  (SELECT count(*) FROM factory.tasks WHERE state='dead'),
  (SELECT count(*) FROM factory.task_events),
  (SELECT count(*) FROM factory.runs WHERE state='leased' AND released_at IS NULL),
  (SELECT count(*) FROM factory.runs WHERE state='expired'),
  0,
  (SELECT count(*) FROM factory.capacity_allocations WHERE released_at IS NULL),
  (SELECT COALESCE(sum(cost_reserved_micros),0) FROM factory.tasks),
  (SELECT COALESCE(sum(cost_observed_micros),0) FROM factory.tasks),
  (SELECT COALESCE(sum(tokens_reserved),0) FROM factory.tasks),
  (SELECT COALESCE(sum(tokens_observed),0) FROM factory.tasks),
  (SELECT COALESCE(sum(wall_reserved_seconds),0) FROM factory.tasks),
  (SELECT COALESCE(sum(output_bytes),0) FROM factory.usage_observations),
  (SELECT count(*) FROM factory.tasks WHERE accounting_blocked),
  (SELECT count(*) FROM factory.kill_switch_heads WHERE enabled),
  (SELECT count(*) FROM factory.reconciliation_runs WHERE status='completed'),
  (SELECT COALESCE(sum(candidates),0) FROM factory.reconciliation_runs WHERE status='completed'),
  (SELECT COALESCE(sum(repaired),0) FROM factory.reconciliation_runs WHERE status='completed');

CREATE FUNCTION factory.metrics_task_delta() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  old_row factory.tasks%ROWTYPE;
  new_row factory.tasks%ROWTYPE;
BEGIN
  IF TG_OP IN ('UPDATE','DELETE') THEN old_row := OLD; END IF;
  IF TG_OP IN ('INSERT','UPDATE') THEN new_row := NEW; END IF;
  UPDATE factory.metric_counters SET
    accepted=accepted + CASE WHEN TG_OP IN ('INSERT','UPDATE') THEN 1 ELSE 0 END
      - CASE WHEN TG_OP IN ('UPDATE','DELETE') THEN 1 ELSE 0 END,
    superseded=superseded + CASE WHEN new_row.state='superseded' THEN 1 ELSE 0 END
      - CASE WHEN old_row.state='superseded' THEN 1 ELSE 0 END,
    queued=queued + CASE WHEN new_row.state='queued' THEN 1 ELSE 0 END
      - CASE WHEN old_row.state='queued' THEN 1 ELSE 0 END,
    retry=retry + CASE WHEN new_row.state='retry' THEN 1 ELSE 0 END
      - CASE WHEN old_row.state='retry' THEN 1 ELSE 0 END,
    dead=dead + CASE WHEN new_row.state='dead' THEN 1 ELSE 0 END
      - CASE WHEN old_row.state='dead' THEN 1 ELSE 0 END,
    cost_reserved_micros=cost_reserved_micros
      + COALESCE(new_row.cost_reserved_micros,0)-COALESCE(old_row.cost_reserved_micros,0),
    cost_observed_micros=cost_observed_micros
      + COALESCE(new_row.cost_observed_micros,0)-COALESCE(old_row.cost_observed_micros,0),
    tokens_reserved=tokens_reserved
      + COALESCE(new_row.tokens_reserved,0)-COALESCE(old_row.tokens_reserved,0),
    tokens_observed=tokens_observed
      + COALESCE(new_row.tokens_observed,0)-COALESCE(old_row.tokens_observed,0),
    wall_reserved_seconds=wall_reserved_seconds
      + COALESCE(new_row.wall_reserved_seconds,0)-COALESCE(old_row.wall_reserved_seconds,0),
    accounting_blocked=accounting_blocked
      + CASE WHEN new_row.accounting_blocked THEN 1 ELSE 0 END
      - CASE WHEN old_row.accounting_blocked THEN 1 ELSE 0 END
  WHERE singleton;
  RETURN NULL;
END;
$$;

CREATE FUNCTION factory.metrics_event_delta() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  UPDATE factory.metric_counters SET transition_events=transition_events
    + CASE WHEN TG_OP='INSERT' THEN 1 ELSE -1 END WHERE singleton;
  RETURN NULL;
END;
$$;

CREATE FUNCTION factory.metrics_run_delta() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  old_live integer := 0;
  new_live integer := 0;
  old_reclaimed integer := 0;
  new_reclaimed integer := 0;
BEGIN
  IF TG_OP IN ('UPDATE','DELETE') THEN
    old_live := CASE WHEN OLD.state='leased' AND OLD.released_at IS NULL THEN 1 ELSE 0 END;
    old_reclaimed := CASE WHEN OLD.state='expired' THEN 1 ELSE 0 END;
  END IF;
  IF TG_OP IN ('INSERT','UPDATE') THEN
    new_live := CASE WHEN NEW.state='leased' AND NEW.released_at IS NULL THEN 1 ELSE 0 END;
    new_reclaimed := CASE WHEN NEW.state='expired' THEN 1 ELSE 0 END;
  END IF;
  UPDATE factory.metric_counters SET
    live_leases=live_leases+new_live-old_live,
    reclaimed=reclaimed+new_reclaimed-old_reclaimed
  WHERE singleton;
  RETURN NULL;
END;
$$;

CREATE FUNCTION factory.metrics_capacity_delta() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  old_active integer := 0;
  new_active integer := 0;
BEGIN
  IF TG_OP IN ('UPDATE','DELETE') THEN old_active := CASE WHEN OLD.released_at IS NULL THEN 1 ELSE 0 END; END IF;
  IF TG_OP IN ('INSERT','UPDATE') THEN new_active := CASE WHEN NEW.released_at IS NULL THEN 1 ELSE 0 END; END IF;
  UPDATE factory.metric_counters SET active_capacity=active_capacity+new_active-old_active WHERE singleton;
  RETURN NULL;
END;
$$;

CREATE FUNCTION factory.metrics_usage_delta() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  UPDATE factory.metric_counters SET output_observed_bytes=output_observed_bytes
    + CASE WHEN TG_OP IN ('INSERT','UPDATE') THEN NEW.output_bytes ELSE 0 END
    - CASE WHEN TG_OP IN ('UPDATE','DELETE') THEN OLD.output_bytes ELSE 0 END
  WHERE singleton;
  RETURN NULL;
END;
$$;

CREATE FUNCTION factory.metrics_kill_delta() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  INSERT INTO factory.kill_switch_heads(scope_key,switch_id,created_at,enabled)
  VALUES (NEW.scope_key,NEW.switch_id,NEW.created_at,NEW.enabled)
  ON CONFLICT(scope_key) DO UPDATE SET
    switch_id=EXCLUDED.switch_id,created_at=EXCLUDED.created_at,enabled=EXCLUDED.enabled
  WHERE (EXCLUDED.created_at,EXCLUDED.switch_id) >
        (factory.kill_switch_heads.created_at,factory.kill_switch_heads.switch_id);
  RETURN NULL;
END;
$$;

CREATE FUNCTION factory.metrics_kill_head_delta() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  UPDATE factory.metric_counters SET active_kills=active_kills
    + CASE WHEN NEW.enabled THEN 1 ELSE 0 END
    - CASE WHEN TG_OP='UPDATE' AND OLD.enabled THEN 1 ELSE 0 END
  WHERE singleton;
  RETURN NULL;
END;
$$;

CREATE FUNCTION factory.metrics_reconciliation_delta() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  old_completed integer := 0;
  new_completed integer := 0;
BEGIN
  IF TG_OP IN ('UPDATE','DELETE') THEN old_completed := CASE WHEN OLD.status='completed' THEN 1 ELSE 0 END; END IF;
  IF TG_OP IN ('INSERT','UPDATE') THEN new_completed := CASE WHEN NEW.status='completed' THEN 1 ELSE 0 END; END IF;
  IF old_completed=0 AND new_completed=0 THEN RETURN NULL; END IF;
  UPDATE factory.metric_counters SET
    reconciliation_runs=reconciliation_runs+new_completed-old_completed,
    reconciliation_candidates=reconciliation_candidates
      + CASE WHEN new_completed=1 THEN NEW.candidates ELSE 0 END
      - CASE WHEN old_completed=1 THEN OLD.candidates ELSE 0 END,
    repaired=repaired
      + CASE WHEN new_completed=1 THEN NEW.repaired ELSE 0 END
      - CASE WHEN old_completed=1 THEN OLD.repaired ELSE 0 END
  WHERE singleton;
  RETURN NULL;
END;
$$;

CREATE TRIGGER metrics_tasks AFTER INSERT OR UPDATE OR DELETE ON factory.tasks
  FOR EACH ROW EXECUTE FUNCTION factory.metrics_task_delta();
CREATE TRIGGER metrics_events AFTER INSERT OR DELETE ON factory.task_events
  FOR EACH ROW EXECUTE FUNCTION factory.metrics_event_delta();
CREATE TRIGGER metrics_runs AFTER INSERT OR UPDATE OR DELETE ON factory.runs
  FOR EACH ROW EXECUTE FUNCTION factory.metrics_run_delta();
CREATE TRIGGER metrics_capacity AFTER INSERT OR UPDATE OR DELETE ON factory.capacity_allocations
  FOR EACH ROW EXECUTE FUNCTION factory.metrics_capacity_delta();
CREATE TRIGGER metrics_usage AFTER INSERT OR UPDATE OR DELETE ON factory.usage_observations
  FOR EACH ROW EXECUTE FUNCTION factory.metrics_usage_delta();
CREATE TRIGGER metrics_kills AFTER INSERT ON factory.kill_switches
  FOR EACH ROW EXECUTE FUNCTION factory.metrics_kill_delta();
CREATE TRIGGER metrics_kill_heads AFTER INSERT OR UPDATE ON factory.kill_switch_heads
  FOR EACH ROW EXECUTE FUNCTION factory.metrics_kill_head_delta();
CREATE TRIGGER metrics_reconciliation AFTER INSERT OR UPDATE OR DELETE ON factory.reconciliation_runs
  FOR EACH ROW EXECUTE FUNCTION factory.metrics_reconciliation_delta();

CREATE FUNCTION factory.increment_fence_rejected() RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  result bigint;
BEGIN
  UPDATE factory.metric_counters SET fence_rejected=CASE
    WHEN fence_rejected<9223372036854775807 THEN fence_rejected+1 ELSE fence_rejected END
  WHERE singleton RETURNING fence_rejected INTO STRICT result;
  RETURN result;
END;
$$;

CREATE FUNCTION factory.read_metrics_snapshot() RETURNS SETOF factory.metric_counters
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  IF current_setting('statement_timeout')::interval='0 seconds'::interval
     OR current_setting('statement_timeout')::interval>'5 seconds'::interval THEN
    RAISE EXCEPTION 'bounded metrics statement timeout required';
  END IF;
  IF current_setting('lock_timeout')::interval='0 seconds'::interval
     OR current_setting('lock_timeout')::interval>'500 milliseconds'::interval THEN
    RAISE EXCEPTION 'bounded metrics lock timeout required';
  END IF;
  RETURN QUERY SELECT * FROM factory.metric_counters WHERE singleton;
END;
$$;

REVOKE SELECT, INSERT, UPDATE, DELETE ON factory.metric_counters FROM factory_runtime;
REVOKE ALL ON factory.metric_counters, factory.kill_switch_heads FROM PUBLIC;
REVOKE ALL ON factory.metric_counters FROM factory_runtime;
REVOKE ALL ON factory.kill_switch_heads FROM factory_runtime;
REVOKE ALL ON FUNCTION factory.increment_fence_rejected() FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.read_metrics_snapshot() FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.metrics_task_delta() FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.metrics_event_delta() FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.metrics_run_delta() FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.metrics_capacity_delta() FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.metrics_usage_delta() FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.metrics_kill_delta() FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.metrics_kill_head_delta() FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.metrics_reconciliation_delta() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION factory.increment_fence_rejected() TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.read_metrics_snapshot() TO factory_runtime;
