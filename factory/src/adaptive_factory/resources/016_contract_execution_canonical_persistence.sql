-- Contract phase for constraints superseded by canonical persistence.
ALTER TABLE factory.execution_proposals
  DROP CONSTRAINT execution_proposals_body_check;

-- A snapshot can legitimately be reused as evidence for separately fenced runs.
ALTER TABLE factory.workspace_results
  DROP CONSTRAINT workspace_results_workspace_snapshot_digest_key;
