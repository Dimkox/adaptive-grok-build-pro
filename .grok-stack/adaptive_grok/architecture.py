from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, Iterable, Mapping

from .spec import SpecError, _schema_preflight, validate_schema

if TYPE_CHECKING:
    from .architecture_diff import ArchitectureDiff
    from .architecture_fitness import FitnessReport

MAX_DOCUMENT_BYTES = 1_000_000
MAX_DEPTH = 64
MAX_PARSED_NODES = 100_000
MAX_MODEL_NODES = 128
MAX_MODEL_EDGES = 512
MAX_RULES = 256
MAX_CONTRACTS = 256
MAX_DRIFT_FINDINGS = 10_000
MAX_DRIFT_ENTRIES = 100_000
MAX_DRIFT_FILES = 20_000
MAX_DRIFT_BYTES = 250_000_000

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


def _secure_open_flags(*, label: str) -> tuple[int, int, int]:
    """Return required descriptor-relative flags, or fail before touching a path."""
    no_follow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    nonblock = getattr(os, "O_NONBLOCK", None)
    supports_dir_fd = getattr(os, "supports_dir_fd", set())
    if (
        not isinstance(no_follow, int)
        or no_follow == 0
        or not isinstance(directory, int)
        or directory == 0
        or not isinstance(nonblock, int)
        or os.open not in supports_dir_fd
    ):
        raise ArchitectureError(
            f"{label}: descriptor-relative no-follow reads are unavailable",
            code="io",
        )
    return no_follow, directory, nonblock


def _read_regular_bytes(root: Path, relative: str, *, label: str) -> bytes:
    no_follow, directory_flag, nonblock = _secure_open_flags(label=label)
    parts = PurePosixPath(relative).parts
    descriptors: list[int] = []
    try:
        current = os.open(
            root.resolve(strict=True),
            os.O_RDONLY | directory_flag | no_follow,
        )
        descriptors.append(current)
        for part in parts[:-1]:
            current = os.open(
                part,
                os.O_RDONLY | directory_flag | no_follow,
                dir_fd=current,
            )
            descriptors.append(current)
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | no_follow | nonblock,
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
    try:
        no_follow, directory_flag, nonblock = _secure_open_flags(
            label="repository path inspection"
        )
    except ArchitectureError:
        return "unsafe"
    descriptors: list[int] = []
    parts = PurePosixPath(relative).parts
    try:
        current = os.open(
            root.resolve(strict=True),
            os.O_RDONLY | directory_flag | no_follow,
        )
        descriptors.append(current)
        for part in parts[:-1]:
            current = os.open(
                part,
                os.O_RDONLY | directory_flag | no_follow,
                dir_fd=current,
            )
            descriptors.append(current)
        final = os.open(
            parts[-1],
            os.O_RDONLY | no_follow | nonblock,
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


_SUPPORTED_SOURCE_SUFFIXES = {
    ".js",
    ".php",
    ".ps1",
    ".py",
    ".sh",
    ".sql",
    ".ts",
}
_SOURCE_LIKE_SUFFIXES = _SUPPORTED_SOURCE_SUFFIXES | {
    ".c",
    ".cpp",
    ".cs",
    ".go",
    ".h",
    ".java",
    ".kt",
    ".kts",
    ".lua",
    ".rb",
    ".rs",
    ".scala",
    ".swift",
}
_DRIFT_CACHE_DIRECTORIES = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}
_NON_AUTHORITATIVE_REPOSITORY_DIRECTORIES = {
    PurePosixPath(".git"),
    PurePosixPath(".superpowers"),
    PurePosixPath("engineering/contracts/examples"),
    PurePosixPath("examples"),
    PurePosixPath("trust-ci/holdout.example"),
}


@dataclass(frozen=True)
class _RepositoryArtifact:
    path: str
    kind: str
    size: int


def _ignore_inventory_directory(relative: PurePosixPath) -> bool:
    return (
        relative in _NON_AUTHORITATIVE_REPOSITORY_DIRECTORIES
        or relative.name in _DRIFT_CACHE_DIRECTORIES
    )


def _inventory_identity(info: os.stat_result) -> tuple[int, int, int]:
    return info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)


