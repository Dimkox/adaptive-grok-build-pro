from __future__ import annotations

import hashlib
import json
import os
import stat
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .spec import SpecError, _schema_preflight, validate_schema

MAX_DOCUMENT_BYTES = 1_000_000
MAX_DEPTH = 64
MAX_PARSED_NODES = 100_000
MAX_MODEL_NODES = 128
MAX_MODEL_EDGES = 512
MAX_RULES = 256

SYSTEM_PATH = Path("architecture/system.yaml")
RULES_PATH = Path("architecture/rules.yaml")
SYSTEM_SCHEMA_PATH = Path("schemas/architecture-system.schema.json")
RULES_SCHEMA_PATH = Path("schemas/architecture-rules.schema.json")

SYSTEM_COLLECTIONS = (
    "trust_domains",
    "data_classifications",
    "secret_classes",
    "signals",
    "contracts",
    "nodes",
    "edges",
)
RULE_COLLECTIONS = (
    "forbidden_edges",
    "path_boundaries",
    "contract_policies",
    "migration_policies",
    "tenant_authorization_policies",
    "network_policies",
    "change_separation_policies",
    "code_budgets",
    "background_job_policies",
    "secret_flow_policies",
    "workspace_trust_policies",
    "risk_escalations",
)
RULE_PATH_FIELDS = {
    "source_prefixes",
    "forbidden_dependency_prefixes",
    "path_prefixes",
    "implementation_prefixes",
    "trust_ci_prefixes",
}


class ArchitectureError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ArchitectureFinding:
    code: str
    message: str
    path: str
    severity: str = "error"


@dataclass(frozen=True)
class ArchitectureSnapshot:
    system: dict[str, Any]
    rules: dict[str, Any]
    system_schema: dict[str, Any]
    rules_schema: dict[str, Any]
    system_path: str
    rules_path: str


def _unsafe_text(value: str) -> bool:
    return any(
        unicodedata.category(character) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        for character in value
    )


def _safe_relative_path(value: str, *, label: str) -> str:
    if not isinstance(value, str):
        raise ArchitectureError(f"{label}: path must be a string", code="path")
    pure = PurePosixPath(value)
    raw_parts = value.split("/")
    if (
        not value
        or _unsafe_text(value)
        or unicodedata.normalize("NFC", value) != value
        or "\\" in value
        or pure.is_absolute()
        or value.endswith("/")
        or "//" in value
        or any(part in {"", ".", ".."} for part in raw_parts)
    ):
        raise ArchitectureError(f"{label}: unsafe repository-relative path {value!r}", code="path")
    return pure.as_posix()


def _document_relative(root: Path, path: Path | str, *, label: str) -> str:
    root_real = root.resolve(strict=True)
    candidate = Path(path)
    if not candidate.is_absolute():
        raw = candidate.as_posix()
        _safe_relative_path(raw, label=label)
        candidate = root_real / candidate
    candidate_absolute = Path(os.path.abspath(candidate))
    try:
        relative = candidate_absolute.relative_to(root_real)
    except ValueError as exc:
        raise ArchitectureError(f"{label}: path escapes repository", code="path") from exc
    return _safe_relative_path(relative.as_posix(), label=label)


def _read_regular_bytes(root: Path, relative: str, *, label: str) -> bytes:
    parts = PurePosixPath(relative).parts
    descriptors: list[int] = []
    try:
        current = os.open(
            root.resolve(strict=True),
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        descriptors.append(current)
        for part in parts[:-1]:
            current = os.open(
                part,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=current,
            )
            descriptors.append(current)
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
            dir_fd=current,
        )
        descriptors.append(descriptor)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ArchitectureError(f"{label}: must be a regular non-symlink file", code="io")
        if before.st_size > MAX_DOCUMENT_BYTES:
            raise ArchitectureError(f"{label}: document byte limit exceeded", code="limit")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65_536, MAX_DOCUMENT_BYTES + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_DOCUMENT_BYTES:
                raise ArchitectureError(f"{label}: document byte limit exceeded", code="limit")
            chunks.append(chunk)
        after = os.fstat(descriptor)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if total != before.st_size or identity_after != identity_before:
            raise ArchitectureError(f"{label}: file changed while reading", code="io")
        return b"".join(chunks)
    except ArchitectureError:
        raise
    except (OSError, ValueError) as exc:
        raise ArchitectureError(f"{label}: cannot safely read {relative}: {exc}", code="io") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ArchitectureError(f"duplicate JSON key: {key}", code="parse")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise ArchitectureError(f"non-finite JSON number is forbidden: {value}", code="parse")


