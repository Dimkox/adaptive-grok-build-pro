import unittest

from adaptive_factory.brokers import (
    ArtifactProposal,
    BrokerError,
    NoteProposal,
    ProposalBroker,
    ProposalContext,
    TerminalProposal,
    UsageProposal,
    proposal_idempotency_key,
)
from adaptive_factory.protocol import CanonicalEvent


TASK = "task-001"
RUN = "run-001"
PACKET = "a" * 64


def context(**overrides):
    values = {
        "task_id": TASK,
        "run_id": RUN,
        "owner": "writer-01",
        "fence": 7,
        "packet_digest": PACKET,
        "role": "writer",
        "repository_id": "owner/repository",
        "workspace_handle": "workspace:" + "d" * 64,
        "allowed_paths": ("artifacts", "factory"),
        "allowed_artifact_classes": ("patch", "report"),
        "max_note_bytes": 4096,
        "max_artifact_bytes": 1_000_000,
        "max_output_bytes": 1_000_000,
        "max_cost_usd_micros": 1_000_000,
        "max_token_units": 100_000,
        "declared_capabilities": ("artifacts", "notes", "structured_output", "usage"),
    }
    values.update(overrides)
    return ProposalContext(**values)


def event(sequence, event_type, payload, **identity):
    return CanonicalEvent(
        "adaptive-factory.execution/v1",
        identity.get("task_id", TASK),
        identity.get("run_id", RUN),
        identity.get("packet_digest", PACKET),
        sequence,
        event_type,
        payload,
    )


