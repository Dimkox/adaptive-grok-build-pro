from dataclasses import replace
import base64
import hashlib
import pickle
import subprocess
import sys
import textwrap
import unittest

from adaptive_factory.contracts import ContractError, canonical_digest
from adaptive_factory.fpf_snapshot import (
    FPF_LICENSE_ID,
    FPF_LICENSE_URL,
    FPF_SOURCE_AUTHOR,
    FPF_SOURCE_REPOSITORY,
    FPF_SOURCE_REVISION,
    FPF_SOURCE_TREE,
    Applicability,
    ContextBudget,
    FpfBlocked,
    FrozenFpfSnapshot,
    ProgressiveReader,
    SelectionRevision,
    _dependency_order,
    consume_selection,
    reconstruct_selection_artifact,
)
from adaptive_factory._fpf_snapshot_data import FPF_FRAGMENT_MANIFEST, FPF_FRAGMENT_BYTES


class FpfSnapshotTests(unittest.TestCase):
    def snapshot(self, selected=("A.2.4", "A.3.1")):
        return FrozenFpfSnapshot.load(
            tenant_id="tenant-1",
            repository_id="owner/project",
            selected_pattern_ids=selected,
            modifications="Exact excerpts selected without textual modification.",
        )

    @staticmethod
    def recompute_revision(values):
        forged = dict(values)
        forged["selection_digest"] = canonical_digest({
            **{key: value for key, value in forged.items() if key not in ("fragments", "selection_digest")},
            "fragments": [
                {key: value for key, value in item.items() if key != "text"}
                for item in forged["fragments"]
            ],
        })
        return forged

    def test_reviewed_manifest_binds_real_source_attribution_and_exact_bytes(self):
        snapshot = self.snapshot()
        self.assertEqual(snapshot.source_repository, FPF_SOURCE_REPOSITORY)
        self.assertEqual(snapshot.source_revision, FPF_SOURCE_REVISION)
        self.assertEqual(snapshot.source_tree, FPF_SOURCE_TREE)
        self.assertEqual(snapshot.source_author, FPF_SOURCE_AUTHOR)
        self.assertEqual(snapshot.license_id, FPF_LICENSE_ID)
        self.assertEqual(snapshot.license_url, FPF_LICENSE_URL)
        for pattern_id, fragment in snapshot.fragments.items():
            manifest = FPF_FRAGMENT_MANIFEST["fragments"][pattern_id]
            self.assertEqual(fragment["locator"], manifest["locator"])
            self.assertEqual(fragment["anchor"], manifest["anchor"])
            self.assertEqual(fragment["sha256"], manifest["sha256"])
            self.assertEqual(hashlib.sha256(fragment["text"]).hexdigest(), manifest["sha256"])
            self.assertEqual(fragment["text"], FPF_FRAGMENT_BYTES[pattern_id])
        self.assertEqual(snapshot.fragments["A.2.4"]["required"], ())
        self.assertEqual(
            set(snapshot.fragments["A.2.4"]["optional"]),
            {"A.10", "A.13", "A.15.1", "A.6.1", "B.3", "C.2.1", "C.28",
             "E.17", "F.10", "F.19:4", "F.6", "G.11", "G.6"},
        )
        self.assertEqual(snapshot.fragments["A.3.1"]["required"], ())
        self.assertEqual(set(snapshot.fragments["A.3.1"]["optional"]), {"A.22", "B.1.5", "F.19:4"})
        self.assertIn("conditional escalation", snapshot.fragments["A.2.4"]["dependency_rationale"])
        self.assertEqual(
            snapshot.fragments["A.3.1"]["dependency_evidence"],
            "Moving to a heavier level must solve one of those concrete problems.",
        )

    def test_snapshot_is_deep_frozen_and_direct_construction_is_closed(self):
        snapshot = self.snapshot()
        with self.assertRaises(TypeError):
            snapshot.fragments["A.2.4"]["text"] = b"mutated"
        with self.assertRaises(TypeError):
            snapshot.fragments["A.2.4"] = {}
        with self.assertRaises(TypeError):
            FPF_FRAGMENT_BYTES["A.2.4"] = b"mutated"
        with self.assertRaises(TypeError):
            FPF_FRAGMENT_MANIFEST["fragments"]["A.2.4"]["locator"] = "other.md"
        with self.assertRaises(TypeError):
            FrozenFpfSnapshot(
                tenant_id="tenant-1", repository_id="owner/project",
                modifications="forged", selected_pattern_ids=("A.2.4",),
                fragments={}, snapshot_digest="0" * 64,
            )

    def test_replace_cannot_forge_text_locator_dependencies_or_provenance(self):
        snapshot = self.snapshot()
        for field, value in (
            ("source_revision", "0" * 40), ("source_tree", "0" * 40),
            ("source_author", "someone else"), ("license_id", "UNKNOWN"),
            ("snapshot_digest", "0" * 64),
        ):
            with self.subTest(field=field), self.assertRaises(TypeError):
                replace(snapshot, **{field: value})
        forged = {key: dict(item) for key, item in snapshot.fragments.items()}
        forged["A.2.4"]["text"] = b"forged"
        object.__setattr__(snapshot, "fragments", forged)
        with self.assertRaisesRegex(ContractError, "snapshot_manifest_mismatch"):
            snapshot.revalidate()

    def test_rebinding_importable_module_globals_cannot_change_loaded_bytes(self):
        code = textwrap.dedent("""
            import adaptive_factory.fpf_snapshot as module
            module.FPF_SOURCE_REVISION = "0" * 40
            module.FPF_SOURCE_TREE = "0" * 40
            module.FPF_SOURCE_AUTHOR = "attacker"
            module.FPF_FRAGMENT_BYTES = {"A.2.4": b"EVIL"}
            module.FPF_FRAGMENT_MANIFEST = {"fragments": {}}
            module._SEALED_SOURCE = ({"fragments": {}}, {"A.2.4": b"EVIL"}, "0" * 64)
            module._snapshot_values = lambda *args: {"fragments": {"A.2.4": {"text": b"EVIL"}}}
            module._snapshot_init = lambda *args, **kwargs: None
            assert not hasattr(module, "_FACTORY_TOKEN")
            snapshot = module.FrozenFpfSnapshot.load(
                tenant_id="tenant-1", repository_id="owner/project",
                selected_pattern_ids=("A.2.4",), modifications="Exact excerpt.",
            )
            assert snapshot.source_revision == "86226dcb42d8ba340ebc86d7660fce165ac0722a"
            assert snapshot.fragments["A.2.4"]["text"] != b"EVIL"
            snapshot.revalidate()
        """)
        completed = subprocess.run(
            [sys.executable, "-c", code], check=False, capture_output=True, text=True
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_unknown_or_unselected_manifest_pattern_fails_closed(self):
        with self.assertRaisesRegex(FpfBlocked, "unreviewed_pattern"):
            self.snapshot(("made-up",))
        snapshot = self.snapshot(("A.2.4",))
        with self.assertRaisesRegex(FpfBlocked, "unresolved_pattern"):
            Applicability.select(
                task_size="standard", unresolved_question="Which method applies?",
                triggers=("method_applicability",),
                trigger_patterns={"method_applicability": "A.3.1"}, snapshot=snapshot,
                mandatory_rule_ids=(),
            )

    def test_applicability_selects_only_reviewed_loaded_patterns(self):
        native = Applicability.select(
            task_size="micro", unresolved_question=None,
            triggers=("ambiguous_evidence",),
            trigger_patterns={"ambiguous_evidence": "A.2.4"},
            snapshot=self.snapshot(), mandatory_rule_ids=("RULE-1",),
        )
        self.assertEqual(native.profile, "native")
        selected = Applicability.select(
            task_size="standard", unresolved_question="What evidence bounds this claim?",
            triggers=("ambiguous_evidence",),
            trigger_patterns={"ambiguous_evidence": "A.2.4"},
            snapshot=self.snapshot(), mandatory_rule_ids=("RULE-1",),
        )
        self.assertEqual(selected.profile, "native_fpf")
        self.assertEqual(selected.selected_patterns, ("A.2.4",))

    def test_applicability_rejects_subclass_and_ignores_method_monkeypatch(self):
        class ForgedSnapshot(FrozenFpfSnapshot):
            def revalidate(self):
                return None

        forged = ForgedSnapshot.load(
            tenant_id="tenant-1", repository_id="owner/project",
            selected_pattern_ids=("A.2.4",), modifications="Exact excerpt.",
        )
        with self.assertRaisesRegex(ContractError, "invalid_snapshot"):
            Applicability.select(
                task_size="standard", unresolved_question="question",
                triggers=(), trigger_patterns={}, snapshot=forged,
                mandatory_rule_ids=(),
            )
        snapshot = self.snapshot(("A.2.4",))
        original = FrozenFpfSnapshot.revalidate
        try:
            FrozenFpfSnapshot.revalidate = lambda _self: None
            object.__setattr__(snapshot, "source_revision", "0" * 40)
            with self.assertRaisesRegex(ContractError, "snapshot_manifest_mismatch"):
                Applicability.select(
                    task_size="standard", unresolved_question="question",
                    triggers=(), trigger_patterns={}, snapshot=snapshot,
                    mandatory_rule_ids=(),
                )
        finally:
            FrozenFpfSnapshot.revalidate = original

    def test_context_budget_derives_payload_bytes_and_conservative_tokens(self):
        payloads = (b"abc", b"defg")
        budget = ContextBudget(100, 10, 10, max_payload_bytes=7, max_reads=2)
        usage = budget.admit(payloads=payloads, mandatory=False)
        self.assertEqual(usage.payload_bytes, 7)
        self.assertEqual(usage.token_status, "estimated")
        self.assertEqual(usage.payload_tokens, 7)
        self.assertEqual(usage.total_tokens, 27)
        self.assertEqual(usage.tokenizer_id, "conservative-bytes-upper-bound")
        with self.assertRaisesRegex(FpfBlocked, "optional_context_budget"):
            budget.admit(payloads=(b"12345678",), mandatory=False)

    def test_caller_cannot_supply_a_self_attested_low_token_count(self):
        budget = ContextBudget(21, 10, 10, 1000, 1)
        with self.assertRaises(TypeError):
            budget.admit(payloads=(b"x" * 1000,), payload_tokens=0, mandatory=True)
        with self.assertRaisesRegex(FpfBlocked, "mandatory_context_budget"):
            budget.admit(payloads=(b"x" * 1000,), mandatory=True)

    def test_budget_exact_byte_token_and_read_boundaries_and_codes(self):
        exact = ContextBudget(29, 10, 10, max_payload_bytes=9, max_reads=1)
        self.assertEqual(
            exact.admit(payloads=(b"123456789",), mandatory=True).total_tokens,
            29,
        )
        with self.assertRaisesRegex(FpfBlocked, "mandatory_context_budget"):
            exact.admit(payloads=(b"x",), mandatory=True)
        with self.assertRaisesRegex(FpfBlocked, "mandatory_context_budget"):
            ContextBudget(29, 10, 10, 8, 1).admit(
                payloads=(b"123456789",), mandatory=True
            )
        with self.assertRaisesRegex(FpfBlocked, "optional_context_budget"):
            ContextBudget(28, 10, 10, 9, 1).admit(
                payloads=(b"123456789",), mandatory=False
            )

    def test_progressive_reader_exact_limits_tenant_and_failed_read_state(self):
        snapshot = self.snapshot()
        with self.assertRaisesRegex(FpfBlocked, "tenant_mismatch"):
            ProgressiveReader(snapshot, tenant_id="other")
        reader = ProgressiveReader(
            snapshot, tenant_id="tenant-1", max_depth=5, max_transitions=100,
            max_bytes=len(snapshot.fragments["A.2.4"]["text"]), max_reads=1,
        )
        with self.assertRaisesRegex(FpfBlocked, "uri_not_admitted"):
            reader.read("https://example.test/A.2.4", replay_label="test")
        self.assertEqual(reader.reads, 0)
        self.assertIsNone(reader.previous_digest)

        clean = self.snapshot()
        forged_reader = ProgressiveReader(clean, tenant_id="tenant-1")
        object.__setattr__(clean, "source_revision", "0" * 40)
        with self.assertRaisesRegex(ContractError, "snapshot_manifest_mismatch"):
            forged_reader.read("spec://ailev/FPF/A.2.4", replay_label="test")
        self.assertEqual(forged_reader.reads, 0)
        selection = reader.read("spec://ailev/FPF/A.2.4", replay_label="criterion-AC96")
        self.assertEqual(reader.reads, 1)
        self.assertEqual(selection.fragments[0]["text"], FPF_FRAGMENT_BYTES["A.2.4"])
        self.assertEqual(tuple(item["pattern_id"] for item in selection.fragments), ("A.2.4",))
        self.assertEqual(reader.previous_digest, selection.selection_digest)
        with self.assertRaisesRegex(FpfBlocked, "read_budget"):
            reader.read("spec://ailev/FPF/A.2.4", replay_label="criterion-AC96")

        too_small = ProgressiveReader(
            self.snapshot(("A.2.4",)), tenant_id="tenant-1",
            max_bytes=len(FPF_FRAGMENT_BYTES["A.2.4"]) - 1,
        )
        with self.assertRaisesRegex(FpfBlocked, "mandatory_context_budget"):
            too_small.read("spec://ailev/FPF/A.2.4", replay_label="criterion-AC96")
        self.assertEqual(too_small.reads, 0)
        self.assertIsNone(too_small.previous_digest)

    def test_reader_rejects_snapshot_subclass_and_ignores_class_method_monkeypatch(self):
        class ForgedSnapshot(FrozenFpfSnapshot):
            def revalidate(self):
                return None

        forged = ForgedSnapshot.load(
            tenant_id="tenant-1", repository_id="owner/project",
            selected_pattern_ids=("A.2.4",), modifications="Exact excerpt.",
        )
        object.__setattr__(forged, "source_revision", "0" * 40)
        with self.assertRaisesRegex(ContractError, "invalid_snapshot"):
            ProgressiveReader(forged, tenant_id="tenant-1")

        snapshot = self.snapshot(("A.2.4",))
        reader = ProgressiveReader(snapshot, tenant_id="tenant-1")
        original = FrozenFpfSnapshot.revalidate
        try:
            FrozenFpfSnapshot.revalidate = lambda _self: None
            object.__setattr__(snapshot, "source_revision", "0" * 40)
            with self.assertRaisesRegex(ContractError, "snapshot_manifest_mismatch"):
                reader.read("spec://ailev/FPF/A.2.4", replay_label="criterion-AC96")
        finally:
            FrozenFpfSnapshot.revalidate = original

    def test_selection_revision_requires_replay_api_and_revalidates_mutation(self):
        with self.assertRaises(TypeError):
            SelectionRevision(revision=1)
        selection = ProgressiveReader(
            self.snapshot(("A.2.4",)), tenant_id="tenant-1"
        ).read("spec://ailev/FPF/A.2.4", replay_label="criterion-AC96")
        consumed = consume_selection(selection)
        self.assertEqual(consumed["fragments"][0]["text"], FPF_FRAGMENT_BYTES["A.2.4"])
        object.__setattr__(selection, "selection_digest", "0" * 64)
        with self.assertRaisesRegex(ContractError, "selection_digest_mismatch"):
            consume_selection(selection)

        recomputed = ProgressiveReader(
            self.snapshot(("A.2.4",)), tenant_id="tenant-1"
        ).read("spec://ailev/FPF/A.2.4", replay_label="criterion-AC96")
        forged_fragment = {**dict(recomputed.fragments[0]), "text": b"FORGED"}
        object.__setattr__(recomputed, "fragments", (forged_fragment,))
        # Text is deliberately excluded from the public digest facts, so even an
        # unchanged/self-recomputed digest must not turn caller bytes into authority.
        with self.assertRaisesRegex(ContractError, "selection_fragment_mismatch"):
            consume_selection(recomputed)

        unissued = object.__new__(SelectionRevision)
        for field in SelectionRevision.__dataclass_fields__:
            object.__setattr__(unissued, field, getattr(recomputed, field))
        with self.assertRaisesRegex(ContractError, "selection_fragment_mismatch"):
            consume_selection(unissued)

    def test_selection_restart_reconstruction_and_sequence_replay_are_stateless(self):
        reader = ProgressiveReader(
            self.snapshot(("A.2.4",)), tenant_id="tenant-1", max_reads=2
        )
        first = reader.read("spec://ailev/FPF/A.2.4", replay_label="first")
        second = reader.read("spec://ailev/FPF/A.2.4", replay_label="second")
        replayed_first = reconstruct_selection_artifact(consume_selection(first))
        replayed_second = reconstruct_selection_artifact(consume_selection(second, first))
        self.assertEqual(consume_selection(replayed_first)["selection_digest"], first.selection_digest)
        self.assertEqual(
            consume_selection(replayed_second, replayed_first)["selection_digest"],
            second.selection_digest,
        )
        with self.assertRaisesRegex(ContractError, "selection_sequence_incomplete"):
            consume_selection(replayed_second)

        serialized = base64.b64encode(pickle.dumps(consume_selection(first))).decode("ascii")
        code = textwrap.dedent(f"""
            import base64, pickle
            from adaptive_factory.fpf_snapshot import reconstruct_selection_artifact, consume_selection
            values = pickle.loads(base64.b64decode({serialized!r}))
            replayed = reconstruct_selection_artifact(values)
            assert consume_selection(replayed)["selection_digest"] == values["selection_digest"]
        """)
        completed = subprocess.run(
            [sys.executable, "-c", code], check=False, capture_output=True, text=True
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        # No issuance registry grows with volume: every envelope validates solely
        # from its carried facts and the closure-sealed source.
        for index in range(256):
            fresh = ProgressiveReader(
                self.snapshot(("A.2.4",)), tenant_id="tenant-1"
            ).read("spec://ailev/FPF/A.2.4", replay_label=f"read-{index}")
            consume_selection(reconstruct_selection_artifact(consume_selection(fresh)))
        closure_values = [cell.cell_contents for cell in consume_selection.__closure__ or ()]
        self.assertFalse(any(isinstance(value, dict) for value in closure_values))

    def test_replay_rejects_recomputed_invalid_inputs_and_impossible_sequence(self):
        reader = ProgressiveReader(
            self.snapshot(("A.2.4",)), tenant_id="tenant-1", max_reads=2
        )
        first = reader.read("spec://ailev/FPF/A.2.4", replay_label="first")
        second = reader.read("spec://ailev/FPF/A.2.4", replay_label="second")
        first_values = consume_selection(first)
        second_values = consume_selection(second, first)
        for field, value, code in (
            ("replay_label", "", "invalid_"),
            ("replay_label", "forged reason", "invalid_"),
            ("max_reads", 1.5, "invalid_navigation_budget"),
            ("max_depth", True, "invalid_navigation_budget"),
            ("max_bytes", False, "invalid_navigation_budget"),
        ):
            forged = self.recompute_revision({**first_values, field: value})
            with self.subTest(field=field, value=value), self.assertRaisesRegex(
                ContractError, code
            ):
                consume_selection(reconstruct_selection_artifact(forged))

        relabeled = self.recompute_revision({
            **first_values, "replay_label": "alternate-input"
        })
        alternate = consume_selection(reconstruct_selection_artifact(relabeled))
        self.assertEqual(alternate["replay_label"], "alternate-input")
        self.assertNotEqual(alternate["selection_digest"], first.selection_digest)
        self.assertTrue({"occurred", "delivered", "read_at"}.isdisjoint(alternate))

        impossible = self.recompute_revision({**second_values, "max_bytes": 4096})
        with self.assertRaisesRegex(ContractError, "selection_sequence_mismatch"):
            consume_selection(reconstruct_selection_artifact(impossible), first)

    def test_dependency_walk_deduplicates_cycles_and_enforces_exact_limits(self):
        graph = {"a": {"required": ("b",)}, "b": {"required": ("a",)}}
        self.assertEqual(_dependency_order("a", graph, 1, 2), ("a", "b"))
        with self.assertRaisesRegex(FpfBlocked, "navigation_budget"):
            _dependency_order("a", graph, 0, 2)
        with self.assertRaisesRegex(FpfBlocked, "navigation_budget"):
            _dependency_order("a", graph, 1, 1)
        with self.assertRaisesRegex(FpfBlocked, "missing_required_fragment"):
            _dependency_order("a", {"a": {"required": ("missing",)}}, 1, 2)

    def test_snapshot_digest_changes_only_after_valid_rebuild(self):
        first = self.snapshot(("A.2.4",))
        second = self.snapshot(("A.2.4", "A.3.1"))
        self.assertNotEqual(first.snapshot_digest, second.snapshot_digest)
        object.__setattr__(second, "snapshot_digest", "0" * 64)
        with self.assertRaisesRegex(ContractError, "snapshot_manifest_mismatch"):
            second.revalidate()


if __name__ == "__main__":
    unittest.main()