def _bounded_walk(
    value: Any,
    *,
    depth: int = 0,
    counter: list[int] | None = None,
) -> None:
    if counter is None:
        counter = [0]
    counter[0] += 1
    if counter[0] > MAX_PARSED_NODES:
        raise ArchitectureError("architecture parsed-node limit exceeded", code="limit")
    if depth > MAX_DEPTH:
        raise ArchitectureError("architecture nesting limit exceeded", code="limit")
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise ArchitectureError("unpaired Unicode surrogate is forbidden", code="parse")
    if isinstance(value, dict):
        for key, child in value.items():
            _bounded_walk(key, depth=depth + 1, counter=counter)
            _bounded_walk(child, depth=depth + 1, counter=counter)
    elif isinstance(value, list):
        for child in value:
            _bounded_walk(child, depth=depth + 1, counter=counter)


def _parse_json(data: bytes, *, label: str, counter: list[int] | None = None) -> dict[str, Any]:
    if data.startswith(b"\xef\xbb\xbf"):
        raise ArchitectureError(f"{label}: UTF-8 BOM is forbidden", code="parse")
    try:
        text = data.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_duplicate_rejecting_object,
            parse_constant=_reject_non_finite,
        )
    except ArchitectureError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ArchitectureError(f"{label}: invalid canonical JSON: {exc}", code="parse") from exc
    if not isinstance(value, dict):
        raise ArchitectureError(f"{label}: root must be an object", code="parse")
    _bounded_walk(value, counter=counter)
    return value


def _load_schema(root: Path, relative: Path) -> dict[str, Any]:
    label = relative.as_posix()
    value = _parse_json(_read_regular_bytes(root, label, label=label), label=label)
    try:
        _schema_preflight(value)
    except SpecError as exc:
        raise ArchitectureError(f"{label}: {exc}", code="schema") from exc
    return value


def _validate_against_schema(value: dict[str, Any], schema: dict[str, Any], *, label: str) -> None:
    try:
        validate_schema(value, schema)
    except SpecError as exc:
        raise ArchitectureError(f"{label}: {exc}", code="schema") from exc


def _stable_ids(document: dict[str, Any], collections: tuple[str, ...], *, label: str) -> set[str]:
    all_ids: list[str] = []
    for collection in collections:
        items = document[collection]
        all_ids.extend(str(item["id"]) for item in items)
    if len(all_ids) != len(set(all_ids)):
        raise ArchitectureError(
            f"{label}: stable IDs must be unique across collections", code="reference"
        )
    return set(all_ids)


def _require_references(values: list[str], known: set[str], *, label: str) -> None:
    missing = sorted(set(values) - known)
    if missing:
        raise ArchitectureError(f"{label}: unresolved references: {missing}", code="reference")


def _validate_system_semantics(system: dict[str, Any]) -> None:
    _stable_ids(system, SYSTEM_COLLECTIONS, label="system")
    trust_domains = {item["id"] for item in system["trust_domains"]}
    data_types = {item["id"] for item in system["data_classifications"]}
    secret_classes = {item["id"] for item in system["secret_classes"]}
    signals = {item["id"] for item in system["signals"]}
    contracts = {item["id"] for item in system["contracts"]}
    nodes = {item["id"] for item in system["nodes"]}

    for contract in system["contracts"]:
        _safe_relative_path(contract["path"], label=f"contract {contract['id']}")
    for node in system["nodes"]:
        _require_references(
            [node["trust_domain"]], trust_domains, label=f"node {node['id']} trust_domain"
        )
        _require_references(
            [node["data_classification"]],
            data_types,
            label=f"node {node['id']} data_classification",
        )
        _require_references(node["secrets"], secret_classes, label=f"node {node['id']} secrets")
        _require_references(
            node["public_contracts"], contracts, label=f"node {node['id']} public_contracts"
        )
        for path in node["repository_paths"]:
            _safe_relative_path(path, label=f"node {node['id']} repository path")
    capability_keys: set[str] = set()
    for edge in system["edges"]:
        _require_references(
            [edge["from"], edge["to"]], nodes, label=f"edge {edge['id']} endpoints"
        )
        _require_references(
            edge["allowed_data"], data_types, label=f"edge {edge['id']} allowed_data"
        )
        _require_references(
            [edge["failure_behavior"]["observable_signal"]],
            signals,
            label=f"edge {edge['id']} observable_signal",
        )
        capability = _normalize({key: value for key, value in edge.items() if key != "id"})
        encoded = _canonical_bytes(capability).decode("utf-8")
        if encoded in capability_keys:
            raise ArchitectureError(
                f"edge {edge['id']}: duplicate capability edge",
                code="duplicate_capability",
            )
        capability_keys.add(encoded)


