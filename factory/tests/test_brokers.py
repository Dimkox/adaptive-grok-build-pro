import unittest

from adaptive_factory.brokers import (
    ArtifactProposal,
    BrokerError,
    NoteProposal,
    ProposalBroker,
    ProposalContext,
    TerminalProposal,
    UsageProposal,
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

    def test_artifact_usage_and_terminal_are_closed_values(self):
        broker = ProposalBroker()
        artifact = broker.accept(event(1, "artifact.proposed", {"artifact_class": "report", "path": "artifacts/report.json", "sha256": "b" * 64, "size_bytes": 20, "media_type": "application/json"}), context(), owner="writer-01", fence=7)
        usage = broker.accept(event(2, "usage.reported", {"provider_call_id": "call-1", "price_table_digest": "c" * 64, "input_tokens": 10, "output_tokens": 4, "reasoning_tokens": 2, "cost_usd_micros": 30, "output_bytes": 20}), context(), owner="writer-01", fence=7)
        terminal = broker.accept(event(3, "run.completed", {"summary": "complete"}), context(), owner="writer-01", fence=7)
        self.assertIsInstance(artifact, ArtifactProposal)
        self.assertIsInstance(usage, UsageProposal)
        self.assertIsInstance(terminal, TerminalProposal)
        self.assertEqual(usage.total_tokens, 16)

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
