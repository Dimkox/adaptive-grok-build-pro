UPDATE factory.tasks AS task
SET state='needs_human', accounting_blocked=true, updated_at=clock_timestamp()
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
