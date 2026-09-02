ALTER TABLE factory.tasks
  ADD COLUMN infrastructure_retries smallint;

UPDATE factory.tasks AS task
SET infrastructure_retries = CASE
  WHEN jsonb_typeof(intent.body #> '{limits,infrastructure_retries}') = 'number'
    AND intent.body #>> '{limits,infrastructure_retries}' IN ('0','1','2')
  THEN (intent.body #>> '{limits,infrastructure_retries}')::smallint
  ELSE 2
END
FROM factory.accepted_intents AS intent
WHERE intent.intent_id = task.intent_id;

ALTER TABLE factory.tasks
  ALTER COLUMN infrastructure_retries SET DEFAULT 2,
  ALTER COLUMN infrastructure_retries SET NOT NULL,
  ADD CONSTRAINT tasks_infrastructure_retries_closed
    CHECK (infrastructure_retries BETWEEN 0 AND 2);
