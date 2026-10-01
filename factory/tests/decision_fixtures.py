"""Dependency-free factual fixtures shared by direct and discovered Factory tests."""


def decision_facts():
    return dict(
        schema_version=1,
        decision_id="decision-1",
        repository_id="owner/project",
        task_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        attempt_id="00000000-0000-0000-0000-000000000003",
        fence=1,
        observed_at="2026-09-30T12:00:00Z",
        decision_kind="state",
        rule_id="RULE-1",
        rule_version="1",
        facts=[
            dict(name="from_state", value="leased"),
            dict(name="target", value="analyzing"),
        ],
        outcome="observed",
        reason_code="phase_started",
        base_sha="1" * 40,
        head_sha="2" * 40,
        context_digest="3" * 64,
        spec_digest="4" * 64,
        profile_digest="5" * 64,
        evidence_refs=["evidence/report.json"],
        constraints=["scope_bound"],
        next_step="verify",
        supersedes=None,
    )
