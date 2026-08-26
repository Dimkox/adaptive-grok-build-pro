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
MAX_CONTRACTS = 256
MAX_DRIFT_FINDINGS = 10_000

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


@dataclass(frozen=True)
class ContractRecord:
    id: str
    kind: str
    path: str
    version: str
    role: str
    compatibility: str
    digest: str
    document: dict[str, Any]


@dataclass(frozen=True)
class CompatibilityResult:
    status: str
    reasons: tuple[str, ...]


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
        path = _safe_relative_path(contract["path"], label=f"contract {contract['id']}")
        if Path(path).name == ".gitkeep" or "examples" in PurePosixPath(path).parts:
            raise ArchitectureError(
                f"contract {contract['id']}: examples and .gitkeep are non-authoritative",
                code="contract",
            )
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


def contract_inventory(
    root: Path | str,
    snapshot: ArchitectureSnapshot,
) -> tuple[ContractRecord, ...]:
    repository = Path(root).resolve(strict=True)
    if len(snapshot.system["contracts"]) > MAX_CONTRACTS:
        raise ArchitectureError("contract inventory limit exceeded", code="limit")
    records: list[ContractRecord] = []
    for contract in snapshot.system["contracts"]:
        path = _safe_relative_path(contract["path"], label=f"contract {contract['id']}")
        data = _read_regular_bytes(repository, path, label=f"contract {contract['id']}")
        document = _parse_json(data, label=f"contract {contract['id']}")
        records.append(
            ContractRecord(
                id=contract["id"],
                kind=contract["kind"],
                path=path,
                version=contract["version"],
                role=contract["role"],
                compatibility=contract["compatibility"],
                digest=hashlib.sha256(data).hexdigest(),
                document=document,
            )
        )
    return tuple(sorted(records, key=lambda item: item.id))


def contract_inventory_digest(records: tuple[ContractRecord, ...]) -> str:
    payload = [
        {
            "id": record.id,
            "kind": record.kind,
            "path": record.path,
            "version": record.version,
            "role": record.role,
            "compatibility": record.compatibility,
            "digest": record.digest,
        }
        for record in sorted(records, key=lambda item: item.id)
    ]
    return _sha256({"contract": "adaptive-grok.contract-inventory", "version": 1, "items": payload})


_SOURCE_ROOTS = (
    Path("src"),
    Path("local"),
    Path(".grok/hooks"),
    Path(".grok-stack/adaptive_grok"),
    Path("scripts"),
    Path("trust-ci/src"),
    Path("trust-ci/sql"),
)
_SOURCE_SUFFIXES = {".py", ".php", ".js", ".ts", ".sql"}


def _is_declared(path: str, declarations: set[str]) -> bool:
    return any(path == item or path.startswith(item + "/") for item in declarations)


def validate_repository_drift(
    root: Path | str,
    snapshot: ArchitectureSnapshot,
) -> tuple[ArchitectureFinding, ...]:
    repository = Path(root).resolve(strict=True)
    findings = list(validate_architecture(snapshot, repository))
    declared_paths = {
        path for node in snapshot.system["nodes"] for path in node["repository_paths"]
    }
    declared_contracts = {contract["path"] for contract in snapshot.system["contracts"]}

    contract_root = repository / "engineering/contracts"
    if contract_root.is_dir() and not contract_root.is_symlink():
        for path in sorted(contract_root.rglob("*")):
            relative = path.relative_to(repository).as_posix()
            if (
                not path.is_file()
                or path.is_symlink()
                or path.name == ".gitkeep"
                or "examples" in PurePosixPath(relative).parts
            ):
                continue
            if relative not in declared_contracts:
                findings.append(
                    ArchitectureFinding(
                        "undeclared_contract",
                        f"contract artifact is not declared: {relative}",
                        relative,
                    )
                )
                if len(findings) > MAX_DRIFT_FINDINGS:
                    raise ArchitectureError(
                        "repository drift finding limit exceeded", code="limit"
                    )

    for source_root in _SOURCE_ROOTS:
        absolute = repository / source_root
        if not absolute.is_dir() or absolute.is_symlink():
            continue
        for path in sorted(absolute.rglob("*")):
            if (
                not path.is_file()
                or path.is_symlink()
                or path.suffix not in _SOURCE_SUFFIXES
                or "__pycache__" in path.parts
            ):
                continue
            relative = path.relative_to(repository).as_posix()
            if not _is_declared(relative, declared_paths):
                findings.append(
                    ArchitectureFinding(
                        "undeclared_source",
                        f"source artifact is not owned by an architecture node: {relative}",
                        relative,
                    )
                )
            if len(findings) > MAX_DRIFT_FINDINGS:
                raise ArchitectureError("repository drift finding limit exceeded", code="limit")
    return tuple(sorted(set(findings), key=lambda item: (item.code, item.path, item.message)))