def _bounded_repository_inventory(root: Path) -> tuple[_RepositoryArtifact, ...]:
    artifacts: list[_RepositoryArtifact] = []
    entry_count = 0
    file_count = 0
    byte_count = 0
    no_follow, directory_flag, nonblock = _secure_open_flags(
        label="repository drift"
    )

    def walk(directory_fd: int, relative_parent: PurePosixPath, depth: int) -> None:
        nonlocal byte_count, entry_count, file_count
        if depth > MAX_DEPTH:
            raise ArchitectureError("repository drift directory depth limit exceeded", code="limit")
        children: list[tuple[str, PurePosixPath, tuple[int, int, int]]] = []
        with os.scandir(directory_fd) as iterator:
            for entry in iterator:
                entry_count += 1
                if entry_count > MAX_DRIFT_ENTRIES:
                    raise ArchitectureError(
                        "repository drift entry limit exceeded", code="limit"
                    )
                relative = relative_parent / entry.name
                relative_text = relative.as_posix()
                if entry.is_symlink():
                    artifacts.append(_RepositoryArtifact(relative_text, "symlink", 0))
                elif entry.is_dir(follow_symlinks=False):
                    observed = entry.stat(follow_symlinks=False)
                    if not _ignore_inventory_directory(relative):
                        children.append(
                            (entry.name, relative, _inventory_identity(observed))
                        )
                elif entry.is_file(follow_symlinks=False):
                    observed = entry.stat(follow_symlinks=False)
                    descriptor = -1
                    try:
                        descriptor = os.open(
                            entry.name,
                            os.O_RDONLY | no_follow | nonblock,
                            dir_fd=directory_fd,
                        )
                        actual = os.fstat(descriptor)
                    except OSError as exc:
                        raise ArchitectureError(
                            f"repository file failed no-follow identity validation: {relative_text}: {exc}",
                            code="io",
                        ) from exc
                    finally:
                        if descriptor >= 0:
                            os.close(descriptor)
                    if (
                        _inventory_identity(actual) != _inventory_identity(observed)
                        or not stat.S_ISREG(actual.st_mode)
                    ):
                        raise ArchitectureError(
                            f"repository file changed during no-follow inventory: {relative_text}",
                            code="io",
                        )
                    size = actual.st_size
                    file_count += 1
                    byte_count += size
                    if file_count > MAX_DRIFT_FILES:
                        raise ArchitectureError(
                            "repository drift file limit exceeded", code="limit"
                        )
                    if byte_count > MAX_DRIFT_BYTES:
                        raise ArchitectureError(
                            "repository drift byte limit exceeded", code="limit"
                        )
                    artifacts.append(_RepositoryArtifact(relative_text, "file", size))
                else:
                    artifacts.append(_RepositoryArtifact(relative_text, "special", 0))
        for name, relative, observed_identity in sorted(
            children, key=lambda item: item[1].as_posix()
        ):
            descriptor = -1
            try:
                descriptor = os.open(
                    name,
                    os.O_RDONLY | directory_flag | no_follow,
                    dir_fd=directory_fd,
                )
                actual = os.fstat(descriptor)
                if (
                    _inventory_identity(actual) != observed_identity
                    or not stat.S_ISDIR(actual.st_mode)
                ):
                    raise ArchitectureError(
                        f"repository directory changed during no-follow inventory: {relative}",
                        code="io",
                    )
                walk(descriptor, relative, depth + 1)
            except ArchitectureError:
                raise
            except OSError as exc:
                raise ArchitectureError(
                    f"repository directory failed no-follow identity validation: {relative}: {exc}",
                    code="io",
                ) from exc
            finally:
                if descriptor >= 0:
                    os.close(descriptor)

    root_descriptor = -1
    try:
        root_descriptor = os.open(
            root,
            os.O_RDONLY | directory_flag | no_follow,
        )
        walk(root_descriptor, PurePosixPath(), 0)
    except ArchitectureError:
        raise
    except OSError as exc:
        raise ArchitectureError(
            f"repository drift inventory failed closed: {exc}", code="io"
        ) from exc
    finally:
        if root_descriptor >= 0:
            os.close(root_descriptor)
    return tuple(sorted(artifacts, key=lambda item: item.path))


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
    for artifact in _bounded_repository_inventory(repository):
        path = artifact.path
        pure = PurePosixPath(path)
        if artifact.kind != "file":
            findings.append(
                ArchitectureFinding(
                    "unsafe_repository_artifact",
                    f"repository inventory rejects {artifact.kind} artifacts: {path}",
                    path,
                )
            )
            if len(findings) > MAX_DRIFT_FINDINGS:
                raise ArchitectureError(
                    "repository drift finding limit exceeded", code="limit"
                )
            continue
        if pure.parts[:2] == ("engineering", "contracts"):
            if pure.name == ".gitkeep":
                continue
            if path not in declared_contracts:
                findings.append(
                    ArchitectureFinding(
                        "undeclared_contract",
                        f"contract artifact is not declared: {path}",
                        path,
                    )
                )
        suffix = pure.suffix.lower()
        if suffix not in _SOURCE_LIKE_SUFFIXES:
            continue
        if suffix not in _SUPPORTED_SOURCE_SUFFIXES:
            findings.append(
                ArchitectureFinding(
                    "unsupported_source_artifact",
                    f"source-like artifact uses an unsupported language: {path}",
                    path,
                )
            )
        elif not _is_declared(path, declared_paths):
            findings.append(
                ArchitectureFinding(
                    "undeclared_source",
                    f"source artifact is not owned by an architecture node: {path}",
                    path,
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
_SUPPORTED_CONTRACT_KINDS = {"event", "json_schema", "openapi", "signed_payload"}
_SUPPORTED_COMPATIBILITY_MODES = {
    "bidirectional",
    "consumer_accepts_old",
    "exact",
    "producer_accepted_by_old",
    "versioned_break",
}
_NONNEGATIVE_INTEGER_KEYWORDS = {"maxItems", "maxLength", "minItems", "minLength"}
_NUMBER_KEYWORDS = {"maximum", "minimum"}


def _valid_schema_scalar(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool)):
        return True
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _unsupported_schema(schema: Any) -> bool:
    if not isinstance(schema, dict):
        return True
    if set(schema) - _SUPPORTED_SCHEMA_KEYS:
        return True
    if "type" in schema:
        schema_type = schema["type"]
        if not isinstance(schema_type, str) or schema_type not in {
            "array",
            "boolean",
            "integer",
            "null",
            "number",
            "object",
            "string",
        }:
            return True
    for key in ("$id", "$schema", "description"):
        if key in schema and not isinstance(schema[key], str):
            return True
    properties = schema.get("properties", {})
    if not isinstance(properties, dict) or not all(
        isinstance(name, str) for name in properties
    ):
        return True
    required = schema.get("required", [])
    if (
        not isinstance(required, list)
        or not all(isinstance(item, str) for item in required)
        or len(required) != len(set(required))
    ):
        return True
    additional = schema.get("additionalProperties", True)
    if not isinstance(additional, bool):
        return True
    enum = schema.get("enum", [])
    if (
        not isinstance(enum, list)
        or ("enum" in schema and not enum)
        or any(not _valid_schema_scalar(item) for item in enum)
        or len({_canonical_bytes(item) for item in enum}) != len(enum)
    ):
        return True
    for key in _NONNEGATIVE_INTEGER_KEYWORDS:
        value = schema.get(key)
        if key in schema and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            return True
    for key in _NUMBER_KEYWORDS:
        value = schema.get(key)
        if key in schema and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            return True
    for minimum, maximum in (
        ("minItems", "maxItems"),
        ("minLength", "maxLength"),
        ("minimum", "maximum"),
    ):
        if minimum in schema and maximum in schema and schema[minimum] > schema[maximum]:
            return True
    if "pattern" in schema:
        if not isinstance(schema["pattern"], str):
            return True
        try:
            re.compile(schema["pattern"])
        except re.error:
            return True
    if "items" in schema and not isinstance(schema["items"], dict):
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
    base_enum = {_canonical_bytes(item) for item in base.get("enum", [])}
    head_enum = {_canonical_bytes(item) for item in head.get("enum", [])}
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


def _supported_content(content: Any, schemas: list[dict[str, Any]]) -> bool:
    if not isinstance(content, dict) or set(content) != {"application/json"}:
        return False
    media = content["application/json"]
    if not isinstance(media, dict) or set(media) != {"schema"}:
        return False
    schema = media["schema"]
    if _unsupported_schema(schema):
        return False
    schemas.append(schema)
    return True


def _supported_parameter(parameter: Any, schemas: list[dict[str, Any]]) -> bool:
    if not isinstance(parameter, dict) or not set(parameter) <= {
        "description",
        "in",
        "name",
        "required",
        "schema",
    }:
        return False
    if not isinstance(parameter.get("name"), str) or not parameter["name"]:
        return False
    location = parameter.get("in")
    if not isinstance(location, str) or location not in {"cookie", "header", "path", "query"}:
        return False
    required = parameter.get("required", False)
    if not isinstance(required, bool) or (location == "path" and not required):
        return False
    if "description" in parameter and not isinstance(parameter["description"], str):
        return False
    schema = parameter.get("schema")
    if _unsupported_schema(schema):
        return False
    schemas.append(schema)
    return True


def _supported_parameters(parameters: Any, schemas: list[dict[str, Any]]) -> bool:
    if not isinstance(parameters, list):
        return False
    keys: set[tuple[str, str]] = set()
    for parameter in parameters:
        if not _supported_parameter(parameter, schemas):
            return False
        key = _parameter_key(parameter)
        if key in keys:
            return False
        keys.add(key)
    return True


def _security_schemes(document: dict[str, Any]) -> dict[str, dict[str, Any]] | None:
    components = document.get("components", {})
    if not isinstance(components, dict) or not set(components) <= {"securitySchemes"}:
        return None
    schemes = components.get("securitySchemes", {})
    if not isinstance(schemes, dict):
        return None
    for name, scheme in schemes.items():
        if not isinstance(name, str) or not name or not isinstance(scheme, dict):
            return None
        scheme_type = scheme.get("type")
        if scheme_type == "http":
            if not set(scheme) <= {"bearerFormat", "description", "scheme", "type"}:
                return None
            if not isinstance(scheme.get("scheme"), str) or not scheme["scheme"]:
                return None
            if "bearerFormat" in scheme and not isinstance(scheme["bearerFormat"], str):
                return None
        elif scheme_type == "apiKey":
            if not set(scheme) <= {"description", "in", "name", "type"}:
                return None
            location = scheme.get("in")
            if not isinstance(location, str) or location not in {"cookie", "header", "query"}:
                return None
            if not isinstance(scheme.get("name"), str) or not scheme["name"]:
                return None
        else:
            return None
        if "description" in scheme and not isinstance(scheme["description"], str):
            return None
    return schemes


def _supported_security(value: Any, schemes: dict[str, dict[str, Any]]) -> bool:
    if not isinstance(value, list):
        return False
    for requirement in value:
        if not isinstance(requirement, dict):
            return False
        for name, scopes in requirement.items():
            if name not in schemes or scopes != []:
                return False
    return True


def _openapi_schemas(document: Any) -> tuple[dict[str, Any], ...] | None:
    if not isinstance(document, dict) or not set(document) <= {
        "components",
        "info",
        "openapi",
        "paths",
        "security",
    }:
        return None
    if not isinstance(document.get("openapi"), str) or not document["openapi"].startswith("3.1."):
        return None
    info = document.get("info")
    if not isinstance(info, dict) or not set(info) <= {"description", "title", "version"}:
        return None
    if (
        not isinstance(info.get("title"), str)
        or not info["title"]
        or not isinstance(info.get("version"), str)
        or not info["version"]
        or ("description" in info and not isinstance(info["description"], str))
    ):
        return None
    paths = document.get("paths")
    if not isinstance(paths, dict):
        return None
    schemes = _security_schemes(document)
    if schemes is None:
        return None
    if "security" in document and not _supported_security(document["security"], schemes):
        return None
    schemas: list[dict[str, Any]] = []
    for path, path_item in paths.items():
        if not isinstance(path, str) or not path.startswith("/") or not isinstance(path_item, dict):
            return None
        if not set(path_item) <= _HTTP_METHODS | {"description", "parameters", "summary"}:
            return None
        if any(
            key in path_item and not isinstance(path_item[key], str)
            for key in ("description", "summary")
        ):
            return None
        if "parameters" in path_item and not _supported_parameters(
            path_item["parameters"], schemas
        ):
            return None
        for method in _HTTP_METHODS & set(path_item):
            operation = path_item[method]
            if not isinstance(operation, dict) or not set(operation) <= {
                "description",
                "operationId",
                "parameters",
                "requestBody",
                "responses",
                "security",
                "summary",
                "tags",
            }:
                return None
            if any(
                key in operation and not isinstance(operation[key], str)
                for key in ("description", "operationId", "summary")
            ):
                return None
            if "tags" in operation and (
                not isinstance(operation["tags"], list)
                or not all(isinstance(item, str) for item in operation["tags"])
            ):
                return None
            if "parameters" in operation and not _supported_parameters(
                operation["parameters"], schemas
            ):
                return None
            if "security" in operation and not _supported_security(
                operation["security"], schemes
            ):
                return None
            if "requestBody" in operation:
                body = operation["requestBody"]
                if not isinstance(body, dict) or not set(body) <= {
                    "content",
                    "description",
                    "required",
                }:
                    return None
                if "description" in body and not isinstance(body["description"], str):
                    return None
                if "required" in body and not isinstance(body["required"], bool):
                    return None
                if not _supported_content(body.get("content"), schemas):
                    return None
            responses = operation.get("responses")
            if not isinstance(responses, dict) or not responses:
                return None
            for status, response in responses.items():
                if not isinstance(status, str) or not re.fullmatch(r"[1-5][0-9]{2}", status):
                    return None
                if not isinstance(response, dict) or not set(response) <= {
                    "content",
                    "description",
                }:
                    return None
                if not isinstance(response.get("description"), str):
                    return None
                if "content" in response and not _supported_content(
                    response["content"], schemas
                ):
                    return None
    return tuple(schemas)


def _operations(
    document: dict[str, Any],
) -> dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]]:
    result: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]] = {}
    for path, path_item in document["paths"].items():
        for method in _HTTP_METHODS & set(path_item):
            result[(path, method)] = (path_item, path_item[method])
    return result


