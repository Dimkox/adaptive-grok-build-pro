"""Closed schema-025/026 reset operations; caller owns target and transaction."""

RESET_SQL = "TRUNCATE factory.next_model_request_outbox_v1, factory.result_admission_commands_v1, factory.result_sources_v1, factory.decision_records_v1, factory.semantic_recovery_records, factory.semantic_escalations, factory.semantic_child_task_bindings, factory.semantic_child_proposals, factory.semantic_directives, factory.semantic_verdicts, factory.semantic_coverage, factory.semantic_findings, factory.semantic_assignments, factory.semantic_metric_events, factory.semantic_command_results, factory.semantic_subjects, factory.execution_recovery_outcomes, factory.execution_recovery_claims, factory.execution_recovery_jobs, factory.workspace_results, factory.execution_artifact_attestations, factory.execution_proposals, factory.execution_stage_events, factory.execution_manifests, factory.execution_packets, factory.audit_log, factory.audit_heads, factory.task_events, factory.command_results, factory.metric_counters, factory.budget_reservations, factory.usage_observations, factory.capacity_allocations, factory.attempts, factory.runs, factory.lease_sequences, factory.kill_switches, factory.reconciliation_runs, factory.tasks, factory.accepted_intents, factory.intake_identities, factory.m0_authority_observations, factory.m0_bootstrap_exceptions RESTART IDENTITY"


M7_TABLES = (
    "m7_command_results", "m7_contexts", "m7_checks",
    "m7_outcomes", "m7_bundles", "m7_source_bindings",
)
RESET_026_SQL = (
    "TRUNCATE " + ", ".join("factory." + table for table in M7_TABLES)
    + ", " + RESET_SQL.removeprefix("TRUNCATE ")
)


def reset_fixture_tables(cursor, *, schema_version: int | None = None) -> None:
    if schema_version is None:
        cursor.execute("SELECT version FROM factory.schema_migrations ORDER BY version DESC LIMIT 1")
        row = cursor.fetchone()
        schema_version = row[0] if row else None
    if type(schema_version) is not int or schema_version not in (25, 26):
        raise ValueError("fixture reset supports only explicit schema 025/026")
    cursor.execute(RESET_SQL if schema_version == 25 else RESET_026_SQL)