_SUPPORTED_SCHEMA_KEYS = {
    "$schema",
    "$id",
    "description",
    "type",
    "properties",
    "required",
    "additionalProperties",
    "enum",
    "items",
    "minItems",
    "maxItems",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "pattern",
}
_HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def _unsupported_schema(schema: Any) -> bool:
    if not isinstance(schema, dict):
        return True
    if set(schema) - _SUPPORTED_SCHEMA_KEYS:
        return True
    if "type" in schema and schema["type"] not in {
        "array",
        "boolean",
        "integer",
        "null",
        "number",
        "object",
        "string",
    }:
        return True
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return True
    required = schema.get("required", [])
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        return True
    additional = schema.get("additionalProperties", True)
    if not isinstance(additional, bool):
        return True
    enum = schema.get("enum", [])
    if not isinstance(enum, list) or any(
        isinstance(item, (dict, list)) for item in enum
    ):
        return True
    if any(_unsupported_schema(child) for child in properties.values()):
        return True
    if "items" in schema and _unsupported_schema(schema["items"]):
        return True
    return False


def _constraint_breaks(base: dict[str, Any], head: dict[str, Any], direction: str) -> bool:
    minimums = ("minimum", "minLength", "minItems")
    maximums = ("maximum", "maxLength", "maxItems")
    if direction == "consumer":
        return any(head.get(key, float("-inf")) > base.get(key, float("-inf")) for key in minimums) or any(
            head.get(key, float("inf")) < base.get(key, float("inf")) for key in maximums
        )
    return any(head.get(key, float("-inf")) < base.get(key, float("-inf")) for key in minimums) or any(
        head.get(key, float("inf")) > base.get(key, float("inf")) for key in maximums
    )


def _compare_schema_direction(
    base: dict[str, Any],
    head: dict[str, Any],
    direction: str,
    reasons: set[str],
) -> None:
    if base.get("type") != head.get("type"):
        reasons.add("changed_type")
        return
    base_enum = set(base.get("enum", []))
    head_enum = set(head.get("enum", []))
    if direction == "consumer":
        if head_enum and (not base_enum or not base_enum.issubset(head_enum)):
            reasons.add("narrowed_enum")
    elif base_enum and (not head_enum or not head_enum.issubset(base_enum)):
        reasons.add("widened_producer_output")
    if _constraint_breaks(base, head, direction):
        reasons.add("narrowed_constraint" if direction == "consumer" else "widened_producer_output")
    if base.get("pattern") != head.get("pattern"):
        reasons.add("changed_constraint")

    base_properties = base.get("properties", {})
    head_properties = head.get("properties", {})
    base_required = set(base.get("required", []))
    head_required = set(head.get("required", []))
    removed = set(base_properties) - set(head_properties)
    added = set(head_properties) - set(base_properties)
    if direction == "consumer":
        if removed:
            reasons.add("removed_property")
        if head_required - base_required:
            reasons.add("new_required_input")
        if base.get("additionalProperties", True) and not head.get("additionalProperties", True):
            reasons.add("narrowed_additional_properties")
    else:
        if added:
            reasons.add("widened_producer_output")
        if (removed & base_required) or (base_required - head_required):
            reasons.add("widened_producer_output")
        if not base.get("additionalProperties", True) and head.get("additionalProperties", True):
            reasons.add("widened_producer_output")
    for name in sorted(set(base_properties) & set(head_properties)):
        _compare_schema_direction(base_properties[name], head_properties[name], direction, reasons)
    if "items" in base and "items" in head:
        _compare_schema_direction(base["items"], head["items"], direction, reasons)
    elif "items" in base or "items" in head:
        reasons.add("changed_type")


def _content_schema(container: dict[str, Any]) -> dict[str, Any] | None:
    content = container.get("content")
    if not isinstance(content, dict):
        return None
    media = content.get("application/json")
    if not isinstance(media, dict) or not isinstance(media.get("schema"), dict):
        return None
    return media["schema"]


def _media_schema(operation: dict[str, Any], key: str) -> dict[str, Any] | None:
    container = operation.get(key)
    if not isinstance(container, dict):
        return None
    return _content_schema(container)