def _parameter_key(parameter: dict[str, Any]) -> tuple[str, str]:
    name = parameter["name"]
    if parameter["in"] == "header":
        name = name.lower()
    return parameter["in"], name


def _effective_parameters(
    path_item: dict[str, Any], operation: dict[str, Any]
) -> dict[tuple[str, str], dict[str, Any]]:
    result = {
        _parameter_key(parameter): parameter for parameter in path_item.get("parameters", [])
    }
    result.update(
        {_parameter_key(parameter): parameter for parameter in operation.get("parameters", [])}
    )
    return result


def _effective_security(document: dict[str, Any], operation: dict[str, Any]) -> Any:
    return operation["security"] if "security" in operation else document.get("security")


def _security_identity(value: Any) -> tuple[tuple[str, ...], ...]:
    return tuple(sorted(tuple(sorted(requirement)) for requirement in (value or [])))


def _referenced_security(value: Any) -> set[str]:
    return {name for requirement in (value or []) for name in requirement}


def _compare_openapi(base: dict[str, Any], head: dict[str, Any], reasons: set[str]) -> None:
    base_operations = _operations(base)
    head_operations = _operations(head)
    if set(base_operations) - set(head_operations):
        reasons.add("removed_operation")
    for key in sorted(set(base_operations) & set(head_operations)):
        base_path_item, base_operation = base_operations[key]
        head_path_item, head_operation = head_operations[key]
        base_security = _effective_security(base, base_operation)
        head_security = _effective_security(head, head_operation)
        if _security_identity(base_security) != _security_identity(head_security):
            reasons.add(
                "weakened_authentication" if base_security and not head_security else "changed_authentication"
            )
        referenced_schemes = _referenced_security(base_security) | _referenced_security(
            head_security
        )
        base_schemes = _security_schemes(base) or {}
        head_schemes = _security_schemes(head) or {}
        if any(base_schemes.get(name) != head_schemes.get(name) for name in referenced_schemes):
            reasons.add("changed_authentication")
        base_parameters = _effective_parameters(base_path_item, base_operation)
        head_parameters = _effective_parameters(head_path_item, head_operation)
        if set(base_parameters) - set(head_parameters):
            reasons.add("removed_input_parameter")
        for parameter_key in set(head_parameters) - set(base_parameters):
            if head_parameters[parameter_key].get("required", False):
                reasons.add("new_required_input")
        for parameter_key in set(base_parameters) & set(head_parameters):
            base_parameter = base_parameters[parameter_key]
            head_parameter = head_parameters[parameter_key]
            if not base_parameter.get("required", False) and head_parameter.get("required", False):
                reasons.add("new_required_input")
            _compare_schema_direction(
                base_parameter["schema"], head_parameter["schema"], "consumer", reasons
            )
        base_request = _media_schema(base_operation, "requestBody")
        head_request = _media_schema(head_operation, "requestBody")
        if base_request is not None and head_request is not None:
            base_body = base_operation.get("requestBody", {})
            head_body = head_operation.get("requestBody", {})
            if (
                isinstance(base_body, dict)
                and isinstance(head_body, dict)
                and not base_body.get("required", False)
                and head_body.get("required", False)
            ):
                reasons.add("new_required_input")
            _compare_schema_direction(base_request, head_request, "consumer", reasons)
        elif base_request is not None:
            reasons.add("removed_request_schema")
        elif base_request is None and head_request is not None:
            request_body = head_operation.get("requestBody", {})
            if isinstance(request_body, dict) and request_body.get("required"):
                reasons.add("new_required_input")
        base_responses = base_operation.get("responses", {})
        head_responses = head_operation.get("responses", {})
        if set(head_responses) - set(base_responses):
            reasons.add("added_response")
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
            elif head_schema is not None:
                reasons.add("widened_producer_output")


