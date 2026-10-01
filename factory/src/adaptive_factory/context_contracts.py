"""Native context admission. Inputs are selected data, never instructions or grants."""

import hashlib
from .contracts import ContractError, canonical_digest
from .v15_contracts import FrozenWire, closed, version, safe_text, path, digest, sha, identity, timestamp, sequence


class ContextManifestV1(FrozenWire):
    @classmethod
    def from_dict(cls, data, *, expected_tenant=None, expected_repository=None):
        closed(
            data,
            (
                "schema_version",
                "builder_version",
                "tenant_id",
                "repository_id",
                "source_snapshot",
                "change_id",
                "route_id",
                "change_spec_digest",
                "observed_at",
                "mandatory_sources",
                "selected_sources",
                "rule_bindings",
            ),
        )
        version(data)
        for key in ("builder_version", "tenant_id", "repository_id", "change_id", "route_id"):
            identity(data[key])
        if expected_tenant is not None and data["tenant_id"] != expected_tenant:
            raise ContractError("tenant_mismatch")
        if expected_repository is not None and data["repository_id"] != expected_repository:
            raise ContractError("repository_mismatch")
        snapshot = data["source_snapshot"]
        closed(snapshot, ("base_sha", "head_sha", "dirty_fingerprint"))
        sha(snapshot["base_sha"])
        sha(snapshot["head_sha"])
        if snapshot["dirty_fingerprint"] is not None:
            digest(snapshot["dirty_fingerprint"])
        digest(data["change_spec_digest"])
        timestamp(data["observed_at"])
        seen = set()
        admitted_sources = {}
        total = 0
        normalized = dict(data)
        for group in ("mandatory_sources", "selected_sources"):
            entries = sequence(data[group])
            if group == "mandatory_sources" and not entries:
                raise ContractError("mandatory_context_missing")
            for entry in entries:
                closed(
                    entry,
                    (
                        "path",
                        "kind",
                        "content",
                        "sha256",
                        "reason",
                        "applicable_scope",
                        "mode",
                    ),
                )
                path(entry["path"])
                digest(entry["sha256"])
                identity(entry["reason"])
                identity(entry["applicable_scope"])
                if entry["mode"] not in ("full", "verified_extract"):
                    raise ContractError("invalid_source_mode")
                if entry["kind"] not in ("instruction", "rule", "contract", "source", "navigation"):
                    raise ContractError("invalid_source_kind")
                safe_text(entry["content"], "content")
                if hashlib.sha256(entry["content"].encode()).hexdigest() != entry["sha256"]:
                    raise ContractError("source_digest_mismatch")
                if entry["path"] in seen:
                    raise ContractError("duplicate_source")
                seen.add(entry["path"])
                admitted_sources.setdefault(entry["sha256"], set()).add(
                    (
                        entry["path"],
                        entry["applicable_scope"],
                        entry["mode"],
                    )
                )
                total += len(entry["content"].encode())
            normalized[group] = sorted(entries, key=lambda e: e["path"])
        if len(seen) > 128 or total > 262144:
            raise ContractError("context_too_large")
        bindings = sequence(data["rule_bindings"])
        seen = set()
        for binding in bindings:
            closed(
                binding,
                (
                    "criterion_id",
                    "rule_id",
                    "revision",
                    "repository_id",
                    "source_digest",
                    "source_path",
                    "applicable_scope",
                    "mode",
                    "status",
                ),
            )
            for key in ("criterion_id", "rule_id", "revision", "repository_id", "applicable_scope"):
                identity(binding[key])
            digest(binding["source_digest"])
            path(binding["source_path"])
            if binding["repository_id"] != data["repository_id"]:
                raise ContractError("repository_mismatch")
            if binding["status"] != "active":
                raise ContractError("rule_not_active")
            if binding["mode"] not in ("full", "verified_extract"):
                raise ContractError("invalid_source_mode")
            if (
                binding["source_path"],
                binding["applicable_scope"],
                binding["mode"],
            ) not in admitted_sources.get(binding["source_digest"], set()):
                raise ContractError("source_binding_mismatch")
            key = (binding["criterion_id"], binding["rule_id"])
            if key in seen:
                raise ContractError("duplicate_rule_binding")
            seen.add(key)
        normalized["rule_bindings"] = sorted(bindings, key=lambda b: (b["criterion_id"], b["rule_id"]))
        return cls.freeze(normalized)

    @property
    def context_digest(self):
        semantic = self.to_dict()
        semantic.pop("observed_at")
        return canonical_digest(semantic)
