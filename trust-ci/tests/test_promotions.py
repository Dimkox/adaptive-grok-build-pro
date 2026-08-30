from __future__ import annotations

import base64
import json
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from jsonschema import Draft202012Validator, FormatChecker, ValidationError, validators

from _support import digest, now, sha
from adaptive_trust_ci.models import (
    PromotionEnvelope,
    PromotionExpectedBinding,
    PromotionEvent,
    PromotionPayload,
    ProtectedBranchAttestationEnvelope,
    ProtectedBranchAttestationPayload,
    canonical_json,
)
from adaptive_trust_ci.signing import (
    PromotionError,
    ProtectedAttestationError,
    Signer,
    TrustStore,
    sign_promotion,
    sign_protected_branch_attestation,
    verify_protected_branch_attestation,
    verify_promotion,
)


PROMOTION_ID = "12345678-1234-4234-8234-123456789abc"
ATTESTATION_ID = "abcdefab-1234-4234-8234-abcdefabcdef"
NONCE = base64.urlsafe_b64encode(b"n" * 32).decode("ascii").rstrip("=")


def _validate_max_utf8_bytes(validator, maximum, instance, schema):
    del validator, schema
    if isinstance(instance, str) and len(instance.encode("utf-8")) > maximum:
        yield ValidationError(f"UTF-8 value exceeds {maximum} bytes")


ContractValidator = validators.extend(
    Draft202012Validator, {"x-maxUtf8Bytes": _validate_max_utf8_bytes}
)
CONTRACT_FORMAT_CHECKER = FormatChecker()


@CONTRACT_FORMAT_CHECKER.checks("date-time", raises=ValueError)
def _validate_rfc3339_datetime(value):
    if not isinstance(value, str):
        return True
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    return True


def promotion_payload(signer: Signer, **overrides) -> PromotionPayload:
    values = {
        "schema_version": 1,
        "promotion_id": PROMOTION_ID,
        "nonce": NONCE,
        "actor": "dmitry",
        "key_id": signer.key_id,
        "repository": "dimkox/adaptive-grok-build-pro",
        "merged_commit_sha": sha("a"),
        "artifact_sha256": digest("b"),
        "target_environment": "production",
        "policy_epoch": digest("c"),
        "source_attestation_id": ATTESTATION_ID,
        "reason": "Promote the reviewed immutable artifact",
        "issued_at": "2026-08-23T12:00:00Z",
        "expires_at": "2026-08-23T12:15:00Z",
    }
    values.update(overrides)
    return PromotionPayload(**values)


def promotion_expected(payload: PromotionPayload | None = None, **overrides):
    values = {
        "repository": "dimkox/adaptive-grok-build-pro",
        "merged_commit_sha": sha("a"),
        "artifact_sha256": digest("b"),
        "target_environment": "production",
        "policy_epoch": digest("c"),
        "source_attestation_id": ATTESTATION_ID,
    }
    if payload is not None:
        values = {name: getattr(payload, name) for name in values}
    values.update(overrides)
    return PromotionExpectedBinding(**values)


def promotion_key_record(signer: Signer, **overrides) -> dict:
    record = {
        "key_id": signer.key_id,
        "actor": "dmitry",
        "scopes": ["promotion:production"],
        "public_key_pem": signer.public_key_pem().decode("utf-8"),
    }
    record.update(overrides)
    return record


class PromotionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.signer = Signer.generate()
        self.payload = promotion_payload(self.signer)
        self.envelope = sign_promotion(self.payload, self.signer)
        self.trust_store = TrustStore.from_dict(
            {"schema_version": 2, "keys": [promotion_key_record(self.signer)]}
        )
        self.expected = promotion_expected(self.payload)
        self.current = now() + timedelta(seconds=1)

    def verify(self, envelope=None, expected=None, current=None, maximum_ttl_seconds=900):
        return verify_promotion(
            envelope or self.envelope,
            self.trust_store,
            expected or self.expected,
            current or self.current,
            maximum_ttl_seconds,
        )

    def test_valid_promotion_round_trips_and_verifies(self) -> None:
        serialized = self.envelope.to_dict()
        self.assertEqual(self.payload, PromotionEnvelope.from_dict(serialized).payload)
        self.assertEqual(self.payload, self.verify())
        self.assertEqual("Ed25519", serialized["algorithm"])
        self.assertNotIn("=", serialized["signature"])

    def test_promotion_types_are_immutable(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            self.payload.reason = "changed"
        with self.assertRaises(FrozenInstanceError):
            self.envelope.signature = "changed"

    def test_promotion_tamper_and_unknown_fields_fail(self) -> None:
        changed = self.envelope.to_dict()
        changed["payload"]["artifact_sha256"] = digest("f")
        with self.assertRaisesRegex(PromotionError, "^promotion authorization invalid$"):
            self.verify(PromotionEnvelope.from_dict(changed))

        changed = self.envelope.to_dict()
        changed["payload"]["extra"] = True
        with self.assertRaises(ValueError):
            PromotionEnvelope.from_dict(changed)

    def test_promotion_from_dict_requires_exact_fields_and_types(self) -> None:
        payload = self.payload.to_dict()
        payload.pop("reason")
        with self.assertRaises(ValueError):
            PromotionPayload.from_dict(payload)

        envelope = self.envelope.to_dict()
        envelope["extra"] = True
        with self.assertRaises(ValueError):
            PromotionEnvelope.from_dict(envelope)

        for value in (True, 1.0, "1", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                PromotionPayload.from_dict(
                    {**self.payload.to_dict(), "schema_version": value}
                )

    def test_every_signed_field_is_structurally_strict(self) -> None:
        invalid_values = {
            "schema_version": 2,
            "promotion_id": PROMOTION_ID.upper(),
            "nonce": base64.urlsafe_b64encode(b"n" * 31).decode("ascii").rstrip("="),
            "actor": " dmitry",
            "key_id": "",
            "repository": "Dimkox/adaptive-grok-build-pro",
            "merged_commit_sha": sha("A"),
            "artifact_sha256": digest("B"),
            "target_environment": "Production",
            "policy_epoch": digest("C"),
            "source_attestation_id": ATTESTATION_ID.upper(),
            "reason": " trailing ",
            "issued_at": "2026-08-23T12:00:00+00:00",
            "expires_at": "2026-08-23T12:15:00.000Z",
        }
        for field, value in invalid_values.items():
            with self.subTest(field=field), self.assertRaises(ValueError):
                PromotionPayload.from_dict({**self.payload.to_dict(), field: value})

    def test_identity_and_reason_utf8_limits_are_enforced(self) -> None:
        for field in ("actor", "key_id"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                promotion_payload(self.signer, **{field: "x" * 129})
        with self.assertRaises(ValueError):
            promotion_payload(self.signer, reason="é" * 257)

    def test_expiry_must_follow_issue(self) -> None:
        with self.assertRaises(ValueError):
            promotion_payload(self.signer, expires_at="2026-08-23T12:00:00Z")

    def test_signature_covers_every_payload_field(self) -> None:
        valid_changes = {
            "promotion_id": "22345678-1234-4234-8234-123456789abc",
            "nonce": base64.urlsafe_b64encode(b"o" * 32).decode("ascii").rstrip("="),
            "actor": "another-human",
            "key_id": "ffffffffffffffff",
            "repository": "other/repository",
            "merged_commit_sha": sha("d"),
            "artifact_sha256": digest("d"),
            "target_environment": "staging",
            "policy_epoch": digest("d"),
            "source_attestation_id": "bbcdefab-1234-4234-8234-abcdefabcdef",
            "reason": "Changed after signing",
            "issued_at": "2026-08-23T11:59:59Z",
            "expires_at": "2026-08-23T12:14:59Z",
        }
        for field, value in valid_changes.items():
            changed = self.envelope.to_dict()
            changed["payload"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                PromotionError, "^promotion authorization invalid$"
            ):
                self.verify(PromotionEnvelope.from_dict(changed))

    def test_all_server_owned_bindings_must_match(self) -> None:
        mismatches = {
            "repository": "other/repository",
            "merged_commit_sha": sha("d"),
            "artifact_sha256": digest("d"),
            "target_environment": "staging",
            "policy_epoch": digest("d"),
            "source_attestation_id": "bbcdefab-1234-4234-8234-abcdefabcdef",
        }
        for field, value in mismatches.items():
            with self.subTest(field=field), self.assertRaisesRegex(
                PromotionError, "^promotion authorization invalid$"
            ):
                self.verify(expected=promotion_expected(self.payload, **{field: value}))

    def test_wrong_algorithm_and_malformed_signature_fail_with_constant_error(self) -> None:
        for change in (
            {"algorithm": "ed25519"},
            {"signature": "not+a/base64url/signature"},
        ):
            with self.subTest(change=change), self.assertRaisesRegex(
                PromotionError, "^promotion authorization invalid$"
            ):
                self.verify({**self.envelope.to_dict(), **change})

    def test_time_policy_enforces_future_skew_expiry_and_maximum_ttl(self) -> None:
        self.assertEqual(self.payload, self.verify(current=now() - timedelta(seconds=60)))
        for current, maximum_ttl in (
            (now() - timedelta(seconds=61), 900),
            (datetime(2026, 8, 23, 12, 15, tzinfo=timezone.utc), 900),
            (self.current, 899),
            (self.current, 3601),
        ):
            with self.subTest(current=current, maximum_ttl=maximum_ttl), self.assertRaisesRegex(
                PromotionError, "^promotion authorization invalid$"
            ):
                self.verify(current=current, maximum_ttl_seconds=maximum_ttl)

    def test_wrong_actor_scope_and_untrusted_key_are_indistinguishable(self) -> None:
        wrong_actor_store = TrustStore.from_dict(
            {
                "schema_version": 2,
                "keys": [promotion_key_record(self.signer, actor="someone-else")],
            }
        )
        wrong_scope_store = TrustStore.from_dict(
            {
                "schema_version": 2,
                "keys": [promotion_key_record(self.signer, scopes=["promotion:staging"])],
            }
        )
        for store in (wrong_actor_store, wrong_scope_store, TrustStore(keys={})):
            with self.subTest(store=store), self.assertRaisesRegex(
                PromotionError, "^promotion authorization invalid$"
            ):
                verify_promotion(
                    self.envelope, store, self.expected, self.current, 900
                )

    def test_protected_branch_attestation_contract_is_strict(self) -> None:
        payload = ProtectedBranchAttestationPayload(
            schema_version=1,
            source_attestation_id=ATTESTATION_ID,
            merge_fact_id="fedcbafe-1234-4234-8234-fedcbafedcba",
            repository="dimkox/adaptive-grok-build-pro",
            protected_ref="refs/heads/main",
            merged_commit_sha=sha("a"),
            policy_epoch=digest("b"),
            runner_digest=digest("c"),
            holdout_digest=digest("d"),
            image_digest=digest("e"),
            artifact_sha256=digest("f"),
            result="passed",
            issued_at="2026-08-23T12:00:00Z",
            key_id="ci-signing-key",
        )
        envelope = ProtectedBranchAttestationEnvelope(
            payload=payload,
            algorithm="Ed25519",
            signature=base64.urlsafe_b64encode(b"s" * 64).decode("ascii").rstrip("="),
        )
        self.assertEqual(envelope, ProtectedBranchAttestationEnvelope.from_dict(envelope.to_dict()))
        changed = envelope.to_dict()
        changed["payload"]["unknown"] = True
        with self.assertRaises(ValueError):
            ProtectedBranchAttestationEnvelope.from_dict(changed)
        with self.assertRaises(ValueError):
            ProtectedBranchAttestationPayload.from_dict(
                {**payload.to_dict(), "result": "failed"}
            )

    def test_json_contract_schemas_are_strict_and_frozen(self) -> None:
        root = __import__("pathlib").Path(__file__).resolve().parents[2]
        schema_dir = root / "engineering" / "contracts" / "schemas"
        for name in (
            "promotion-envelope-v1.schema.json",
            "protected-branch-attestation-v1.schema.json",
            "promotion-event-v1.schema.json",
        ):
            with self.subTest(name=name):
                schema = json.loads((schema_dir / name).read_text(encoding="utf-8"))
                self.assertEqual("https://json-schema.org/draft/2020-12/schema", schema["$schema"])
                self.assertFalse(schema["additionalProperties"])

    def test_json_schemas_reject_runtime_invalid_values(self) -> None:
        root = __import__("pathlib").Path(__file__).resolve().parents[2]
        schema_dir = root / "engineering" / "contracts" / "schemas"
        promotion_schema = json.loads(
            (schema_dir / "promotion-envelope-v1.schema.json").read_text(encoding="utf-8")
        )
        promotion_validator = ContractValidator(
            promotion_schema, format_checker=CONTRACT_FORMAT_CHECKER
        )
        promotion_validator.validate(self.envelope.to_dict())

        invalid_promotions = []
        invalid_timestamp = self.envelope.to_dict()
        invalid_timestamp["payload"]["issued_at"] = "2026-99-99T99:99:99Z"
        invalid_promotions.append(invalid_timestamp)
        noncanonical_nonce = self.envelope.to_dict()
        noncanonical_nonce["payload"]["nonce"] = NONCE[:-1] + "5"
        invalid_promotions.append(noncanonical_nonce)
        overlong_actor = self.envelope.to_dict()
        overlong_actor["payload"]["actor"] = "é" * 128
        invalid_promotions.append(overlong_actor)
        noncanonical_signature = self.envelope.to_dict()
        noncanonical_signature["signature"] = self.envelope.signature[:-1] + "B"
        invalid_promotions.append(noncanonical_signature)
        for document in invalid_promotions:
            with self.subTest(document=document), self.assertRaises(ValidationError):
                promotion_validator.validate(document)

        attestation = ProtectedBranchAttestationPayload(
            schema_version=1,
            source_attestation_id=ATTESTATION_ID,
            merge_fact_id="fedcbafe-1234-4234-8234-fedcbafedcba",
            repository="dimkox/adaptive-grok-build-pro",
            protected_ref="refs/heads/main",
            merged_commit_sha=sha("a"),
            policy_epoch=digest("b"),
            runner_digest=digest("c"),
            holdout_digest=digest("d"),
            image_digest=digest("e"),
            artifact_sha256=digest("f"),
            result="passed",
            issued_at="2026-08-23T12:00:00Z",
            key_id=self.signer.key_id,
        )
        attestation_envelope = sign_protected_branch_attestation(attestation, self.signer)
        attestation_schema = json.loads(
            (schema_dir / "protected-branch-attestation-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        attestation_validator = ContractValidator(
            attestation_schema, format_checker=CONTRACT_FORMAT_CHECKER
        )
        attestation_validator.validate(attestation_envelope.to_dict())
        invalid_attestation = attestation_envelope.to_dict()
        invalid_attestation["payload"]["issued_at"] = "2026-02-30T12:00:00Z"
        with self.assertRaises(ValidationError):
            attestation_validator.validate(invalid_attestation)

    def test_protected_attestation_schema_version_requires_exact_integer(self) -> None:
        valid = {
            "schema_version": 1,
            "source_attestation_id": ATTESTATION_ID,
            "merge_fact_id": "fedcbafe-1234-4234-8234-fedcbafedcba",
            "repository": "dimkox/adaptive-grok-build-pro",
            "protected_ref": "refs/heads/main",
            "merged_commit_sha": sha("a"),
            "policy_epoch": digest("b"),
            "runner_digest": digest("c"),
            "holdout_digest": digest("d"),
            "image_digest": digest("e"),
            "artifact_sha256": digest("f"),
            "result": "passed",
            "issued_at": "2026-08-23T12:00:00Z",
            "key_id": self.signer.key_id,
        }
        for value in (True, 1.0, "1", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ProtectedBranchAttestationPayload.from_dict(
                    {**valid, "schema_version": value}
                )

    def test_protected_attestation_signs_and_verifies_with_ci_key_only(self) -> None:
        signer = Signer.generate()
        payload = ProtectedBranchAttestationPayload(
            schema_version=1, source_attestation_id=ATTESTATION_ID,
            merge_fact_id="fedcbafe-1234-4234-8234-fedcbafedcba",
            repository="dimkox/adaptive-grok-build-pro", protected_ref="refs/heads/main",
            merged_commit_sha=sha("a"), policy_epoch=digest("b"), runner_digest=digest("c"),
            holdout_digest=digest("d"), image_digest=digest("e"), artifact_sha256=digest("f"),
            result="passed", issued_at="2026-08-23T12:00:00Z", key_id=signer.key_id,
        )
        envelope = sign_protected_branch_attestation(payload, signer)
        self.assertEqual(payload.canonical_bytes(), canonical_json(payload.to_dict()))
        self.assertEqual(payload, verify_protected_branch_attestation(envelope, signer.public_key_pem()))
        with self.assertRaisesRegex(ProtectedAttestationError, "^protected branch attestation invalid$"):
            verify_protected_branch_attestation({**envelope.to_dict(), "signature": envelope.signature + "="}, signer.public_key_pem())

    def test_human_promotion_signer_is_not_reachable_from_services(self) -> None:
        root = __import__("pathlib").Path(__file__).resolve().parents[1] / "src" / "adaptive_trust_ci"
        for name in ("api.py", "worker.py", "settings.py"):
            source = (root / name).read_text(encoding="utf-8")
            self.assertNotIn("sign_promotion", source)

    def test_promotion_event_is_strict_and_bounded(self) -> None:
        event = PromotionEvent(1, PROMOTION_ID, "promotion.accepted", "2026-08-23T12:00:00Z", PROMOTION_ID, "corr-1", None, "dmitry", self.signer.key_id, self.payload.repository, self.payload.merged_commit_sha, self.payload.artifact_sha256, "production", self.payload.policy_epoch, "accepted", "accepted", {"source": "api"})
        self.assertEqual(event, PromotionEvent.from_json(json.dumps(event.to_dict())))
        with self.assertRaises(ValueError):
            PromotionEvent.from_json('{"schema_version":1,"schema_version":1}')
        with self.assertRaises(ValueError):
            PromotionEvent.from_dict({**event.to_dict(), "schema_version": True})
        with self.assertRaises(ValueError):
            PromotionEvent.from_dict({**event.to_dict(), "details": {"bad-key": "x"}})
        for field in ("event_id", "promotion_id", "operation_id"):
            for value in ("12345678-1234-0234-8234-123456789abc", "12345678-1234-4234-c234-123456789abc", "12345678-1234-4234-8234-123456789ABC"):
                changed = {**event.to_dict(), field: value}
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    PromotionEvent.from_dict(changed)
        for value in ([], {}, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                PromotionEvent.from_dict({**event.to_dict(), "details": {"value": value}})
        self.assertEqual("x" * 512, PromotionEvent.from_dict({**event.to_dict(), "details": {"value": "x" * 512}}).details["value"])
        with self.assertRaises(ValueError):
            PromotionEvent.from_dict({**event.to_dict(), "details": {"value": "x" * 513}})
        for raw in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                PromotionEvent.from_json(
                    json.dumps({**event.to_dict(), "details": {"value": 0}}).replace(
                        '"value": 0', f'"value": {raw}'
                    )
                )
        with self.assertRaises(ValueError):
            PromotionEvent.from_dict({**event.to_dict(), "details": {f"key_{i}": "x" for i in range(17)}})
        for value in ("x" * 513, "é" * 257, "line\nbreak", 2**63, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                PromotionEvent.from_dict(
                    {**event.to_dict(), "details": {"value": value}}
                )

        root = __import__("pathlib").Path(__file__).resolve().parents[2]
        schema = json.loads(
            (
                root
                / "engineering"
                / "contracts"
                / "schemas"
                / "promotion-event-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        validator = ContractValidator(schema, format_checker=CONTRACT_FORMAT_CHECKER)
        validator.validate(event.to_dict())
        for value in ("x" * 513, "é" * 257, "line\nbreak", 2**63, 1.5):
            with self.subTest(schema_value=value), self.assertRaises(ValidationError):
                validator.validate({**event.to_dict(), "details": {"value": value}})


if __name__ == "__main__":
    unittest.main()