def _event_meaning(document: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    meanings: list[tuple[str, str]] = []

    def visit(schema: dict[str, Any], path: str) -> None:
        if "description" in schema:
            meanings.append((path, schema["description"]))
        for name, child in schema.get("properties", {}).items():
            visit(child, f"{path}/properties/{name}")
        if "items" in schema:
            visit(schema["items"], f"{path}/items")

    visit(document, "$")
    return tuple(meanings)


def compare_contracts(
    base: ContractRecord,
    head: ContractRecord,
    policy: str | Mapping[str, Any],
) -> CompatibilityResult:
    raw_mode = policy.get("compatibility") if isinstance(policy, Mapping) else policy
    if not isinstance(raw_mode, str) or raw_mode not in _SUPPORTED_COMPATIBILITY_MODES:
        return CompatibilityResult("unsupported", ("unsupported_compatibility_policy",))
    mode = raw_mode
    if base.kind not in _SUPPORTED_CONTRACT_KINDS or head.kind not in _SUPPORTED_CONTRACT_KINDS:
        return CompatibilityResult("unsupported", ("unsupported_contract_kind",))
    if (
        not isinstance(base.id, str)
        or not base.id
        or not isinstance(head.id, str)
        or not head.id
        or not isinstance(base.version, str)
        or not base.version
        or not isinstance(head.version, str)
        or not head.version
    ):
        return CompatibilityResult("unsupported", ("malformed_contract_identity",))
    if base.id != head.id or base.kind != head.kind:
        return CompatibilityResult("incompatible", ("contract_identity_changed",))
    documents = (base.document, head.document)
    if base.kind == "openapi":
        if mode not in {"bidirectional", "exact", "versioned_break"}:
            return CompatibilityResult("unsupported", ("unsupported_compatibility_policy",))
        base_schemas = _openapi_schemas(base.document)
        head_schemas = _openapi_schemas(head.document)
        if base_schemas is None or head_schemas is None:
            return CompatibilityResult("unsupported", ("unsupported_openapi_construct",))
        schemas = base_schemas + head_schemas
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
        _compare_openapi(base.document, head.document, reasons)
    else:
        directions = {
            "consumer_accepts_old": ("consumer",),
            "producer_accepted_by_old": ("producer",),
            "bidirectional": ("consumer", "producer"),
        }.get(mode)
        if directions is None:
            return CompatibilityResult("unsupported", ("unsupported_compatibility_policy",))
        if (
            base.kind == "event"
            and base.version == head.version
            and _event_meaning(base.document) != _event_meaning(head.document)
        ):
            reasons.add("event_meaning_changed")
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


def diff_architecture(
    root: Path | str,
    *,
    base_sha: str,
    head_sha: str | None = None,
    worktree: bool = False,
) -> ArchitectureDiff:
    from .architecture_fitness import diff_architecture as evaluate_diff

    return evaluate_diff(root, base_sha=base_sha, head_sha=head_sha, worktree=worktree)


def evaluate_fitness(
    root: Path | str,
    snapshot: ArchitectureSnapshot,
    diff: ArchitectureDiff,
    changed_paths: Iterable[str],
    *,
    pre_risk: str,
) -> FitnessReport:
    from .architecture_fitness import evaluate_fitness as evaluate

    return evaluate(root, snapshot, diff, changed_paths, pre_risk=pre_risk)


def architecture_evidence(
    root: Path | str,
    *,
    base_sha: str,
    head_sha: str,
    pre_risk: str,
) -> dict[str, Any]:
    from .architecture_fitness import architecture_evidence as build_evidence

    return build_evidence(root, base_sha=base_sha, head_sha=head_sha, pre_risk=pre_risk)