def _validate_rule_semantics(rules: dict[str, Any], system: dict[str, Any]) -> None:
    rule_ids = _stable_ids(rules, RULE_COLLECTIONS, label="rules")
    if len(rule_ids) > MAX_RULES:
        raise ArchitectureError("rules: total rule limit exceeded", code="limit")
    trust_domains = {item["id"] for item in system["trust_domains"]}
    data_types = {item["id"] for item in system["data_classifications"]}
    secret_classes = {item["id"] for item in system["secret_classes"]}
    for rule in rules["forbidden_edges"]:
        _require_references(
            rule["from_trust_domains"], trust_domains, label=f"rule {rule['id']}"
        )
        _require_references(
            rule["to_trust_domains"], trust_domains, label=f"rule {rule['id']}"
        )
    for rule in rules["tenant_authorization_policies"]:
        _require_references(rule["data_classifications"], data_types, label=f"rule {rule['id']}")
    for rule in rules["secret_flow_policies"]:
        _require_references(rule["secret_classes"], secret_classes, label=f"rule {rule['id']}")
        _require_references(rule["allowed_trust_domains"], trust_domains, label=f"rule {rule['id']}")
    for rule in rules["workspace_trust_policies"]:
        _require_references(
            rule["forbidden_secret_classes"], secret_classes, label=f"rule {rule['id']}"
        )
    for collection in RULE_COLLECTIONS:
        for rule in rules[collection]:
            for field in RULE_PATH_FIELDS & set(rule):
                for value in rule[field]:
                    _safe_relative_path(value, label=f"rule {rule['id']} {field}")


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize(child) for key, child in sorted(value.items())}
    if isinstance(value, list):
        normalized = [_normalize(child) for child in value]
        if all(isinstance(child, dict) and "id" in child for child in normalized):
            return sorted(normalized, key=lambda child: child["id"])
        if all(isinstance(child, (str, int, bool)) or child is None for child in normalized):
            return sorted(normalized, key=lambda child: json.dumps(child, ensure_ascii=False))
        return normalized
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _canonical_source_bytes(value: Any) -> bytes:
    text = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    )
    return (text + "\n").encode("utf-8")


def _require_canonical_source(data: bytes, value: dict[str, Any], *, label: str) -> None:
    if data != _canonical_source_bytes(value):
        raise ArchitectureError(
            f"{label}: authority document is not canonical sorted two-space JSON with one newline",
            code="canonical",
        )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def load_architecture(
    root: Path | str,
    system_path: Path | str | None = None,
    rules_path: Path | str | None = None,
) -> ArchitectureSnapshot:
    repository = Path(root)
    try:
        repository = repository.resolve(strict=True)
    except OSError as exc:
        raise ArchitectureError(f"repository root is unavailable: {exc}", code="io") from exc
    if not repository.is_dir():
        raise ArchitectureError("repository root must be a directory", code="io")

    system_relative = _document_relative(
        repository, system_path or SYSTEM_PATH, label="architecture system"
    )
    rules_relative = _document_relative(repository, rules_path or RULES_PATH, label="architecture rules")
    counter = [0]
    system_data = _read_regular_bytes(repository, system_relative, label="architecture system")
    rules_data = _read_regular_bytes(repository, rules_relative, label="architecture rules")
    system = _parse_json(
        system_data,
        label="architecture system",
        counter=counter,
    )
    rules = _parse_json(
        rules_data,
        label="architecture rules",
        counter=counter,
    )
    _require_canonical_source(system_data, system, label="architecture system")
    _require_canonical_source(rules_data, rules, label="architecture rules")
    system_schema = _load_schema(repository, SYSTEM_SCHEMA_PATH)
    rules_schema = _load_schema(repository, RULES_SCHEMA_PATH)
    _validate_against_schema(system, system_schema, label="architecture system")
    _validate_against_schema(rules, rules_schema, label="architecture rules")
    if system["schema_version"] != 1 or rules["schema_version"] != 1:
        raise ArchitectureError("unsupported architecture schema version", code="version")
    if system["architecture_id"] != rules["architecture_id"]:
        raise ArchitectureError("system and rules architecture_id must match", code="reference")
    if len(system["nodes"]) > MAX_MODEL_NODES:
        raise ArchitectureError("system model node limit exceeded", code="limit")
    if len(system["edges"]) > MAX_MODEL_EDGES:
        raise ArchitectureError("system model edge limit exceeded", code="limit")
    _validate_system_semantics(system)
    _validate_rule_semantics(rules, system)
    return ArchitectureSnapshot(
        system=_normalize(system),
        rules=_normalize(rules),
        system_schema=_normalize(system_schema),
        rules_schema=_normalize(rules_schema),
        system_path=system_relative,
        rules_path=rules_relative,
    )


