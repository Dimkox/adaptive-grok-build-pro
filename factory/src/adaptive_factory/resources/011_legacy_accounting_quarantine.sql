UPDATE factory.tasks AS task
SET state=CASE
      WHEN task.state='ready_for_human' AND EXISTS (
        SELECT 1 FROM factory.tasks AS newer
        WHERE newer.repository_id=task.repository_id
          AND newer.source_type=task.source_type
          AND newer.source_id=task.source_id
          AND newer.generation>task.generation
      ) THEN 'superseded'
      ELSE 'needs_human'
    END,
    accounting_blocked=true,
    updated_at=clock_timestamp()
WHERE (
    task.state IN ('queued','retry') AND task.accounting_blocked
  ) OR (
    task.state='ready_for_human' AND (
      task.accounting_blocked
      OR task.cost_reserved_micros<>0
      OR task.tokens_reserved<>0
      OR task.wall_reserved_seconds<>0
      OR EXISTS (
        SELECT 1 FROM factory.budget_reservations AS reservation
        WHERE reservation.task_id=task.task_id AND reservation.released_at IS NULL
      )
    )
  );
