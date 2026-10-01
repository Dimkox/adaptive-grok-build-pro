from copy import deepcopy
import hashlib
import importlib
import importlib.util
import unittest
from unittest.mock import patch

from adaptive_factory.contracts import ContractError


def context_facts():
    def source(path, kind):
        content = "safe project fact"
        return dict(
            path=path,
            kind=kind,
            content=content,
            sha256=hashlib.sha256(content.encode()).hexdigest(),
            reason="affected_path",
            applicable_scope="repository",
            mode="full",
        )

    mandatory = source("AGENTS.md", "instruction")
    return dict(
        schema_version=1,
        builder_version="native-1",
        tenant_id="tenant-1",
        repository_id="owner/project",
        source_snapshot=dict(base_sha="1" * 40, head_sha="2" * 40, dirty_fingerprint="3" * 64),
        change_id="change-1",
        route_id="route-1",
        change_spec_digest="4" * 64,
        observed_at="2026-09-30T12:00:00Z",
        mandatory_sources=[mandatory],
        selected_sources=[source("src/b.py", "source"), source("src/a.py", "source")],
        rule_bindings=[
            dict(
                criterion_id="AC-001",
                rule_id="RULE-1",
                revision="1",
                repository_id="owner/project",
                source_digest=mandatory["sha256"],
                source_path=mandatory["path"],
                applicable_scope=mandatory["applicable_scope"],
                mode=mandatory["mode"],
                status="active",
            )
        ],
    )


class ContextContractTests(unittest.TestCase):
    def contract(self):
        self.assertIsNotNone(importlib.util.find_spec("adaptive_factory.context_contracts"), "context contract missing")
        return importlib.import_module("adaptive_factory.context_contracts").ContextManifestV1

    def test_semantic_identity_is_order_and_timestamp_independent(self):
        cls = self.contract()
        facts = context_facts()
        first = cls.from_dict(facts)
        facts["selected_sources"].reverse()
        facts["observed_at"] = "2026-09-30T13:00:00Z"
        self.assertEqual(first.context_digest, cls.from_dict(facts).context_digest)
        facts["source_snapshot"]["dirty_fingerprint"] = "6" * 64
        self.assertNotEqual(first.context_digest, cls.from_dict(facts).context_digest)
        self.assertEqual(first.to_dict()["selected_sources"][0]["path"], "src/a.py")

    def test_unsafe_unknown_cross_repository_and_oversized_context_fails_closed(self):
        cls = self.contract()
        changes = [dict(extra=True), dict(schema_version=True), dict(tenant_id="other")]
        for change in changes:
            facts = context_facts()
            facts.update(change)
            with self.assertRaises(ContractError):
                cls.from_dict(facts, expected_tenant="tenant-1", expected_repository="owner/project")
        for path in ("../x", "/tmp/x", "a//b", "a/./b", ".env", "keys/private.pem", "a\\b"):
            facts = context_facts()
            facts["selected_sources"][0]["path"] = path
            with self.subTest(path=path), self.assertRaises(ContractError):
                cls.from_dict(facts)
        for mutation in ("repository", "digest", "duplicate", "bytes", "entries", "secret", "rule"):
            facts = context_facts()
            if mutation == "repository":
                facts["rule_bindings"][0]["repository_id"] = "other/project"
            if mutation == "digest":
                facts["selected_sources"][0]["sha256"] = "0" * 64
            if mutation == "duplicate":
                facts["selected_sources"].append(deepcopy(facts["selected_sources"][0]))
            if mutation == "bytes":
                facts["selected_sources"][0]["content"] = "x" * 4097
            if mutation == "entries":
                facts["selected_sources"] *= 129
            if mutation == "secret":
                facts["selected_sources"][0]["content"] = "password=synthetic-secret"
            if mutation == "rule":
                facts["rule_bindings"][0]["status"] = "approved"
            with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                cls.from_dict(facts)

    def test_expected_repository_rejects_consistently_cross_repository_context(self):
        cls = self.contract()
        facts = context_facts()
        facts["repository_id"] = "other/project"
        facts["rule_bindings"][0]["repository_id"] = "other/project"
        with self.assertRaisesRegex(ContractError, "repository_mismatch"):
            cls.from_dict(facts, expected_repository="owner/project")

    def test_input_and_export_mutation_cannot_change_frozen_identity(self):
        cls = self.contract()
        facts = context_facts()
        manifest = cls.from_dict(facts)
        digest = manifest.context_digest
        facts["selected_sources"][0]["content"] = "changed"
        exported = manifest.to_dict()
        exported["selected_sources"][0]["content"] = "changed"
        self.assertEqual(manifest.context_digest, digest)

    def test_rule_binding_resolves_exact_admitted_digest_scope_mode_and_path(self):
        cls = self.contract()
        for field, value in (
            ("source_digest", "f" * 64),
            ("source_path", "src/other.py"),
            ("applicable_scope", "workspace"),
            ("mode", "verified_extract"),
        ):
            facts = context_facts()
            facts["rule_bindings"][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ContractError, "source_binding_mismatch"):
                cls.from_dict(facts)

    def test_source_content_always_passes_through_safe_text(self):
        module = importlib.import_module("adaptive_factory.context_contracts")
        facts = context_facts()
        with patch.object(module, "safe_text", wraps=module.safe_text) as guarded:
            module.ContextManifestV1.from_dict(facts)
        guarded.assert_any_call(facts["mandatory_sources"][0]["content"], "content")