class BrokerTests(unittest.TestCase):
    def test_note_is_bounded_redacted_and_provenance_bound(self):
        proposal = ProposalBroker().accept(
            event(1, "note.proposed", {"note_type": "conclusion", "body": "token sk-secret conclusion", "evidence": ["factory/src/a.py"]}),
            context(),
            owner="writer-01",
            fence=7,
        )
        self.assertIsInstance(proposal, NoteProposal)
        self.assertEqual(proposal.body, "token [REDACTED] conclusion")
        self.assertEqual(proposal.evidence, ("factory/src/a.py",))
        self.assertEqual(len(proposal.idempotency_key), 64)

    def test_forbidden_note_categories_are_rejected_before_proposal_creation(self):
        for note_type in (
            "analysis", "Reasoning", "scratch-pad", " raw prompt ",
            "model_analysis", "private-reasoning", "raw_prompt_dump",
            "private_thoughts", "hidden_cot", "raw_response",
            "internal_deliberation", "late", "x",
        ):
            with self.subTest(note_type=note_type), self.assertRaisesRegex(
                BrokerError, "forbidden_note_type"
            ):
                ProposalBroker().accept(
                    event(
                        1, "note.proposed",
                        {"note_type": note_type, "body": "safe", "evidence": []},
                    ),
                    context(), owner="writer-01", fence=7,
                )

    def test_redaction_covers_bearer_aws_keyed_secrets_and_complete_pem(self):
        secret_text = (
            "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.signature "
            "aws=AKIAABCDEFGHIJKLMNOP api_key=fixture-secret "
            "AWS_SECRET_ACCESS_KEY=aws-secret client_secret=client-secret "
            "refresh_token=refresh-secret credential=credential-secret "
            "OPENAI_API_KEY=openai-secret GITHUB_TOKEN=github-secret "
            "AWS_SESSION_TOKEN=session-secret DATABASE_PASSWORD=db-secret "
            "SECRET_KEY=key-secret PRIVATE_KEY=private-secret TOKEN=token-secret "
            "{\"api_key\":\"json-secret\"} {'access_token':'python-secret'}\n"
            "-----BEGIN PRIVATE KEY-----\nprivate-material\n-----END PRIVATE KEY-----"
        )
        proposal = ProposalBroker().accept(
            event(
                1,
                "note.proposed",
                {"note_type": "finding", "body": secret_text, "evidence": []},
            ),
            context(), owner="writer-01", fence=7,
        )
        for forbidden in (
            "Bearer", "AKIA", "fixture-secret", "aws-secret", "client-secret",
            "refresh-secret", "credential-secret", "private-material",
            "openai-secret", "github-secret", "session-secret", "db-secret",
            "key-secret", "private-secret", "token-secret", "json-secret",
            "python-secret",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, proposal.body)
        self.assertIn("[REDACTED]", proposal.body)
        with self.assertRaisesRegex(BrokerError, "secret_content"):
            ProposalBroker().accept(
                event(
                    2,
                    "note.proposed",
                    {
                        "note_type": "finding",
                        "body": "-----BEGIN PRIVATE KEY-----\nincomplete",
                        "evidence": [],
                    },
                ),
                context(), owner="writer-01", fence=7,
            )

    def test_raw_secret_size_is_bounded_before_redaction(self):
        large_pem = (
            "-----BEGIN PRIVATE KEY-----\n"
            + "x" * 256
            + "\n-----END PRIVATE KEY-----"
        )
        with self.assertRaisesRegex(BrokerError, "note_too_large"):
            ProposalBroker().accept(
                event(
                    1, "note.proposed",
                    {"note_type": "finding", "body": large_pem, "evidence": []},
                ),
                context(max_note_bytes=64), owner="writer-01", fence=7,
            )

    def test_authorization_bearer_redaction_consumes_the_credential_tail(self):
        credential = "TOKEN-credential-tail"
        proposal = ProposalBroker().accept(
            event(
                1, "note.proposed",
                {
                    "note_type": "finding",
                    "body": f"Authorization: Bearer {credential}",
                    "evidence": [],
                },
            ),
            context(), owner="writer-01", fence=7,
        )
        self.assertNotIn(credential, proposal.body)

    def test_all_authorization_schemes_and_secret_shaped_identity_fields_fail_closed(self):
        proposal = ProposalBroker().accept(
            event(
                1,
                "note.proposed",
                {
                    "note_type": "finding",
                    "body": "Authorization: Basic Zml4dHVyZS1jcmVkZW50aWFs\n"
                    "Authorization: Token fixture-tail\n"
                    "Authorization=Basic equals-tail\n"
                    "HTTP_AUTHORIZATION=Basic http-tail\n"
                    "PROXY_AUTHORIZATION: Basic proxy-tail",
                    "evidence": [],
                },
            ),
            context(), owner="writer-01", fence=7,
        )
        self.assertNotIn("Zml4dHVyZS1jcmVkZW50aWFs", proposal.body)
        self.assertNotIn("fixture-tail", proposal.body)
        self.assertNotIn("equals-tail", proposal.body)
        self.assertNotIn("http-tail", proposal.body)
        self.assertNotIn("proxy-tail", proposal.body)
        for event_type, payload, error in (
            (
                "note.proposed",
                {"note_type": "ghp_secret", "body": "safe", "evidence": []},
                "forbidden_note_type",
            ),
            (
                "note.proposed",
                {"note_type": "finding", "body": "safe", "evidence": ["factory/ghp_secret"]},
                "secret_identity",
            ),
            (
                "usage.reported",
                {
                    "provider_call_id": "client_secret=fixture-tail",
                    "price_table_digest": "a" * 64,
                    "input_tokens": 1,
                    "output_tokens": 1,
                    "reasoning_tokens": 0,
                    "cost_usd_micros": 1,
                    "output_bytes": 1,
                },
                "secret_identity",
            ),
        ):
            with self.subTest(event_type=event_type), self.assertRaisesRegex(
                BrokerError, error
            ):
                ProposalBroker().accept(
                    event(2, event_type, payload), context(), owner="writer-01", fence=7,
                )

    def test_structured_note_and_terminal_text_is_never_stringified(self):
        cases = (
            event(
                1, "note.proposed",
                {"note_type": "finding", "body": {"reasoning": "private"}, "evidence": []},
            ),
            event(1, "run.completed", {"summary": {"reasoning": "private"}}),
            event(
                1, "run.failed",
                {"failure_class": "protocol", "diagnostic": {"reasoning": "private"}},
            ),
        )
        for value in cases:
            with self.subTest(event_type=value.event_type), self.assertRaisesRegex(
                BrokerError, "(?:executable_note|terminal_fields)"
            ):
                ProposalBroker().accept(value, context(), owner="writer-01", fence=7)

    def test_note_and_artifact_must_stay_in_authoritative_allowed_paths(self):
        cases = (
            event(
                1, "note.proposed",
                {"note_type": "finding", "body": "safe", "evidence": ["outside/a.py"]},
            ),
            event(
                1, "artifact.proposed",
                {
                    "artifact_class": "report", "path": "outside/report.json",
                    "sha256": "b" * 64, "size_bytes": 1, "media_type": "application/json",
                },
            ),
        )
        for value in cases:
            with self.subTest(event_type=value.event_type), self.assertRaisesRegex(
                BrokerError, "path_forbidden"
            ):
                ProposalBroker().accept(value, context(), owner="writer-01", fence=7)

    def test_artifact_requires_server_side_attestation(self):
        value = event(
            1, "artifact.proposed",
            {
                "artifact_class": "report", "path": "artifacts/report.json",
                "sha256": "b" * 64, "size_bytes": 20, "media_type": "application/json",
            },
        )
        with self.assertRaisesRegex(BrokerError, "artifact_attestation"):
            ProposalBroker().accept(value, context(), owner="writer-01", fence=7)

    def test_artifact_is_writer_only_before_trusted_attestation(self):
        value = event(
            1, "artifact.proposed",
            {
                "artifact_class": "report", "path": "artifacts/report.json",
                "sha256": "b" * 64, "size_bytes": 20, "media_type": "application/json",
            },
        )
        with self.assertRaisesRegex(BrokerError, "artifact_role"):
            ProposalBroker().accept(
                value,
                context(role="reader"),
                owner="writer-01",
                fence=7,
                artifact_attestation_digest="d" * 64,
            )

    def test_terminal_text_required_by_sql_is_non_empty_in_broker(self):
        cases = (
            event(1, "run.completed", {"summary": ""}),
            event(1, "run.failed", {"failure_class": "protocol", "diagnostic": ""}),
            event(1, "run.needs_human", {"reason": "", "diagnostic": "bounded"}),
            event(1, "run.needs_human", {"reason": "bounded", "diagnostic": ""}),
        )
        for value in cases:
            with self.subTest(event_type=value.event_type, payload=value.payload), \
                    self.assertRaisesRegex(BrokerError, "terminal_fields"):
                ProposalBroker().accept(
                    value, context(), owner="writer-01", fence=7,
                )

    def test_derived_terminal_summary_is_built_from_redacted_components(self):
        cases = (
            event(
                1,
                "run.failed",
                {
                    "failure_class": "protocol",
                    "diagnostic": "Authorization=fixture-secret detail",
                },
            ),
            event(
                1,
                "run.needs_human",
                {
                    "reason": "Authorization=fixture-secret",
                    "diagnostic": "bounded detail",
                },
            ),
        )
        for value in cases:
            proposal = ProposalBroker().accept(
                value, context(), owner="writer-01", fence=7,
            )
            if value.event_type == "run.failed":
                self.assertEqual(
                    proposal.summary,
                    f"{proposal.failure_class}: {proposal.diagnostic}",
                )
            else:
                self.assertEqual(
                    proposal.summary,
                    f"{proposal.reason}: {proposal.diagnostic}",
                )
            self.assertNotIn("fixture-secret", proposal.summary)

    def test_terminal_failure_reason_bound_matches_persisted_result(self):
        for value in (
            event(
                1,
                "run.failed",
                {"failure_class": "protocol", "diagnostic": "x" * 4097},
            ),
            event(
                1,
                "run.needs_human",
                {"reason": "x" * 4097, "diagnostic": "bounded"},
            ),
        ):
            with self.subTest(event_type=value.event_type), self.assertRaisesRegex(
                BrokerError, "terminal_too_large"
            ):
                ProposalBroker().accept(
                    value,
                    context(max_note_bytes=65_536),
                    owner="writer-01",
                    fence=7,
                )

    def test_result_carried_terminal_text_is_nfc_without_c0_controls(self):
        cases = (
            event(
                1,
                "run.failed",
                {"failure_class": "protocol", "diagnostic": "line1\nline2"},
            ),
            event(
                1,
                "run.failed",
                {"failure_class": "protocol", "diagnostic": "e\u0301"},
            ),
            event(
                1,
                "run.needs_human",
                {"reason": "line1\nline2", "diagnostic": "bounded"},
            ),
            event(
                1,
                "run.needs_human",
                {"reason": "e\u0301", "diagnostic": "bounded"},
            ),
        )
        for value in cases:
            with self.subTest(event_type=value.event_type, payload=value.payload), \
                    self.assertRaisesRegex(BrokerError, "terminal_text"):
                ProposalBroker().accept(
                    value,
                    context(max_note_bytes=65_536),
                    owner="writer-01",
                    fence=7,
                )

    def test_artifact_usage_and_terminal_are_closed_values(self):
        broker = ProposalBroker()
        artifact = broker.accept(event(1, "artifact.proposed", {"artifact_class": "report", "path": "artifacts/report.json", "sha256": "b" * 64, "size_bytes": 20, "media_type": "application/json"}), context(), owner="writer-01", fence=7, artifact_attestation_digest="d" * 64)
        usage = broker.accept(event(2, "usage.reported", {"provider_call_id": "call-1", "price_table_digest": "c" * 64, "input_tokens": 10, "output_tokens": 4, "reasoning_tokens": 2, "cost_usd_micros": 30, "output_bytes": 20}), context(), owner="writer-01", fence=7)
        terminal = broker.accept(event(3, "run.completed", {"summary": "complete"}), context(), owner="writer-01", fence=7)
        self.assertIsInstance(artifact, ArtifactProposal)
        self.assertIsInstance(usage, UsageProposal)
        self.assertIsInstance(terminal, TerminalProposal)
        self.assertEqual(usage.total_tokens, 16)
        self.assertEqual((artifact.author_role, artifact.artifact_attestation_digest), ("writer", "d" * 64))
        self.assertEqual(proposal_idempotency_key(artifact), artifact.idempotency_key)

    def test_artifact_digest_binds_authoritative_role_and_attestation(self):
        value = event(
            1, "artifact.proposed",
            {
                "artifact_class": "report", "path": "artifacts/report.json",
                "sha256": "b" * 64, "size_bytes": 20, "media_type": "application/json",
            },
        )
        writer = ProposalBroker().accept(
            value, context(), owner="writer-01", fence=7,
            artifact_attestation_digest="d" * 64,
        )
        changed_attestation = ProposalBroker().accept(
            value, context(), owner="writer-01", fence=7,
            artifact_attestation_digest="e" * 64,
        )
        self.assertNotEqual(writer.idempotency_key, changed_attestation.idempotency_key)

    def test_stale_identity_owner_or_fence_fails(self):
        cases = [
            (event(1, "run.completed", {"summary": "x"}, task_id="other"), "identity_mismatch", "writer-01", 7),
            (event(1, "run.completed", {"summary": "x"}), "owner_mismatch", "other", 7),
            (event(1, "run.completed", {"summary": "x"}), "stale_fence", "writer-01", 6),
        ]
        for value, code, owner, fence in cases:
            with self.subTest(code=code), self.assertRaisesRegex(BrokerError, code):
                ProposalBroker().accept(value, context(), owner=owner, fence=fence)

    def test_undeclared_proposal_capability_fails_closed(self):
        with self.assertRaisesRegex(BrokerError, "undeclared_capability"):
            ProposalBroker().accept(
                event(1, "note.proposed", {"note_type": "finding", "body": "safe", "evidence": []}),
                context(declared_capabilities=("usage",)), owner="writer-01", fence=7,
            )

    def test_executable_note_artifact_escape_and_missing_usage_fail(self):
        cases = [
            (event(1, "note.proposed", {"note_type": "conclusion", "body": "#!/bin/sh\ngit push", "evidence": []}), "executable_note"),
            (event(1, "artifact.proposed", {"artifact_class": "report", "path": "../outside", "sha256": "b" * 64, "size_bytes": 1, "media_type": "text/plain"}), "invalid_artifact_path"),
            (event(1, "artifact.proposed", {"artifact_class": "binary", "path": "artifacts/a", "sha256": "b" * 64, "size_bytes": 1, "media_type": "application/octet-stream"}), "artifact_class"),
            (event(1, "usage.reported", {"provider_call_id": "call-1", "input_tokens": 1, "output_tokens": 1, "reasoning_tokens": 0, "cost_usd_micros": 0, "output_bytes": 1}), "missing_usage"),
        ]
        for value, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(BrokerError, code):
                ProposalBroker().accept(value, context(), owner="writer-01", fence=7)

    def test_budget_overflow_and_duplicate_terminal_fail(self):
        broker = ProposalBroker()
        with self.assertRaisesRegex(BrokerError, "budget_exceeded"):
            broker.accept(event(1, "usage.reported", {"provider_call_id": "call-1", "price_table_digest": "c" * 64, "input_tokens": 100_001, "output_tokens": 0, "reasoning_tokens": 0, "cost_usd_micros": 1, "output_bytes": 1}), context(), owner="writer-01", fence=7)
        broker.accept(event(2, "run.completed", {"summary": "one"}), context(), owner="writer-01", fence=7)
        with self.assertRaisesRegex(BrokerError, "duplicate_terminal"):
            broker.accept(event(3, "run.failed", {"failure_class": "protocol", "diagnostic": "two"}), context(), owner="writer-01", fence=7)


if __name__ == "__main__":
    unittest.main()