def _openapi_schemas(document: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    schemas: list[dict[str, Any]] = []
    paths = document.get("paths", {})
    if not isinstance(paths, dict):
        return ({"unsupported": True},)
    for path_item in paths.values():
        if not isinstance(path_item, dict):
            return ({"unsupported": True},)
        for method, operation in path_item.items():
            if method not in _HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                return ({"unsupported": True},)
            if set(operation) & {"callbacks", "parameters"}:
                return ({"unsupported": True},)
            request_schema = _media_schema(operation, "requestBody")
            if request_schema is not None:
                schemas.append(request_schema)
            responses = operation.get("responses", {})
            if not isinstance(responses, dict):
                return ({"unsupported": True},)
            for response in responses.values():
                if not isinstance(response, dict):
                    return ({"unsupported": True},)
                schema = _content_schema(response)
                if schema is not None:
                    schemas.append(schema)
    return tuple(schemas)


def _operations(document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for path, path_item in (document.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method in _HTTP_METHODS and isinstance(operation, dict):
                result[(str(path), method)] = operation
    return result


def _effective_security(document: dict[str, Any], operation: dict[str, Any]) -> Any:
    return operation["security"] if "security" in operation else document.get("security")


def _compare_openapi(base: dict[str, Any], head: dict[str, Any], reasons: set[str]) -> None:
    base_operations = _operations(base)
    head_operations = _operations(head)
    if set(base_operations) - set(head_operations):
        reasons.add("removed_operation")
    for key in sorted(set(base_operations) & set(head_operations)):
        base_operation = base_operations[key]
        head_operation = head_operations[key]
        base_security = _effective_security(base, base_operation)
        head_security = _effective_security(head, head_operation)
        if base_security != head_security:
            reasons.add(
                "weakened_authentication" if base_security and not head_security else "changed_authentication"
            )
        base_request = _media_schema(base_operation, "requestBody")
        head_request = _media_schema(head_operation, "requestBody")
        if base_request is not None and head_request is not None:
            _compare_schema_direction(base_request, head_request, "consumer", reasons)
        elif base_request is not None:
            reasons.add("removed_request_schema")
        elif base_request is None and head_request is not None:
            request_body = head_operation.get("requestBody", {})
            if isinstance(request_body, dict) and request_body.get("required"):
                reasons.add("new_required_input")
        base_responses = base_operation.get("responses", {})
        head_responses = head_operation.get("responses", {})
        for status in set(base_responses) - set(head_responses):
            reasons.add("removed_response")
        for status in set(base_responses) & set(head_responses):
            base_response = base_responses[status]
            head_response = head_responses[status]
            if not isinstance(base_response, dict) or not isinstance(head_response, dict):
                continue
            base_schema = _content_schema(base_response)
            head_schema = _content_schema(head_response)
            if base_schema is not None and head_schema is not None:
                _compare_schema_direction(base_schema, head_schema, "producer", reasons)
            elif base_schema is not None:
                reasons.add("removed_response_schema")


def compare_contracts(
    base: ContractRecord,
    head: ContractRecord,
    policy: str | Mapping[str, Any],
) -> CompatibilityResult:
    mode = str(policy.get("compatibility")) if isinstance(policy, Mapping) else str(policy)
    if base.id != head.id or base.kind != head.kind:
        return CompatibilityResult("incompatible", ("contract_identity_changed",))
    documents = (base.document, head.document)
    if base.kind == "openapi":
        schemas = _openapi_schemas(base.document) + _openapi_schemas(head.document)
    else:
        schemas = documents
    if any(_unsupported_schema(schema) for schema in schemas):
        return CompatibilityResult("unsupported", ("unsupported_schema_keyword",))
    if _canonical_bytes(base.document) == _canonical_bytes(head.document):
        return CompatibilityResult("compatible", ())
    if mode == "exact":
        return CompatibilityResult("incompatible", ("same_version_semantic_change",))
    if mode == "versioned_break":
        reason = (
            "same_version_semantic_change"
            if base.version == head.version
            else "versioned_break_requires_coexistence"
        )
        status = "incompatible" if base.version == head.version else "unsupported"
        return CompatibilityResult(status, (reason,))
    reasons: set[str] = set()
    if base.kind == "openapi":
        if mode != "bidirectional":
            return CompatibilityResult("unsupported", ("unsupported_compatibility_policy",))
        _compare_openapi(base.document, head.document, reasons)
    else:
        directions = {
            "consumer_accepts_old": ("consumer",),
            "producer_accepted_by_old": ("producer",),
            "bidirectional": ("consumer", "producer"),
        }.get(mode)
        if directions is None:
            return CompatibilityResult("unsupported", ("unsupported_compatibility_policy",))
        for direction in directions:
            _compare_schema_direction(base.document, head.document, direction, reasons)
    return CompatibilityResult("incompatible" if reasons else "compatible", tuple(sorted(reasons)))


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
