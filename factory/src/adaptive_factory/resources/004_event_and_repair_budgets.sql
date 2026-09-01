ALTER TABLE factory.tasks
  ADD COLUMN repair_limit integer NOT NULL DEFAULT 3 CHECK (repair_limit BETWEEN 1 AND 3),
  ADD COLUMN repair_count integer NOT NULL DEFAULT 0 CHECK (repair_count >= 0 AND repair_count <= repair_limit);

ALTER TABLE factory.tasks ALTER COLUMN repair_limit DROP DEFAULT;
