from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))


class StableSynthesisContractTest(unittest.TestCase):
    def test_closed_pins_and_deterministic_api_exist(self) -> None:
        config = json.loads((ROOT / "engineering/contracts/schemas/stable-synthesis-upstreams.v1.json").read_text())
        self.assertEqual([s["id"] for s in config["sources"]], ["bmad_method", "spec_kit", "superpowers"])
        from adaptive_grok.stable_synthesis import load_upstreams, synthesize
        self.assertEqual(load_upstreams(ROOT), load_upstreams(ROOT))
        self.assertEqual(synthesize({"intent":"x"}), synthesize({"intent":"x"}))

    def test_dag_cycles_transitions_snapshot_and_iteration_bound_fail_closed(self) -> None:
        from adaptive_grok.stable_synthesis import SynthesisError, synthesize, transition, validate_dag, verify_snapshot, snapshot
        with self.assertRaisesRegex(SynthesisError, "cycle"):
            validate_dag([{"id":"a","depends_on":["b"]},{"id":"b","depends_on":["a"]}])
        with self.assertRaisesRegex(SynthesisError, "invalid state"):
            transition("ready", "pending")
        with self.assertRaises(SynthesisError):
            synthesize({"intent":"x"}, iterations=9)
        snap = snapshot({"b":2,"a":1})
        self.assertEqual(snap, snapshot({"a":1,"b":2}))
        snap["content"]["a"] = 9
        with self.assertRaisesRegex(SynthesisError, "digest"):
            verify_snapshot(snap)

    def test_journal_is_cas_chained_resumable_and_corruption_is_rejected(self) -> None:
        from adaptive_grok.stable_synthesis import Journal, SynthesisError
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".grok-stack/runtime").mkdir(parents=True)
            journal = Journal(root)
            first = journal.append({"kind":"analyze","recorded_at":"2026-09-03T00:00:00Z"}, "0" * 64)
            second = journal.append({"kind":"ready","recorded_at":"2026-09-03T00:00:01Z"}, first["digest"])
            self.assertEqual(journal.read(), [first, second])
            with self.assertRaisesRegex(SynthesisError, "compare-and-swap"):
                journal.append({"kind":"bad"}, first["digest"])
            journal.path.write_text(journal.path.read_text().replace('"kind":"ready"', '"kind":"forged"'))
            with self.assertRaisesRegex(SynthesisError, "corrupt"):
                journal.read()

    def test_config_rejects_unknown_fields_and_noncanonical_sources(self) -> None:
        from adaptive_grok.stable_synthesis import SynthesisError, load_upstreams
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "engineering/contracts/schemas"
            target.mkdir(parents=True)
            data = json.loads((ROOT / "engineering/contracts/schemas/stable-synthesis-upstreams.v1.json").read_text())
            data["unexpected"] = True
            (target / "stable-synthesis-upstreams.v1.json").write_text(json.dumps(data))
            with self.assertRaisesRegex(SynthesisError, "closed"):
                load_upstreams(root)

    def test_traceability_has_stable_spec_kit_categories_and_never_downgrades(self) -> None:
        from adaptive_grok.stable_synthesis import IntentRequirement, PlannedTask, SynthesisError, analyze_traceability, transition
        requirements = [IntentRequirement("AC-1", "observe latest"), IntentRequirement("AC-2", "review fixes")]
        tasks = [
            PlannedTask("T-1", ("AC-1",), "ready"),
            PlannedTask("T-2", ("UNKNOWN",), "pending", ("test:x",)),
            PlannedTask("T-3", ("AC-1",), "analyzing", ("test:y",)),
        ]
        findings = analyze_traceability(requirements, tasks)
        self.assertEqual({f.category for f in findings}, {"missing", "partial", "contradicts", "unrequested"})
        self.assertEqual(findings, analyze_traceability(reversed(requirements), reversed(tasks)))
        with self.assertRaises(SynthesisError):
            transition("ready", "analyzing")


if __name__ == "__main__":
    unittest.main()
