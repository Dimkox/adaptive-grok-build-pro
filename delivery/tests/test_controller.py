import threading
import unittest
from collections.abc import Sequence
from dataclasses import fields
from datetime import UTC, datetime, timedelta

from delivery.tests.synthetic_fixtures import (
    synthetic_digest,
    synthetic_observation,
    synthetic_plan,
    synthetic_promotion,
)

from adaptive_delivery import controller as controller_module
from adaptive_delivery.contracts import DeliveryEvidenceV1
from adaptive_delivery.controller import DryRunController, EvidenceChainError
from adaptive_delivery.fake_environment import AdapterBoundaryError, FakeEnvironmentAdapter
from adaptive_delivery.recovery import choose_recovery


def _replace_evidence(evidence: DeliveryEvidenceV1, **updates) -> DeliveryEvidenceV1:
    values = {
        field.name: getattr(evidence, field.name)
        for field in fields(evidence)
        if field.name != "evidence_digest"
    }
    values.update(updates)
    values["evidence_digest"] = synthetic_digest(values)
    return DeliveryEvidenceV1(**values)


def _synthetic_open_chain(promotion, count: int) -> tuple[DeliveryEvidenceV1, ...]:
    records: list[DeliveryEvidenceV1] = []
    started = datetime(2026, 9, 2, 9, 21, tzinfo=UTC)
    environment = "preview"
    exposure = 10000
    for sequence in range(1, count + 1):
        recovery_digest = None
        if environment == "preview":
            environment = "staging"
            effect = "entered_stage"
            reasons = ("thresholds_passed",)
        elif environment == "staging":
            environment = "bounded_canary"
            exposure = 100
            effect = "entered_stage"
            reasons = ("thresholds_passed",)
        elif exposure == 100:
            exposure = 500
            effect = "changed_exposure"
            reasons = ("thresholds_passed",)
        else:
            exposure = 100
            effect = "changed_exposure"
            reasons = ("health_below_minimum", "recovery_decrease")
            recovery_digest = f"{sequence + 512:064x}"
        values = {
            "schema_version": 1,
            "evidence_id": f"synthetic/evidence-{sequence}",
            "sequence": sequence,
            "promotion_digest": promotion.promotion_digest,
            "previous_evidence_digest": (
                records[-1].evidence_digest if records else None
            ),
            "artifact_digest": promotion.artifact.artifact_digest,
            "environment": environment,
            "exposure_basis_points": exposure,
            "observation_set_digest": f"{sequence:064x}",
            "delivery_decision_digest": f"{sequence + 256:064x}",
            "recovery_decision_digest": recovery_digest,
            "dry_run_effect": effect,
            "recorded_at": (started + timedelta(seconds=sequence - 1)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "reason_codes": reasons,
        }
        values["evidence_digest"] = synthetic_digest(values)
        records.append(DeliveryEvidenceV1(**values))
    return tuple(records)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.promotion = synthetic_promotion()
        self.adapter = FakeEnvironmentAdapter()
        self.controller = DryRunController(self.promotion, self.adapter)

    def step(self, environment, exposure, *, minute, **updates):
        captured = f"2026-09-02T09:{minute:02d}:00Z"
        window_start = f"2026-09-02T09:{minute - 2:02d}:00Z"
        evaluated = f"2026-09-02T09:{minute + 1:02d}:00Z"
        observation = synthetic_observation(
            self.promotion,
            observation_id=f"synthetic/observation-{environment}-{exposure}-{minute}",
            environment=environment,
            exposure_basis_points=exposure,
            captured_at=captured,
            window_started_at=window_start,
            window_ended_at=captured,
            source_snapshot_digest=f"{minute:064x}",
            **updates,
        )
        return self.controller.step(
            (observation,),
            evaluation_time=evaluated,
            recorded_at=evaluated,
        ), observation

    def test_complete_path_is_contiguous_and_stops_after_last_canary(self):
        expected = (
            ("preview", 10000, "staging", 10000, "entered_stage"),
            ("staging", 10000, "bounded_canary", 100, "entered_stage"),
            (
                "bounded_canary",
                100,
                "bounded_canary",
                500,
                "changed_exposure",
            ),
            (
                "bounded_canary",
                500,
                "bounded_canary",
                1000,
                "changed_exposure",
            ),
            (
                "bounded_canary",
                1000,
                "bounded_canary",
                1000,
                "needs_human",
            ),
        )
        minutes = (20, 23, 26, 29, 32)
        previous_digest = None
        for sequence, (case, minute) in enumerate(zip(expected, minutes, strict=True), 1):
            source_environment, source_exposure, result_environment, result_exposure, effect = case
            evidence, _ = self.step(
                source_environment,
                source_exposure,
                minute=minute,
            )
            self.assertEqual(evidence.sequence, sequence)
            self.assertEqual(evidence.previous_evidence_digest, previous_digest)
            self.assertEqual(evidence.environment, result_environment)
            self.assertEqual(evidence.exposure_basis_points, result_exposure)
            self.assertEqual(evidence.dry_run_effect, effect)
            previous_digest = evidence.evidence_digest

        self.assertEqual(len(self.controller.evidence), 5)
        self.assertEqual(len(self.adapter.effects), 4)
        self.assertEqual(self.controller.evidence[-1].dry_run_effect, "needs_human")
        with self.assertRaisesRegex(EvidenceChainError, "terminal"):
            self.step("bounded_canary", 1000, minute=35)

    def test_denial_applies_only_the_selected_narrowing_recovery(self):
        evidence, _ = self.step(
            "preview",
            10000,
            minute=20,
            health_basis_points=9800,
        )
        self.assertEqual(evidence.environment, "preview")
        self.assertEqual(evidence.exposure_basis_points, 10000)
        self.assertEqual(evidence.dry_run_effect, "halted")
        self.assertIsNotNone(evidence.recovery_decision_digest)
        self.assertEqual(tuple(effect.effect for effect in self.adapter.effects), ("halted",))
        with self.assertRaisesRegex(EvidenceChainError, "terminal"):
            self.step("preview", 10000, minute=23)

    def test_restore_effect_uses_only_the_exact_previous_artifact(self):
        plan = synthetic_plan(allowed_recovery_actions=("restore_previous",))
        promotion = synthetic_promotion(plan=plan)
        adapter = FakeEnvironmentAdapter()
        controller = DryRunController(promotion, adapter)
        observation = synthetic_observation(promotion, health_basis_points=9800)
        evidence = controller.step(
            (observation,),
            evaluation_time="2026-09-02T09:21:00Z",
            recorded_at="2026-09-02T09:21:00Z",
        )
        self.assertEqual(evidence.dry_run_effect, "restored")
        self.assertEqual(
            evidence.artifact_digest,
            promotion.previous_signed_artifact.artifact_digest,
        )
        self.assertEqual(adapter.effects[0].artifact_digest, evidence.artifact_digest)

    def test_replayed_observation_set_is_rejected_before_another_step(self):
        _, observation = self.step("preview", 10000, minute=20)
        with self.assertRaisesRegex(EvidenceChainError, "replay"):
            self.controller.step(
                (observation,),
                evaluation_time="2026-09-02T09:24:00Z",
                recorded_at="2026-09-02T09:24:00Z",
            )
        self.assertEqual(len(self.controller.evidence), 1)

    def test_evaluation_time_cannot_move_behind_prior_recorded_time(self):
        self.step("preview", 10000, minute=20)
        observation = synthetic_observation(
            self.promotion,
            observation_id="synthetic/backward-evaluation",
            environment="staging",
            exposure_basis_points=10000,
            captured_at="2026-09-02T09:19:00Z",
            window_started_at="2026-09-02T09:17:00Z",
            window_ended_at="2026-09-02T09:19:00Z",
            source_snapshot_digest="0" * 64,
        )
        with self.assertRaisesRegex(EvidenceChainError, "evaluation_time"):
            self.controller.step(
                (observation,),
                evaluation_time="2026-09-02T09:20:30Z",
                recorded_at="2026-09-02T09:22:00Z",
            )
        self.assertEqual(len(self.controller.evidence), 1)
        self.assertEqual(len(self.adapter.effects), 1)

    def test_denial_without_valid_recovery_is_appended_without_adapter_effect(self):
        decrease_only = synthetic_plan(
            allowed_recovery_actions=("decrease_exposure",)
        )
        first_step_promotion = synthetic_promotion(plan=decrease_only)
        first_step_adapter = FakeEnvironmentAdapter()
        first_step_controller = DryRunController(
            first_step_promotion, first_step_adapter
        )
        failed = synthetic_observation(
            first_step_promotion,
            health_basis_points=9800,
        )
        first_evidence = first_step_controller.step(
            (failed,),
            evaluation_time="2026-09-02T09:21:00Z",
            recorded_at="2026-09-02T09:21:00Z",
        )
        self.assertEqual(first_evidence.dry_run_effect, "none")
        self.assertIsNone(first_evidence.recovery_decision_digest)
        self.assertEqual(first_step_adapter.effects, ())
        healthy_retry = synthetic_observation(
            first_step_promotion,
            observation_id="synthetic/healthy-retry-after-deny",
            captured_at="2026-09-02T09:23:00Z",
            window_started_at="2026-09-02T09:21:00Z",
            window_ended_at="2026-09-02T09:23:00Z",
            source_snapshot_digest="0" * 64,
        )
        with self.assertRaisesRegex(EvidenceChainError, "terminal"):
            first_step_controller.step(
                (healthy_retry,),
                evaluation_time="2026-09-02T09:24:00Z",
                recorded_at="2026-09-02T09:24:00Z",
            )
        self.assertEqual(first_step_adapter.effects, ())
        self.assertEqual(len(first_step_controller.evidence), 1)

    def test_internal_chain_rejects_gap_bad_link_binding_and_stage_skip(self):
        first, _ = self.step("preview", 10000, minute=20)
        bad_gap = _replace_evidence(
            first,
            sequence=2,
            previous_evidence_digest="0" * 64,
        )
        bad_link = _replace_evidence(
            first,
            evidence_id="synthetic/evidence-bad-link",
            sequence=2,
            previous_evidence_digest="0" * 64,
        )
        bad_binding = _replace_evidence(
            first,
            promotion_digest="0" * 64,
        )
        stage_skip = _replace_evidence(
            first,
            environment="bounded_canary",
            exposure_basis_points=100,
        )
        cases = ((bad_gap,), (first, bad_link), (bad_binding,), (stage_skip,))
        for chain in cases:
            with self.subTest(chain=tuple(item.evidence_id for item in chain)), self.assertRaises(
                EvidenceChainError
            ):
                controller_module._validate_chain(self.promotion, chain)

    def test_internal_chain_rejects_reordered_time_and_duplicate_identity(self):
        chain = _synthetic_open_chain(self.promotion, 2)
        earlier = _replace_evidence(
            chain[1],
            recorded_at="2026-09-02T09:20:59Z",
        )
        duplicate = _replace_evidence(
            chain[1],
            evidence_id=chain[0].evidence_id,
            observation_set_digest=chain[0].observation_set_digest,
        )
        for candidate in ((chain[0], earlier), (chain[0], duplicate)):
            with self.subTest(candidate=candidate[-1].evidence_id), self.assertRaises(
                EvidenceChainError
            ):
                controller_module._validate_chain(self.promotion, candidate)

    def test_internal_chain_revalidates_record_digest_and_effect_reason_shape(self):
        first, _ = self.step("preview", 10000, minute=20)
        inconsistent_reason = _replace_evidence(
            first,
            reason_codes=("observation_incomplete",),
        )
        tampered_after_construction = _replace_evidence(
            first,
            evidence_id="synthetic/tampered-evidence",
        )
        object.__setattr__(
            tampered_after_construction,
            "reason_codes",
            ("observation_incomplete",),
        )
        for candidate in (inconsistent_reason, tampered_after_construction):
            with self.subTest(candidate=candidate.evidence_id), self.assertRaises(
                EvidenceChainError
            ):
                controller_module._validate_chain(self.promotion, (candidate,))

    def test_controller_rejects_fake_adapter_subclasses_before_any_effect(self):
        class CapabilityInjectingAdapter(FakeEnvironmentAdapter):
            supported_effects = frozenset(
                {*FakeEnvironmentAdapter.supported_effects, "production"}
            )

            def __init__(self):
                super().__init__()
                self.apply_calls = 0

            def apply(self, **kwargs):
                self.apply_calls += 1
                return super().apply(**kwargs)

        adapter = CapabilityInjectingAdapter()
        with self.assertRaisesRegex(EvidenceChainError, "fake adapter"):
            DryRunController(self.promotion, adapter)
        self.assertEqual(adapter.apply_calls, 0)

    def test_fake_adapter_instance_cannot_be_monkeypatched(self):
        apply_target = FakeEnvironmentAdapter()
        with self.assertRaises(AttributeError):
            apply_target.apply = object()

        effects_target = FakeEnvironmentAdapter()
        with self.assertRaises(AttributeError):
            effects_target.supported_effects = frozenset({"production"})

    def test_controller_rejects_post_init_adapter_swap(self):
        with self.assertRaises(AttributeError):
            self.controller._adapter = FakeEnvironmentAdapter()

    def test_controller_fails_closed_if_reviewed_adapter_method_is_globally_replaced(self):
        original_apply = FakeEnvironmentAdapter.apply
        calls = []

        def replaced_apply(adapter, **kwargs):
            calls.append((adapter, kwargs))
            return original_apply(adapter, **kwargs)

        FakeEnvironmentAdapter.apply = replaced_apply
        try:
            with self.assertRaisesRegex(EvidenceChainError, "adapter.*surface"):
                self.step("preview", 10000, minute=20)
        finally:
            FakeEnvironmentAdapter.apply = original_apply

        self.assertEqual(calls, [])
        self.assertEqual(self.controller.evidence, ())
        self.assertEqual(self.adapter.effects, ())

    def test_controller_fails_closed_if_adapter_immutability_surface_changes(self):
        original_setattr = FakeEnvironmentAdapter.__setattr__
        FakeEnvironmentAdapter.__setattr__ = object.__setattr__
        try:
            with self.assertRaisesRegex(EvidenceChainError, "adapter.*surface"):
                self.step("preview", 10000, minute=20)
        finally:
            FakeEnvironmentAdapter.__setattr__ = original_setattr

        self.assertEqual(self.controller.evidence, ())
        self.assertEqual(self.adapter.effects, ())

    def test_fake_adapter_private_effect_state_cannot_be_replaced_or_cleared(self):
        self.adapter.apply(
            effect="halted",
            promotion_digest=self.promotion.promotion_digest,
            artifact_digest=self.promotion.artifact.artifact_digest,
            environment="preview",
            exposure_basis_points=10000,
        )
        with self.assertRaises(AttributeError):
            self.adapter._effects = []
        with self.assertRaises(AttributeError):
            self.adapter._effects.clear()
        with self.assertRaises(AttributeError):
            self.adapter._FakeEnvironmentAdapter__effects = ()
        self.assertEqual(len(self.adapter.effects), 1)

    def test_controller_private_evidence_state_cannot_be_cleared(self):
        self.step("preview", 10000, minute=20)
        with self.assertRaises(AttributeError):
            self.controller._evidence.clear()
        with self.assertRaises(AttributeError):
            self.controller._DryRunController__evidence = ()
        self.assertEqual(len(self.controller.evidence), 1)

    def test_concurrent_identical_step_serializes_apply_and_append(self):
        observation = synthetic_observation(self.promotion)
        original_validate = controller_module._validate_chain
        candidate_barrier = threading.Barrier(2)

        def synchronized_validate(promotion, evidence_chain):
            result = original_validate(promotion, evidence_chain)
            if evidence_chain:
                try:
                    candidate_barrier.wait(timeout=0.2)
                except threading.BrokenBarrierError:
                    pass
            return result

        controller_module._validate_chain = synchronized_validate
        results = []
        errors = []

        def run_step():
            try:
                results.append(
                    self.controller.step(
                        (observation,),
                        evaluation_time="2026-09-02T09:21:00Z",
                        recorded_at="2026-09-02T09:21:00Z",
                    )
                )
            except Exception as exc:  # noqa: BLE001 - thread result is asserted below
                errors.append(exc)

        try:
            threads = (threading.Thread(target=run_step), threading.Thread(target=run_step))
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=2)
            self.assertTrue(all(not thread.is_alive() for thread in threads))
        finally:
            controller_module._validate_chain = original_validate

        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], EvidenceChainError)
        self.assertIn("replay", str(errors[0]))
        self.assertEqual(len(self.controller.evidence), 1)
        self.assertEqual(len(self.adapter.effects), 1)

    def test_nonempty_prior_evidence_requires_a_trusted_task5_witness(self):
        first, _ = self.step("preview", 10000, minute=20)
        with self.assertRaisesRegex(EvidenceChainError, "trusted.*witness"):
            DryRunController(
                self.promotion,
                FakeEnvironmentAdapter(),
                prior_evidence=(first,),
            )

    def test_prior_evidence_generator_is_rejected_without_materialization(self):
        first, _ = self.step("preview", 10000, minute=20)
        consumed = []

        def records():
            consumed.append(True)
            yield first

        with self.assertRaisesRegex(EvidenceChainError, "sequence"):
            DryRunController(
                self.promotion,
                FakeEnvironmentAdapter(),
                prior_evidence=records(),
            )
        self.assertEqual(consumed, [])

    def test_recovery_evidence_requires_denial_and_forbids_thresholds_passed(self):
        halted = self.controller.step(
            (synthetic_observation(self.promotion, health_basis_points=9800),),
            evaluation_time="2026-09-02T09:21:00Z",
            recorded_at="2026-09-02T09:21:00Z",
        )
        cases = (
            ("health_below_minimum", "recovery_halt", "thresholds_passed"),
            ("recovery_halt",),
        )
        for reasons in cases:
            forged = _replace_evidence(halted, reason_codes=reasons)
            with self.subTest(reasons=reasons), self.assertRaisesRegex(
                EvidenceChainError, "reason_codes"
            ):
                controller_module._validate_chain(self.promotion, (forged,))

    def test_recording_after_promotion_expiry_creates_no_effect_or_evidence(self):
        observation = synthetic_observation(
            self.promotion,
            captured_at="2026-09-02T10:58:00Z",
            window_started_at="2026-09-02T10:56:00Z",
            window_ended_at="2026-09-02T10:58:00Z",
        )
        with self.assertRaisesRegex(EvidenceChainError, "recorded_at.*expired"):
            self.controller.step(
                (observation,),
                evaluation_time="2026-09-02T10:59:00Z",
                recorded_at="2026-09-02T11:00:00Z",
            )
        self.assertEqual(self.controller.evidence, ())
        self.assertEqual(self.adapter.effects, ())

    def test_recording_after_current_artifact_authority_expiry_is_rejected(self):
        artifact = self.promotion.artifact
        expiring_artifact = type(artifact)(
            **{
                field.name: (
                    "2026-09-02T09:22:00Z"
                    if field.name == "authority_expires_at"
                    else getattr(artifact, field.name)
                )
                for field in fields(artifact)
            }
        )
        promotion = synthetic_promotion(artifact=expiring_artifact)
        adapter = FakeEnvironmentAdapter()
        controller = DryRunController(promotion, adapter)
        with self.assertRaisesRegex(EvidenceChainError, "current artifact.*expired"):
            controller.step(
                (synthetic_observation(promotion),),
                evaluation_time="2026-09-02T09:21:00Z",
                recorded_at="2026-09-02T09:22:00Z",
            )
        self.assertEqual(controller.evidence, ())
        self.assertEqual(adapter.effects, ())

    def test_restore_rechecks_previous_artifact_authority_at_recorded_time(self):
        previous = self.promotion.previous_signed_artifact
        expiring_previous = type(previous)(
            **{
                field.name: (
                    "2026-09-02T09:22:00Z"
                    if field.name == "authority_expires_at"
                    else getattr(previous, field.name)
                )
                for field in fields(previous)
            }
        )
        promotion = synthetic_promotion(
            previous_artifact=expiring_previous,
            plan=synthetic_plan(allowed_recovery_actions=("restore_previous",)),
        )
        recovery = choose_recovery(
            promotion,
            controller_module.evaluate_delivery(
                promotion,
                (synthetic_observation(promotion, health_basis_points=9800),),
                "2026-09-02T09:21:00Z",
                environment="preview",
                exposure_basis_points=10000,
            ),
            "2026-09-02T09:21:00Z",
        )
        original_choose = controller_module.choose_recovery
        controller_module.choose_recovery = lambda *_args, **_kwargs: recovery
        adapter = FakeEnvironmentAdapter()
        controller = DryRunController(promotion, adapter)
        try:
            with self.assertRaisesRegex(EvidenceChainError, "previous artifact.*expired"):
                controller.step(
                    (synthetic_observation(promotion, health_basis_points=9800),),
                    evaluation_time="2026-09-02T09:21:00Z",
                    recorded_at="2026-09-02T09:22:00Z",
                )
        finally:
            controller_module.choose_recovery = original_choose
        self.assertEqual(controller.evidence, ())
        self.assertEqual(adapter.effects, ())

    def test_oversized_observation_sequence_is_rejected_before_materialization(self):
        class OversizedObservations(Sequence):
            def __init__(self):
                self.read = False

            def __len__(self):
                return 129

            def __getitem__(self, index):
                self.read = True
                raise AssertionError(f"materialized item {index}")

        observations = OversizedObservations()
        with self.assertRaisesRegex(EvidenceChainError, "128"):
            self.controller.step(
                observations,
                evaluation_time="2026-09-02T09:21:00Z",
                recorded_at="2026-09-02T09:21:00Z",
            )
        self.assertFalse(observations.read)

    def test_observation_sequence_reads_only_its_declared_bounded_length(self):
        observation = synthetic_observation(self.promotion)

        class LyingObservationSequence(Sequence):
            def __init__(self):
                self.read_indexes = []

            def __len__(self):
                return 1

            def __getitem__(self, index):
                self.read_indexes.append(index)
                if index >= 3:
                    raise AssertionError("unbounded sequence materialization")
                return observation

        observations = LyingObservationSequence()
        evidence = self.controller.step(
            observations,
            evaluation_time="2026-09-02T09:21:00Z",
            recorded_at="2026-09-02T09:21:00Z",
        )
        self.assertEqual(evidence.sequence, 1)
        self.assertEqual(observations.read_indexes, [0])

    def assert_mixed_recovery_reason_is_rejected(
        self,
        promotion,
        chain,
        extra_reason,
    ):
        mutated = _replace_evidence(
            chain[-1],
            reason_codes=tuple(sorted((*chain[-1].reason_codes, extra_reason))),
        )
        with self.assertRaisesRegex(EvidenceChainError, "reason_codes"):
            controller_module._validate_chain(
                promotion,
                (*chain[:-1], mutated),
            )

    def test_internal_halt_rejects_mixed_recovery_reasons(self):
        halted_controller = DryRunController(
            self.promotion,
            FakeEnvironmentAdapter(),
        )
        halted = halted_controller.step(
            (synthetic_observation(self.promotion, health_basis_points=9800),),
            evaluation_time="2026-09-02T09:21:00Z",
            recorded_at="2026-09-02T09:21:00Z",
        )
        self.assert_mixed_recovery_reason_is_rejected(
            self.promotion,
            (halted,),
            "recovery_restore_previous",
        )

    def test_internal_restore_rejects_mixed_recovery_reasons(self):
        restore_plan = synthetic_plan(allowed_recovery_actions=("restore_previous",))
        restore_promotion = synthetic_promotion(plan=restore_plan)
        restore_controller = DryRunController(
            restore_promotion,
            FakeEnvironmentAdapter(),
        )
        restored = restore_controller.step(
            (
                synthetic_observation(
                    restore_promotion,
                    health_basis_points=9800,
                ),
            ),
            evaluation_time="2026-09-02T09:21:00Z",
            recorded_at="2026-09-02T09:21:00Z",
        )
        self.assert_mixed_recovery_reason_is_rejected(
            restore_promotion,
            (restored,),
            "recovery_decrease",
        )

    def test_internal_decrease_rejects_mixed_recovery_reasons(self):
        decrease_chain = _synthetic_open_chain(self.promotion, 4)
        self.assert_mixed_recovery_reason_is_rejected(
            self.promotion,
            decrease_chain,
            "recovery_halt",
        )

    def test_internal_chain_and_fake_adapter_are_independently_capped_at_128(self):
        chain = _synthetic_open_chain(self.promotion, 128)
        controller_module._validate_chain(self.promotion, chain)
        with self.assertRaisesRegex(EvidenceChainError, "128"):
            controller_module._validate_chain(self.promotion, chain + (chain[-1],))

        adapter = FakeEnvironmentAdapter()
        for _ in range(128):
            adapter.apply(
                effect="halted",
                promotion_digest=self.promotion.promotion_digest,
                artifact_digest=self.promotion.artifact.artifact_digest,
                environment="preview",
                exposure_basis_points=10000,
            )
        with self.assertRaisesRegex(AdapterBoundaryError, "128"):
            adapter.apply(
                effect="halted",
                promotion_digest=self.promotion.promotion_digest,
                artifact_digest=self.promotion.artifact.artifact_digest,
                environment="preview",
                exposure_basis_points=10000,
            )

    def test_adapter_has_no_production_or_external_capability_surface(self):
        public_names = {
            name for name in dir(self.adapter) if not name.startswith("_")
        }
        forbidden_fragments = (
            "production",
            "network",
            "shell",
            "provider",
            "credential",
            "sign",
            "connector",
            "subprocess",
            "command",
        )
        self.assertFalse(
            any(
                fragment in name
                for name in public_names
                for fragment in forbidden_fragments
            )
        )
        self.assertNotIn("production", self.adapter.supported_effects)
        with self.assertRaises(AdapterBoundaryError):
            self.adapter.apply(
                effect="entered_stage",
                promotion_digest=self.promotion.promotion_digest,
                artifact_digest=self.promotion.artifact.artifact_digest,
                environment="production",
                exposure_basis_points=10000,
            )
        self.assertEqual(self.adapter.effects, ())

    def test_effect_and_evidence_views_are_immutable_append_only_tuples(self):
        self.step("preview", 10000, minute=20)
        evidence_view = self.controller.evidence
        effect_view = self.adapter.effects
        self.assertIsInstance(evidence_view, tuple)
        self.assertIsInstance(effect_view, tuple)
        with self.assertRaises(AttributeError):
            evidence_view.append(evidence_view[0])
        with self.assertRaises(AttributeError):
            effect_view.append(effect_view[0])
        self.assertEqual(len(self.controller.evidence), 1)
        self.assertEqual(len(self.adapter.effects), 1)


if __name__ == "__main__":
    unittest.main()
