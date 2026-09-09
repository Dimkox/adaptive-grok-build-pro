from pathlib import Path
import unittest

from adaptive_factory.adapters import (
    AdapterError,
    AdapterRegistry,
    CodexAdapter,
    GrokAdapter,
    TrustedExecutionProfile,
    select_adapter,
)
from adaptive_factory.execution_contracts import ExecutionContractError, ExecutionSelectionV1
from factory.tests.test_execution_contracts import valid_packet


FIXTURES = Path(__file__).with_name("fixtures")


class AdapterTests(unittest.TestCase):
    @staticmethod
    def selection():
        packet = valid_packet()
        return ExecutionSelectionV1.from_dict({
            "provider": packet["provider"],
            "capability_policy": packet["capability_policy"],
            "plan": packet["plan"],
            "workspace_handle": packet["workspace_handle"],
            "prompt_template_digest": "7" * 64,
            "role_definition_digest": "8" * 64,
            "tool_policy_digest": "9" * 64,
            "output_schema_digest": "a" * 64,
        })

    def test_codex_01521_fixture_projects_safe_canonical_lifecycle(self):
        adapter = CodexAdapter()
        events = adapter.translate(
            (FIXTURES / "codex-0.152.1" / "success.jsonl").read_bytes(),
            task_id="task-001",
            run_id="run-001",
            packet_digest="a" * 64,
        )
        self.assertEqual(adapter.conformance.native_version, "0.152.1")
        self.assertEqual(adapter.conformance.distribution_digest_hint, "b8201824…06f9")
        self.assertTrue(adapter.conformance.fixture_conformant)
        self.assertEqual(tuple(item["event_type"] for item in events), ("adapter.ready", "run.started", "note.proposed", "usage.reported", "run.completed"))
        self.assertNotIn("private scratch", repr(events))
        self.assertFalse(hasattr(adapter, "invoke"))

    def test_grok_1017_fixture_is_translatable_but_ineligible(self):
        adapter = GrokAdapter()
        events = adapter.translate(
            (FIXTURES / "grok-1.0.17" / "success.jsonl").read_bytes(),
            task_id="task-001",
            run_id="run-001",
            packet_digest="a" * 64,
        )
        self.assertEqual(adapter.conformance.native_version, "1.0.17")
        self.assertEqual(adapter.conformance.distribution_digest_hint, "82595e26…4568")
        self.assertFalse(adapter.conformance.execution_eligible)
        self.assertIn("cancellation", adapter.conformance.missing_capabilities)
        self.assertEqual(events[-1]["event_type"], "run.needs_human")

    def test_selection_is_explicit_and_never_falls_back(self):
        self.assertIsInstance(select_adapter("codex", native_version="0.152.1"), CodexAdapter)
        with self.assertRaisesRegex(AdapterError, "unsupported_version"):
            select_adapter("codex", native_version="0.152.0")
        with self.assertRaisesRegex(AdapterError, "provider_ineligible"):
            select_adapter("grok", native_version="1.0.17", require_execution_eligible=True)
        with self.assertRaisesRegex(AdapterError, "unknown_provider"):
            select_adapter("future", native_version="1.0.0")

    def test_unknown_native_events_fail_closed(self):
        with self.assertRaisesRegex(AdapterError, "unknown_native_event"):
            CodexAdapter().translate(
                b'{"type":"future.unsafe","payload":"x"}\n',
                task_id="task-001",
                run_id="run-001",
                packet_digest="a" * 64,
            )

    def test_current_adapter_cannot_be_promoted_by_caller_profile(self):
        selected = self.selection()
        registry = AdapterRegistry((TrustedExecutionProfile(selected, CodexAdapter.conformance, ("writer",)),))
        with self.assertRaisesRegex(ExecutionContractError, "provider_ineligible"):
            registry.resolve(selected, role="writer")


if __name__ == "__main__":
    unittest.main()