def _inspect_repository_path(root: Path, relative: str, *, regular: bool) -> str | None:
    descriptors: list[int] = []
    parts = PurePosixPath(relative).parts
    try:
        current = os.open(
            root.resolve(strict=True),
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        descriptors.append(current)
        for part in parts[:-1]:
            current = os.open(
                part,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=current,
            )
            descriptors.append(current)
        final = os.open(
            parts[-1],
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
            dir_fd=current,
        )
        descriptors.append(final)
        info = os.fstat(final)
        if regular and not stat.S_ISREG(info.st_mode):
            return "unsafe"
        if not regular and not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            return "unsafe"
        return None
    except FileNotFoundError:
        return "missing"
    except (OSError, ValueError):
        return "unsafe"
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def validate_architecture(
    snapshot: ArchitectureSnapshot,
    root: Path | str,
) -> tuple[ArchitectureFinding, ...]:
    repository = Path(root)
    findings: list[ArchitectureFinding] = []
    seen_repository_paths: set[str] = set()
    for node in snapshot.system["nodes"]:
        for path in node["repository_paths"]:
            if path in seen_repository_paths:
                continue
            seen_repository_paths.add(path)
            result = _inspect_repository_path(repository, path, regular=False)
            if result:
                code = "missing_repository_path" if result == "missing" else "unsafe_repository_path"
                findings.append(
                    ArchitectureFinding(code, f"repository path is {result}: {path}", path)
                )
    for contract in snapshot.system["contracts"]:
        path = contract["path"]
        result = _inspect_repository_path(repository, path, regular=True)
        if result:
            code = "missing_contract" if result == "missing" else "unsafe_contract_path"
            findings.append(ArchitectureFinding(code, f"contract path is {result}: {path}", path))
    return tuple(sorted(findings, key=lambda item: (item.code, item.path, item.message)))


def architecture_digests(snapshot: ArchitectureSnapshot) -> dict[str, str]:
    system_schema_digest = _sha256(snapshot.system_schema)
    rules_schema_digest = _sha256(snapshot.rules_schema)
    schema_digest = _sha256(
        {
            "system_schema_digest": system_schema_digest,
            "rules_schema_digest": rules_schema_digest,
        }
    )
    system_digest = _sha256(snapshot.system)
    rules_digest = _sha256(snapshot.rules)
    architecture_digest = _sha256(
        {
            "contract": "adaptive-grok.architecture",
            "contract_version": 1,
            "schema_digest": schema_digest,
            "system_digest": system_digest,
            "rules_digest": rules_digest,
        }
    )
    return {
        "system_schema_digest": system_schema_digest,
        "rules_schema_digest": rules_schema_digest,
        "schema_digest": schema_digest,
        "system_digest": system_digest,
        "rules_digest": rules_digest,
        "architecture_digest": architecture_digest,
    }


def architecture_fingerprint(
    root: Path | str,
    snapshot: ArchitectureSnapshot,
    *,
    base_sha: str,
    head_sha: str,
    contract_digests: Mapping[str, str],
) -> str:
    repository = Path(root).resolve(strict=True)
    for model_path in (snapshot.system_path, snapshot.rules_path):
        _document_relative(repository, model_path, label="architecture model")
    contracts = [
        {"path": _safe_relative_path(path, label="contract digest"), "digest": digest}
        for path, digest in contract_digests.items()
    ]
    payload = {
        "contract": "adaptive-grok.architecture-fingerprint",
        "contract_version": 1,
        "architecture_configured": True,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "system_path": snapshot.system_path,
        "rules_path": snapshot.rules_path,
        "digests": architecture_digests(snapshot),
        "contract_digests": sorted(contracts, key=lambda item: item["path"]),
    }
    return _sha256(payload)
