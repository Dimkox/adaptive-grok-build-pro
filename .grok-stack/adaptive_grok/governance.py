from __future__ import annotations

import dataclasses
import errno
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import unicodedata
import weakref
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Literal

from .architecture import (
    ArchitectureError,
    contract_inventory,
    load_architecture,
)
from .architecture_fitness import architecture_evidence as derive_architecture_evidence
from .spec import SpecError, _schema_preflight, validate_schema


MAX_DOCUMENT_BYTES = 1_000_000
MAX_PARSED_NODES = 100_000
MAX_DEPTH = 64
MAX_RULES = 512
MAX_DEBT_ENTRIES = 2048
MAX_EXAMPLES = 256
MAX_EVIDENCE_REFERENCES = 4096

RULES_PATH = Path("governance/rules/index.json")
DEBT_PATH = Path("governance/debt/index.json")
EXAMPLES_PATH = Path("governance/canonical-examples/index.json")
RULES_SCHEMA_PATH = Path("schemas/governance-rule.schema.json")
DEBT_SCHEMA_PATH = Path("schemas/debt-entry.schema.json")
EXAMPLES_SCHEMA_PATH = Path("schemas/canonical-example.schema.json")
HANDOFF_SCHEMA_PATH = Path("schemas/governance-handoff-v1.schema.json")

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SHA40_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ARCHITECTURE_EVIDENCE_FIELDS = frozenset(
    {
        "architecture_contract_version",
        "architecture_digest",
        "architecture_evidence_digest",
        "base_adoption_digest",
        "base_adoption_state",
        "baseline_introduced",
        "contract_inventory_digest",
        "diff_digest",
        "exact_base_sha",
        "exact_head_sha",
        "exemption_state",
        "fitness_results",
        "fitness_status",
        "head_adoption_digest",
        "head_adoption_state",
        "head_kind",
        "overall_status",
        "repository_inventory_digest",
        "required_scopes",
        "risk_escalation",
        "risk_post",
        "risk_pre",
        "risk_triggers",
        "rules_digest",
        "schema_digest",
        "system_digest",
    }
)
_PROJECTION_BEGIN = "<!-- BEGIN ADAPTIVE GROK GOVERNANCE PROJECTION: {name} -->"
_PROJECTION_END = "<!-- END ADAPTIVE GROK GOVERNANCE PROJECTION: {name} -->"


class GovernanceError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class GovernanceFinding:
    code: str
    message: str
    path: str
    severity: str = "error"


@dataclass(frozen=True)
class GovernanceHandoffV1:
    governance_contract_version: int
    governance_digest: str
    governance_evidence_digest: str
    architecture_digest: str
    exact_base_sha: str
    exact_head_sha: str

    def to_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)


ActorKind = Literal["human", "agent", "system"]
RuleStatus = Literal[
    "candidate", "reviewed", "approved", "active", "deprecated", "revoked"
]


@dataclass(frozen=True)
class ActorRef:
    actor_id: str
    actor_kind: ActorKind

    def __post_init__(self) -> None:
        if not self.actor_id or self.actor_kind not in {"human", "agent", "system"}:
            raise GovernanceError("transition actor is invalid", code="actor")


@dataclass(frozen=True)
class RuleReview:
    actor_id: str
    actor_kind: Literal["human", "system"]
    reviewed_at: str


@dataclass(frozen=True)
class GovernanceApproval:
    actor_id: str
    actor_kind: Literal["human"]
    approved_at: str
    scope: Literal["governance"]


@dataclass(frozen=True)
class EvidenceRef:
    evidence_id: str
    path: str
    sha256: str


@dataclass(frozen=True)
class _DebtEvidenceClaim:
    kind: Literal["observed", "repayment", "acceptance"]
    debt_id: str | None = None
    revision: int | None = None
    behavior_preserving_tests: tuple[str, ...] = ()


@dataclass(frozen=True, init=False, eq=False)
class ExampleRecord:
    _canonical_document: bytes

    def __init__(self, canonical_document: bytes) -> None:
        if not isinstance(canonical_document, bytes):
            raise TypeError("canonical_document must be bytes")
        object.__setattr__(self, "_canonical_document", canonical_document)

    @classmethod
    def from_dict(cls, document: dict[str, Any]) -> ExampleRecord:
        try:
            return cls(_canonical_bytes(document))
        except (KeyError, TypeError, ValueError, UnicodeEncodeError) as exc:
            raise GovernanceError("example record is invalid", code="example") from exc

    def to_dict(self) -> dict[str, Any]:
        return json.loads(self._canonical_document)

    @property
    def example_id(self) -> str:
        return self.to_dict()["example_id"]

    @property
    def category(self) -> str:
        return self.to_dict()["category"]

    @property
    def status(self) -> str:
        return self.to_dict()["status"]

    @property
    def evidence(self) -> tuple[EvidenceRef, ...]:
        return tuple(EvidenceRef(**item) for item in self.to_dict()["evidence"])


@dataclass(frozen=True, init=False, eq=False)
class DebtRecord:
    _canonical_document: bytes

    def __init__(self, canonical_document: bytes) -> None:
        if not isinstance(canonical_document, bytes):
            raise TypeError("canonical_document must be bytes")
        object.__setattr__(self, "_canonical_document", canonical_document)

    @classmethod
    def from_dict(cls, document: dict[str, Any]) -> DebtRecord:
        try:
            return cls(_canonical_bytes(document))
        except (KeyError, TypeError, ValueError, UnicodeEncodeError) as exc:
            raise GovernanceError("debt record is invalid", code="debt") from exc

    def to_dict(self) -> dict[str, Any]:
        return json.loads(self._canonical_document)

    @property
    def debt_id(self) -> str:
        return self.to_dict()["debt_id"]

    @property
    def status(self) -> str:
        return self.to_dict()["status"]


@dataclass(frozen=True, init=False, eq=False)
class RuleRecord:
    _canonical_document: bytes

    def __init__(self, canonical_document: bytes) -> None:
        if not isinstance(canonical_document, bytes):
            raise TypeError("canonical_document must be bytes")
        object.__setattr__(self, "_canonical_document", canonical_document)

    @classmethod
    def from_dict(cls, document: dict[str, Any]) -> RuleRecord:
        try:
            canonical = _canonical_bytes(document)
        except (KeyError, TypeError, ValueError, UnicodeEncodeError) as exc:
            raise GovernanceError("rule record is invalid", code="rule") from exc
        return cls(canonical)

    def to_dict(self) -> dict[str, Any]:
        return json.loads(self._canonical_document)

    @property
    def rule_id(self) -> str:
        return self.to_dict()["rule_id"]

    @property
    def source_task(self) -> str:
        return self.to_dict()["source_task"]

    @property
    def author(self) -> ActorRef:
        author = self.to_dict()["author"]
        return ActorRef(author["actor_id"], author["actor_kind"])

    @property
    def created_at(self) -> str:
        return self.to_dict()["created_at"]

    @property
    def expires_at(self) -> str | None:
        return self.to_dict()["expires_at"]

    @property
    def status(self) -> RuleStatus:
        return self.to_dict()["status"]

    @property
    def revision(self) -> int:
        return self.to_dict()["revision"]

    @property
    def evidence(self) -> tuple[EvidenceRef, ...]:
        return tuple(EvidenceRef(**item) for item in self.to_dict()["evidence"])

    @property
    def reviewed_by(self) -> tuple[RuleReview, ...]:
        return tuple(RuleReview(**item) for item in self.to_dict()["reviewed_by"])

    @property
    def approved_by(self) -> tuple[GovernanceApproval, ...]:
        return tuple(
            GovernanceApproval(**item) for item in self.to_dict()["approved_by"]
        )


@dataclass(frozen=True)
class GovernanceSnapshot:
    rules: dict[str, Any]
    debt: dict[str, Any]
    examples: dict[str, Any]
    rules_schema: dict[str, Any]
    debt_schema: dict[str, Any]
    examples_schema: dict[str, Any]
    handoff_schema: dict[str, Any]
    rules_path: str
    debt_path: str
    examples_path: str
    rule_records: tuple[RuleRecord, ...] = ()
    example_records: tuple[ExampleRecord, ...] = ()
    debt_records: tuple[DebtRecord, ...] = ()


@dataclass(frozen=True)
class _RepositoryHandle:
    path: Path
    descriptor: int
    identity: tuple[int, int]


def _unsafe_text(value: str) -> bool:
    return any(
        unicodedata.category(character) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        for character in value
    )


def _safe_relative_path(root_descriptor: int, value: str, *, label: str) -> str:
    if not isinstance(value, str):
        raise GovernanceError(f"{label}: path must be a string", code="path")
    raw_parts = value.split("/")
    pure = PurePosixPath(value)
    if (
        not value
        or _unsafe_text(value)
        or unicodedata.normalize("NFC", value) != value
        or "\\" in value
        or pure.is_absolute()
        or value.endswith("/")
        or any(part in {"", ".", ".."} for part in raw_parts)
    ):
        raise GovernanceError(
            f"{label}: unsafe repository-relative path {value!r}", code="path"
        )
    no_follow, directory_flag, nonblock = _secure_open_flags(label=label)
    descriptors: list[int] = []
    current = root_descriptor
    try:
        for index, part in enumerate(raw_parts):
            final = index == len(raw_parts) - 1
            flags = os.O_RDONLY | no_follow | nonblock
            if not final:
                flags |= directory_flag
            try:
                current = os.open(part, flags, dir_fd=current)
            except FileNotFoundError:
                return pure.as_posix()
            descriptors.append(current)
            info = os.fstat(current)
            if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
                raise GovernanceError(
                    f"{label}: path resolves to an unsafe file type", code="path"
                )
        return pure.as_posix()
    except GovernanceError:
        raise
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.EMLINK, errno.ENOTDIR}:
            raise GovernanceError(
                f"{label}: path cannot resolve safely; path escapes repository boundary or is not a directory",
                code="path",
            ) from exc
        raise GovernanceError(f"{label}: path cannot resolve safely", code="path") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _secure_open_flags(*, label: str) -> tuple[int, int, int]:
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
        or nonblock == 0
        or os.open not in supports_dir_fd
    ):
        raise GovernanceError(
            f"{label}: descriptor-relative no-follow reads are unavailable", code="io"
        )
    return no_follow, directory, nonblock


def _open_repository(root: Path | str) -> _RepositoryHandle:
    label = "repository root"
    no_follow, directory_flag, nonblock = _secure_open_flags(label=label)
    repository = Path(os.path.abspath(Path(root)))
    try:
        named = os.lstat(repository)
        if stat.S_ISLNK(named.st_mode) or not stat.S_ISDIR(named.st_mode):
            raise GovernanceError(
                "repository root must be a regular non-symlink directory", code="io"
            )
        descriptor = os.open(
            repository,
            os.O_RDONLY | directory_flag | no_follow | nonblock,
        )
        try:
            opened = os.fstat(descriptor)
            identity = (opened.st_dev, opened.st_ino)
            if (
                not stat.S_ISDIR(opened.st_mode)
                or identity != (named.st_dev, named.st_ino)
            ):
                raise GovernanceError("repository root changed while opening", code="io")
        except BaseException:
            os.close(descriptor)
            raise
    except GovernanceError:
        raise
    except OSError as exc:
        raise GovernanceError(f"repository root is unavailable: {exc}", code="io") from exc
    return _RepositoryHandle(repository, descriptor, identity)


def _verify_repository(handle: _RepositoryHandle) -> None:
    try:
        opened = os.fstat(handle.descriptor)
        named = os.lstat(handle.path)
    except OSError as exc:
        raise GovernanceError("repository root changed while loading", code="io") from exc
    if (
        not stat.S_ISDIR(opened.st_mode)
        or stat.S_ISLNK(named.st_mode)
        or not stat.S_ISDIR(named.st_mode)
        or (opened.st_dev, opened.st_ino) != handle.identity
        or (named.st_dev, named.st_ino) != handle.identity
    ):
        raise GovernanceError("repository root changed while loading", code="io")


def _read_regular_bytes(root_descriptor: int, relative: str, *, label: str) -> bytes:
    no_follow, directory_flag, nonblock = _secure_open_flags(label=label)
    parts = PurePosixPath(relative).parts
    descriptors: list[int] = []
    try:
        current = root_descriptor
        for part in parts[:-1]:
            current = os.open(
                part,
                os.O_RDONLY | directory_flag | no_follow | nonblock,
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
            raise GovernanceError(
                f"{label}: must be a regular non-symlink file", code="io"
            )
        if before.st_size > MAX_DOCUMENT_BYTES:
            raise GovernanceError(f"{label}: document byte limit exceeded", code="limit")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65_536, MAX_DOCUMENT_BYTES + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_DOCUMENT_BYTES:
                raise GovernanceError(
                    f"{label}: document byte limit exceeded", code="limit"
                )
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
            raise GovernanceError(f"{label}: file changed while reading", code="io")
        return b"".join(chunks)
    except GovernanceError:
        raise
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.EMLINK}:
            raise GovernanceError(
                f"{label}: must be a regular non-symlink file", code="io"
            ) from exc
        raise GovernanceError(
            f"{label}: cannot safely read {relative}: {exc}", code="io"
        ) from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GovernanceError(f"duplicate JSON key: {key}", code="parse")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise GovernanceError(f"non-finite JSON number is forbidden: {value}", code="parse")


def _parse_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        _reject_non_finite(value)
    return parsed


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
        raise GovernanceError("governance parsed-node limit exceeded", code="limit")
    if depth > MAX_DEPTH:
        raise GovernanceError("governance nesting limit exceeded", code="limit")
    if isinstance(value, str) and any(
        0xD800 <= ord(character) <= 0xDFFF for character in value
    ):
        raise GovernanceError("unpaired Unicode surrogate is forbidden", code="parse")
    if isinstance(value, dict):
        for key, child in value.items():
            _bounded_walk(key, depth=depth + 1, counter=counter)
            _bounded_walk(child, depth=depth + 1, counter=counter)
    elif isinstance(value, list):
        for child in value:
            _bounded_walk(child, depth=depth + 1, counter=counter)


def load_bytes(
    data: bytes,
    *,
    label: str = "governance document",
    _counter: list[int] | None = None,
) -> dict[str, Any]:
    if len(data) > MAX_DOCUMENT_BYTES:
        raise GovernanceError(f"{label}: document byte limit exceeded", code="limit")
    if data.startswith(b"\xef\xbb\xbf"):
        raise GovernanceError(f"{label}: UTF-8 BOM is forbidden", code="parse")
    try:
        value = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_duplicate_rejecting_object,
            parse_constant=_reject_non_finite,
            parse_float=_parse_float,
        )
    except GovernanceError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise GovernanceError(
            f"{label}: invalid canonical JSON: {exc}", code="parse"
        ) from exc
    if not isinstance(value, dict):
        raise GovernanceError(f"{label}: root must be an object", code="parse")
    _bounded_walk(value, counter=_counter)
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
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _require_canonical_source(data: bytes, value: dict[str, Any], *, label: str) -> None:
    if data != _canonical_source_bytes(value):
        raise GovernanceError(
            f"{label}: authority document is not canonical sorted two-space JSON with one newline",
            code="canonical",
        )


def _load_document(
    root_descriptor: int,
    relative: Path,
    *,
    counter: list[int],
) -> tuple[bytes, dict[str, Any]]:
    label = relative.as_posix()
    data = _read_regular_bytes(root_descriptor, label, label=label)
    return data, load_bytes(data, label=label, _counter=counter)


def _schema_preflight_checked(schema: dict[str, Any], *, label: str) -> None:
    try:
        _schema_preflight(schema)
    except SpecError as exc:
        raise GovernanceError(f"{label}: {exc}", code="schema") from exc
    definitions = schema.get("$defs", {})

    def visit(node: Any, *, path: str, definition: bool = False) -> None:
        if not isinstance(node, dict):
            kind = "schema reference target" if definition else "schema declaration"
            raise GovernanceError(
                f"{label}: {path}: {kind} must be an object", code="schema"
            )
        reference = node.get("$ref")
        if reference is not None:
            if definition:
                raise GovernanceError(
                    f"{label}: {path}: schema reference aliases are unsupported",
                    code="schema",
                )
            prefix = "#/$defs/"
            if (
                not isinstance(reference, str)
                or not reference.startswith(prefix)
                or not reference[len(prefix) :]
                or "/" in reference[len(prefix) :]
            ):
                raise GovernanceError(
                    f"{label}: {path}: schema reference must be a local #/$defs name",
                    code="schema",
                )
            target = definitions.get(reference[len(prefix) :])
            if not isinstance(target, dict):
                raise GovernanceError(
                    f"{label}: {path}: schema reference target is missing or not an object",
                    code="schema",
                )
        for key in ("properties", "$defs"):
            children = node.get(key, {})
            if not isinstance(children, dict):
                raise GovernanceError(
                    f"{label}: {path}.{key}: schema declaration must be an object",
                    code="schema",
                )
            for name, child in children.items():
                visit(
                    child,
                    path=f"{path}.{key}.{name}",
                    definition=key == "$defs",
                )
        if "items" in node:
            visit(node["items"], path=f"{path}.items")

    visit(schema, path="$")


def _validate_schema_checked(
    document: dict[str, Any], schema: dict[str, Any], *, label: str
) -> None:
    try:
        validate_schema(document, schema)
    except SpecError as exc:
        raise GovernanceError(f"{label}: {exc}", code="schema") from exc


def _require_unique_ids(
    records: list[dict[str, Any]], *, field: str, label: str
) -> None:
    values = [record[field] for record in records]
    if len(values) != len(set(values)):
        raise GovernanceError(f"{label}: duplicate {field}", code="reference")


def _record_paths(snapshot: GovernanceSnapshot) -> list[tuple[str, str]]:
    paths: list[tuple[str, str]] = []
    for index, rule in enumerate(snapshot.rules["rules"]):
        for path in rule["scope"]["repository_paths"]:
            paths.append((f"rules[{index}].scope.repository_paths", path))
        for evidence in rule["evidence"]:
            paths.append((f"rules[{index}].evidence", evidence["path"]))
    for index, entry in enumerate(snapshot.debt["entries"]):
        for path in entry["behavior_preserving_tests"]:
            paths.append((f"entries[{index}].behavior_preserving_tests", path))
        for evidence in entry["evidence"]:
            paths.append((f"entries[{index}].evidence", evidence["path"]))
    for index, example in enumerate(snapshot.examples["examples"]):
        for path in example["repository_paths"]:
            paths.append((f"examples[{index}].repository_paths", path))
        for evidence in example["evidence"]:
            paths.append((f"examples[{index}].evidence", evidence["path"]))
    return paths


def _validate_structural_semantics(
    snapshot: GovernanceSnapshot, root_descriptor: int
) -> None:
    rules = snapshot.rules["rules"]
    debt = snapshot.debt["entries"]
    examples = snapshot.examples["examples"]
    if len(rules) > MAX_RULES:
        raise GovernanceError("governance rule limit exceeded", code="limit")
    if len(debt) > MAX_DEBT_ENTRIES:
        raise GovernanceError("governance debt-entry limit exceeded", code="limit")
    if len(examples) > MAX_EXAMPLES:
        raise GovernanceError("governance example limit exceeded", code="limit")
    evidence_count = sum(len(record["evidence"]) for record in rules)
    evidence_count += sum(len(record["evidence"]) for record in debt)
    evidence_count += sum(len(record["evidence"]) for record in examples)
    if evidence_count > MAX_EVIDENCE_REFERENCES:
        raise GovernanceError("governance evidence-reference limit exceeded", code="limit")
    _require_unique_ids(rules, field="rule_id", label="governance rules")
    _require_unique_ids(debt, field="debt_id", label="governance debt")
    _require_unique_ids(examples, field="example_id", label="governance examples")
    for label, path in _record_paths(snapshot):
        _safe_relative_path(root_descriptor, path, label=label)


def _normalize_mapping(value: dict[str, Any]) -> dict[str, Any]:
    return {key: _normalize_generic(child) for key, child in sorted(value.items())}


def _normalize_generic(value: Any) -> Any:
    if isinstance(value, dict):
        return _normalize_mapping(value)
    if isinstance(value, list):
        return [_normalize_generic(child) for child in value]
    return value


def _normalize_set(values: list[Any]) -> list[Any]:
    normalized = [_normalize_generic(value) for value in values]
    return sorted(normalized, key=_canonical_bytes)


def _normalize_rule(rule: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_mapping(rule)
    normalized["approved_by"] = _normalize_set(rule["approved_by"])
    normalized["evidence"] = _normalize_set(rule["evidence"])
    normalized["reviewed_by"] = _normalize_set(rule["reviewed_by"])
    normalized["supersedes"] = _normalize_set(rule["supersedes"])
    normalized["scope"] = _normalize_mapping(rule["scope"])
    for field in ("domains", "repository_paths", "route_intents"):
        normalized["scope"][field] = _normalize_set(rule["scope"][field])
    return normalized


def _normalize_debt(entry: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_mapping(entry)
    normalized["behavior_preserving_tests"] = _normalize_set(
        entry["behavior_preserving_tests"]
    )
    normalized["evidence"] = _normalize_set(entry["evidence"])
    return normalized


def _normalize_example(example: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_mapping(example)
    for field in (
        "approved_by",
        "contract_ids",
        "evidence",
        "repository_paths",
        "reviewed_by",
        "supersedes",
    ):
        normalized[field] = _normalize_set(example[field])
    return normalized


def _normalize_root(
    document: dict[str, Any],
    *,
    collection: str,
    normalize_record: Callable[[dict[str, Any]], dict[str, Any]],
    stable_fields: tuple[str, ...],
) -> dict[str, Any]:
    normalized = _normalize_mapping(document)
    records = [normalize_record(record) for record in document[collection]]
    normalized[collection] = sorted(
        records,
        key=lambda record: tuple(record[field] for field in stable_fields),
    )
    return normalized


def _load_governance_snapshot(
    root: Path | str,
) -> tuple[GovernanceSnapshot, Path, tuple[int, int]]:
    repository = _open_repository(root)
    try:
        counter = [0]
        schema_documents: dict[Path, dict[str, Any]] = {}
        for relative in (
            RULES_SCHEMA_PATH,
            DEBT_SCHEMA_PATH,
            EXAMPLES_SCHEMA_PATH,
            HANDOFF_SCHEMA_PATH,
        ):
            _, schema = _load_document(
                repository.descriptor, relative, counter=counter
            )
            _schema_preflight_checked(schema, label=relative.as_posix())
            schema_documents[relative] = schema

        _validate_schema_checked(
            {
                "architecture_digest": "a" * 64,
                "exact_base_sha": "b" * 40,
                "exact_head_sha": "c" * 40,
                "governance_contract_version": 1,
                "governance_digest": "d" * 64,
                "governance_evidence_digest": "e" * 64,
            },
            schema_documents[HANDOFF_SCHEMA_PATH],
            label=HANDOFF_SCHEMA_PATH.as_posix(),
        )

        registry_documents: dict[Path, dict[str, Any]] = {}
        for relative in (RULES_PATH, DEBT_PATH, EXAMPLES_PATH):
            data, document = _load_document(
                repository.descriptor, relative, counter=counter
            )
            _require_canonical_source(data, document, label=relative.as_posix())
            registry_documents[relative] = document

        _validate_schema_checked(
            registry_documents[RULES_PATH],
            schema_documents[RULES_SCHEMA_PATH],
            label=RULES_PATH.as_posix(),
        )
        _validate_schema_checked(
            registry_documents[DEBT_PATH],
            schema_documents[DEBT_SCHEMA_PATH],
            label=DEBT_PATH.as_posix(),
        )
        _validate_schema_checked(
            registry_documents[EXAMPLES_PATH],
            schema_documents[EXAMPLES_SCHEMA_PATH],
            label=EXAMPLES_PATH.as_posix(),
        )

        normalized_rules = _normalize_root(
            registry_documents[RULES_PATH],
            collection="rules",
            normalize_record=_normalize_rule,
            stable_fields=("rule_id", "revision"),
        )
        normalized_debt = _normalize_root(
            registry_documents[DEBT_PATH],
            collection="entries",
            normalize_record=_normalize_debt,
            stable_fields=("debt_id", "revision"),
        )
        normalized_examples = _normalize_root(
            registry_documents[EXAMPLES_PATH],
            collection="examples",
            normalize_record=_normalize_example,
            stable_fields=("example_id", "version"),
        )
        snapshot = GovernanceSnapshot(
            rules=normalized_rules,
            debt=normalized_debt,
            examples=normalized_examples,
            rules_schema=_normalize_generic(schema_documents[RULES_SCHEMA_PATH]),
            debt_schema=_normalize_generic(schema_documents[DEBT_SCHEMA_PATH]),
            examples_schema=_normalize_generic(schema_documents[EXAMPLES_SCHEMA_PATH]),
            handoff_schema=_normalize_generic(schema_documents[HANDOFF_SCHEMA_PATH]),
            rules_path=RULES_PATH.as_posix(),
            debt_path=DEBT_PATH.as_posix(),
            examples_path=EXAMPLES_PATH.as_posix(),
            rule_records=tuple(
                RuleRecord.from_dict(rule)
                for rule in normalized_rules["rules"]
            ),
            example_records=tuple(
                ExampleRecord.from_dict(example)
                for example in normalized_examples["examples"]
            ),
            debt_records=tuple(
                DebtRecord.from_dict(entry)
                for entry in normalized_debt["entries"]
            ),
        )
        _validate_structural_semantics(snapshot, repository.descriptor)
        _verify_repository(repository)
        return snapshot, repository.path, repository.identity
    finally:
        os.close(repository.descriptor)


_RULE_TRANSITIONS: dict[RuleStatus, frozenset[RuleStatus]] = {
    "candidate": frozenset({"reviewed"}),
    "reviewed": frozenset({"approved"}),
    "approved": frozenset({"active"}),
    "active": frozenset({"deprecated", "revoked"}),
    "deprecated": frozenset({"revoked"}),
    "revoked": frozenset(),
}


def _require_aware(value: datetime, *, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise GovernanceError(f"{label} must be timezone-aware", code="timestamp")
    return value.astimezone(timezone.utc)


def _format_timestamp(value: datetime) -> str:
    normalized = _require_aware(value, label="transition timestamp")
    rendered = normalized.isoformat(timespec="microseconds")
    if normalized.microsecond == 0:
        rendered = normalized.isoformat(timespec="seconds")
    return rendered.replace("+00:00", "Z")


def _parse_timestamp(value: str, *, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except (AttributeError, TypeError, ValueError) as exc:
        raise GovernanceError(f"{label} is not a valid UTC timestamp", code="timestamp") from exc
    return _require_aware(parsed, label=label)


def _has_independent_review(rule: RuleRecord) -> bool:
    return any(review.actor_id != rule.author.actor_id for review in rule.reviewed_by)


def _has_human_governance_approval(rule: RuleRecord) -> bool:
    return any(
        approval.actor_kind == "human" and approval.scope == "governance"
        for approval in rule.approved_by
    )


def _has_evidence_digests(rule: RuleRecord) -> bool:
    return bool(rule.evidence) and all(
        evidence.path
        and len(evidence.sha256) == 64
        and all(character in "0123456789abcdef" for character in evidence.sha256)
        for evidence in rule.evidence
    )


def _snapshot_rule_records(
    snapshot: GovernanceSnapshot,
) -> tuple[RuleRecord, ...]:
    documents = snapshot.rules["rules"]
    if len(snapshot.rule_records) != len(documents):
        return ()
    if any(
        record._canonical_document != _canonical_bytes(document)
        for record, document in zip(snapshot.rule_records, documents)
    ):
        return ()
    return snapshot.rule_records


def _snapshot_example_records(snapshot: GovernanceSnapshot) -> tuple[ExampleRecord, ...]:
    documents = snapshot.examples["examples"]
    if len(snapshot.example_records) != len(documents):
        return ()
    if any(
        record._canonical_document != _canonical_bytes(document)
        for record, document in zip(snapshot.example_records, documents)
    ):
        return ()
    return snapshot.example_records


def _snapshot_debt_records(snapshot: GovernanceSnapshot) -> tuple[DebtRecord, ...]:
    documents = snapshot.debt["entries"]
    if len(snapshot.debt_records) != len(documents):
        return ()
    if any(
        record._canonical_document != _canonical_bytes(document)
        for record, document in zip(snapshot.debt_records, documents)
    ):
        return ()
    return snapshot.debt_records


def _evidence_contents(
    repository: _RepositoryHandle,
    evidence: list[dict[str, Any]],
    *,
    owner: str,
    prefix: str,
) -> tuple[list[GovernanceFinding], list[bytes]]:
    findings: list[GovernanceFinding] = []
    contents: list[bytes] = []
    if not evidence:
        return [GovernanceFinding(f"{prefix}-evidence-required", f"{owner} requires evidence", owner)], contents
    for item in evidence:
        path = item.get("path", "")
        try:
            _safe_relative_path(repository.descriptor, path, label=f"{owner} evidence")
            content = _read_regular_bytes(repository.descriptor, path, label=f"{owner} evidence")
        except GovernanceError:
            findings.append(GovernanceFinding(f"{prefix}-evidence-unavailable", f"{owner} evidence is unavailable", path))
            continue
        if hashlib.sha256(content).hexdigest() != item.get("sha256"):
            findings.append(GovernanceFinding(f"{prefix}-evidence-digest-mismatch", f"{owner} evidence digest does not match", path))
            continue
        contents.append(content)
    return findings, contents


def _example_content_digest(files: list[tuple[str, bytes]]) -> str:
    payload = {
        "contract": "adaptive-grok.canonical-example-content",
        "files": [
            {"path": path, "sha256": hashlib.sha256(content).hexdigest()}
            for path, content in sorted(files)
        ],
        "version": 1,
    }
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _m2_contract_ids(root: Path) -> frozenset[str]:
    try:
        architecture = load_architecture(root)
        return frozenset(record.id for record in contract_inventory(root, architecture))
    except (ArchitectureError, OSError, ValueError):
        return frozenset()


def _example_findings(
    examples: tuple[ExampleRecord, ...],
    repository: _RepositoryHandle,
) -> list[GovernanceFinding]:
    findings: list[GovernanceFinding] = []
    all_documents = [record.to_dict() for record in examples]
    contract_ids = (
        _m2_contract_ids(repository.path)
        if any(document.get("status") == "active" for document in all_documents)
        else frozenset()
    )
    for document in all_documents:
        if document.get("status") != "active":
            continue
        example_id = document.get("example_id", "unknown")
        path = f"examples[{example_id}]"
        approvals = document.get("approved_by", [])
        approval_ids = {item.get("actor_id") for item in approvals}
        reviews = document.get("reviewed_by", [])
        if not reviews or not any(item.get("actor_id") not in approval_ids for item in reviews):
            findings.append(GovernanceFinding("example-review-required", f"example {example_id} requires independent review", path))
        if not any(item.get("actor_kind") == "human" and item.get("scope") == "governance" for item in approvals):
            findings.append(GovernanceFinding("example-approval-required", f"example {example_id} requires human governance approval", path))
        findings.append(
            GovernanceFinding(
                "example-external-authority-required",
                f"example {example_id} requires independently verified exact-record review and approval authority",
                path,
            )
        )
        evidence_findings, _ = _evidence_contents(repository, document.get("evidence", []), owner=path, prefix="example")
        findings.extend(evidence_findings)
        files: list[tuple[str, bytes]] = []
        repository_paths = document.get("repository_paths", [])
        if not repository_paths:
            findings.append(GovernanceFinding("example-path-required", f"example {example_id} requires a repository path", path))
        for relative in repository_paths:
            try:
                _safe_relative_path(repository.descriptor, relative, label=f"example {example_id} path")
                files.append((relative, _read_regular_bytes(repository.descriptor, relative, label=f"example {example_id} path")))
            except GovernanceError:
                findings.append(GovernanceFinding("example-path-unavailable", f"example {example_id} path is unavailable", relative))
        if files and len(files) == len(document.get("repository_paths", [])) and _example_content_digest(files) != document.get("digest"):
            findings.append(GovernanceFinding("example-digest-mismatch", f"example {example_id} content digest does not match", path))
        references = document.get("contract_ids", [])
        if not references:
            findings.append(GovernanceFinding("example-contract-required", f"example {example_id} requires an M2 contract reference", path))
        for contract_id in references:
            if contract_id not in contract_ids:
                findings.append(GovernanceFinding("example-contract-unresolved", f"example {example_id} contract is unresolved", contract_id))

    for index, current in enumerate(all_documents):
        if current.get("status") != "active":
            continue
        current_paths = tuple(current.get("repository_paths", []))
        related = [
            item
            for item in all_documents
            if item.get("category") == current.get("category")
            and any(
                _path_overlaps(first, second)
                for first in current_paths
                for second in item.get("repository_paths", [])
            )
        ]
        for other in all_documents[index + 1 :]:
            if (
                other.get("status") == "active"
                and other.get("category") == current.get("category")
                and any(
                    _path_overlaps(first, second)
                    for first in current_paths
                    for second in other.get("repository_paths", [])
                )
            ):
                category = current.get("category")
                findings.append(GovernanceFinding("example-active-version-conflict", f"category/scope {category} has multiple active examples", f"examples[{category}]"))
        older = [item for item in related if item.get("version", 0) < current.get("version", 0)]
        missing = sorted(item.get("example_id", "") for item in older if item.get("example_id") not in current.get("supersedes", []))
        if missing:
            findings.append(GovernanceFinding("example-supersession-required", f"example {current.get('example_id')} must explicitly supersede older versions: {', '.join(missing)}", f"examples[{current.get('example_id')}]"))
    return findings


def _parse_debt_evidence_documents(
    contents: list[bytes],
    repository: _RepositoryHandle,
    *,
    owner: str,
) -> tuple[list[GovernanceFinding], list[_DebtEvidenceClaim]]:
    findings: list[GovernanceFinding] = []
    claims: list[_DebtEvidenceClaim] = []
    for index, content in enumerate(contents):
        evidence_path = f"{owner}.evidence[{index}]"
        try:
            document = load_bytes(content, label="governance evidence")
            keys = frozenset(document)
            status = document.get("status")
            if status == "observed" and keys == {"status"}:
                claims.append(_DebtEvidenceClaim("observed"))
                continue
            if status == "pass":
                if keys != {
                    "behavior_preserving_tests",
                    "debt_id",
                    "revision",
                    "status",
                }:
                    raise GovernanceError(
                        "repayment evidence has unknown or missing fields",
                        code="evidence",
                    )
                debt_id = document.get("debt_id")
                revision = document.get("revision")
                tests = document.get("behavior_preserving_tests")
                if (
                    not isinstance(debt_id, str)
                    or not debt_id
                    or len(debt_id) > 128
                    or isinstance(revision, bool)
                    or not isinstance(revision, int)
                    or not 1 <= revision <= 1_000_000
                    or not isinstance(tests, list)
                    or not 1 <= len(tests) <= 128
                    or any(
                        not isinstance(item, str)
                        or not item
                        or len(item) > 4_096
                        for item in tests
                    )
                    or len(set(tests)) != len(tests)
                ):
                    raise GovernanceError(
                        "repayment evidence fields are invalid", code="evidence"
                    )
                for relative in tests:
                    _safe_relative_path(
                        repository.descriptor,
                        relative,
                        label="debt repayment evidence test",
                    )
                claims.append(
                    _DebtEvidenceClaim(
                        "repayment",
                        debt_id=debt_id,
                        revision=revision,
                        behavior_preserving_tests=tuple(sorted(tests)),
                    )
                )
                continue
            if status == "accepted":
                if keys != {"approved_by", "debt_id", "revision", "status"}:
                    raise GovernanceError(
                        "acceptance evidence has unknown or missing fields",
                        code="evidence",
                    )
                debt_id = document.get("debt_id")
                revision = document.get("revision")
                approval = document.get("approved_by")
                if (
                    not isinstance(debt_id, str)
                    or not debt_id
                    or len(debt_id) > 128
                    or isinstance(revision, bool)
                    or not isinstance(revision, int)
                    or not 1 <= revision <= 1_000_000
                    or not isinstance(approval, dict)
                    or frozenset(approval)
                    != {"actor_id", "actor_kind", "approved_at", "scope"}
                    or not isinstance(approval.get("actor_id"), str)
                    or not approval["actor_id"]
                    or len(approval["actor_id"]) > 256
                    or approval.get("actor_kind") != "human"
                    or approval.get("scope") != "governance"
                    or not isinstance(approval.get("approved_at"), str)
                    or not approval["approved_at"].endswith("Z")
                ):
                    raise GovernanceError(
                        "acceptance evidence fields are invalid", code="evidence"
                    )
                _parse_timestamp(
                    approval["approved_at"], label="debt acceptance approved_at"
                )
                claims.append(
                    _DebtEvidenceClaim(
                        "acceptance", debt_id=debt_id, revision=revision
                    )
                )
                continue
            raise GovernanceError(
                "debt evidence status is unsupported", code="evidence"
            )
        except GovernanceError:
            findings.append(
                GovernanceFinding(
                    "debt-evidence-document-invalid",
                    f"{owner} evidence must match a closed bounded evidence contract",
                    evidence_path,
                )
            )
            continue
    return findings, claims


def _debt_findings(
    debts: tuple[DebtRecord, ...],
    repository: _RepositoryHandle,
    *,
    now: datetime,
) -> list[GovernanceFinding]:
    findings: list[GovernanceFinding] = []
    for record in debts:
        document = record.to_dict()
        debt_id = document.get("debt_id", "unknown")
        path = f"debt[{debt_id}]"
        owner = document.get("owner", {})
        if not isinstance(owner, dict) or not str(owner.get("actor_id", "")).strip():
            findings.append(GovernanceFinding("debt-owner-required", f"debt {debt_id} requires an owner", path))
        for field, code, limit in (("reason", "debt-reason-required", 4_000), ("interest", "debt-interest-required", 2_000), ("repayment_trigger", "debt-trigger-required", 2_000)):
            if not isinstance(document.get(field), str) or not document[field].strip() or len(document[field]) > limit:
                findings.append(GovernanceFinding(code, f"debt {debt_id} requires {field}", path))
        deadline: datetime | None = None
        try:
            raw_deadline = document.get("deadline")
            if not isinstance(raw_deadline, str) or not raw_deadline.endswith("Z"):
                raise GovernanceError("deadline must use UTC Z", code="timestamp")
            deadline = _parse_timestamp(raw_deadline, label=f"debt {debt_id} deadline")
        except GovernanceError:
            findings.append(GovernanceFinding("debt-deadline-invalid", f"debt {debt_id} requires a UTC deadline", path))
        tests = document.get("behavior_preserving_tests", [])
        if not tests:
            findings.append(GovernanceFinding("debt-tests-required", f"debt {debt_id} requires behavior-preserving tests", path))
        for relative in tests:
            try:
                _safe_relative_path(repository.descriptor, relative, label=f"debt {debt_id} test")
                _read_regular_bytes(repository.descriptor, relative, label=f"debt {debt_id} test")
            except GovernanceError:
                findings.append(GovernanceFinding("debt-test-unavailable", f"debt {debt_id} test is unavailable", relative))
        evidence_findings, contents = _evidence_contents(repository, document.get("evidence", []), owner=path, prefix="debt")
        findings.extend(evidence_findings)
        evidence_document_findings, evidence_claims = (
            _parse_debt_evidence_documents(
                contents, repository, owner=path
            )
        )
        findings.extend(evidence_document_findings)
        status = document.get("status")
        if status in {"open", "repaying"} and deadline is not None and deadline <= now:
            findings.append(GovernanceFinding("debt-overdue", f"debt {debt_id} is overdue and remains open", path))
        if status == "repaid":
            normalized_tests = tuple(sorted(tests))
            if not any(
                item.kind == "repayment"
                and item.debt_id == debt_id
                and item.revision == document.get("revision")
                and item.behavior_preserving_tests == normalized_tests
                for item in evidence_claims
            ):
                findings.append(GovernanceFinding("debt-repayment-evidence-required", f"debt {debt_id} requires passing evidence for every behavior test", path))
            findings.append(
                GovernanceFinding(
                    "debt-repayment-authority-required",
                    f"repaid debt {debt_id} requires independently verified exact-record repayment authority",
                    path,
                )
            )
        if status == "accepted":
            approved = any(
                item.kind == "acceptance"
                and item.debt_id == debt_id
                and item.revision == document.get("revision")
                for item in evidence_claims
            )
            if not approved:
                findings.append(GovernanceFinding("debt-acceptance-approval-required", f"accepted debt {debt_id} requires human governance approval evidence", path))
            findings.append(
                GovernanceFinding(
                    "debt-acceptance-authority-required",
                    f"accepted debt {debt_id} requires independently verified exact-record acceptance authority",
                    path,
                )
            )
            if deadline is not None and deadline <= now:
                findings.append(GovernanceFinding("debt-accepted-review-overdue", f"accepted debt {debt_id} requires a future review deadline", path))
    return findings


def _transition_rule(
    rule: RuleRecord,
    target: RuleStatus,
    actor: ActorRef,
    *,
    at: datetime,
    live_evidence: bool,
) -> RuleRecord:
    timestamp = _format_timestamp(at)
    if actor.actor_kind == "agent":
        raise GovernanceError(
            "agent may only create candidate governance rules",
            code="rule-transition-actor",
        )
    if target not in _RULE_TRANSITIONS.get(rule.status, frozenset()):
        raise GovernanceError(
            f"invalid rule transition: {rule.status} -> {target}",
            code="rule-transition",
        )
    if target != "revoked" and not live_evidence:
        raise GovernanceError(
            "rule transition requires repository-validated live evidence",
            code="rule-evidence-unvalidated",
        )

    document = rule.to_dict()
    if target == "reviewed":
        if not _has_evidence_digests(rule):
            raise GovernanceError(
                "reviewed rule requires at least one repository evidence digest",
                code="rule-evidence-required",
            )
        if actor.actor_id == rule.author.actor_id:
            raise GovernanceError(
                "reviewed rule requires an independent reviewer",
                code="rule-review-not-independent",
            )
        document["reviewed_by"].append(
            {
                "actor_id": actor.actor_id,
                "actor_kind": actor.actor_kind,
                "reviewed_at": timestamp,
            }
        )
    elif target == "approved":
        if not _has_independent_review(rule):
            raise GovernanceError(
                "approved rule requires an independent reviewer",
                code="rule-review-not-independent",
            )
        if actor.actor_kind != "human":
            raise GovernanceError(
                "approval requires a human governance approval actor",
                code="rule-approval-required",
            )
        document["approved_by"].append(
            {
                "actor_id": actor.actor_id,
                "actor_kind": "human",
                "approved_at": timestamp,
                "scope": "governance",
            }
        )
    elif target == "active":
        if not _has_independent_review(rule):
            raise GovernanceError(
                "active rule requires an independent reviewer",
                code="rule-review-not-independent",
            )
        if not _has_human_governance_approval(rule):
            raise GovernanceError(
                "active rule requires a human governance approval",
                code="rule-approval-required",
            )

    document["status"] = target
    document["revision"] = rule.revision + 1
    return RuleRecord.from_dict(document)


def _rule_is_unexpired(rule: RuleRecord, now: datetime) -> bool:
    if rule.expires_at is None:
        return True
    return _parse_timestamp(
        rule.expires_at, label=f"rule {rule.rule_id} expires_at"
    ) > now


def _rule_is_lifecycle_qualified(rule: RuleRecord, *, live_evidence: bool) -> bool:
    return (
        rule.status == "active"
        and live_evidence
        and _has_independent_review(rule)
        and _has_human_governance_approval(rule)
    )


def _build_rule_lifecycle_api() -> tuple[Callable[..., Any], ...]:
    @dataclass(frozen=True)
    class Binding:
        repository_path: Path
        repository_identity: tuple[int, int]
        rule_digest: str

    bindings: weakref.WeakKeyDictionary[RuleRecord, Binding]
    bindings = weakref.WeakKeyDictionary()
    example_bindings: weakref.WeakKeyDictionary[ExampleRecord, Binding]
    example_bindings = weakref.WeakKeyDictionary()
    debt_bindings: weakref.WeakKeyDictionary[DebtRecord, Binding]
    debt_bindings = weakref.WeakKeyDictionary()
    snapshot_bindings: dict[
        int,
        tuple[
            weakref.ReferenceType[GovernanceSnapshot],
            Path,
            tuple[int, int],
        ],
    ] = {}

    def bind_snapshot(
        snapshot: GovernanceSnapshot,
        repository_path: Path,
        repository_identity: tuple[int, int],
    ) -> None:
        key = id(snapshot)

        def discard(reference: weakref.ReferenceType[GovernanceSnapshot]) -> None:
            current = snapshot_bindings.get(key)
            if current is not None and current[0] is reference:
                snapshot_bindings.pop(key, None)

        snapshot_bindings[key] = (
            weakref.ref(snapshot, discard),
            repository_path,
            repository_identity,
        )

    def snapshot_repository(snapshot: GovernanceSnapshot) -> Path | None:
        binding = snapshot_bindings.get(id(snapshot))
        if binding is None or binding[0]() is not snapshot:
            return None
        repository_path, repository_identity = binding[1], binding[2]
        try:
            repository = _open_repository(repository_path)
        except GovernanceError:
            return None
        try:
            if repository.identity != repository_identity:
                return None
            _verify_repository(repository)
            return repository_path
        except GovernanceError:
            return None
        finally:
            os.close(repository.descriptor)

    def bind(
        record: RuleRecord,
        repository_path: Path,
        repository_identity: tuple[int, int],
    ) -> None:
        bindings[record] = Binding(
            repository_path=repository_path,
            repository_identity=repository_identity,
            rule_digest=hashlib.sha256(record._canonical_document).hexdigest(),
        )

    def bind_other(
        mapping: weakref.WeakKeyDictionary[Any, Binding],
        record: ExampleRecord | DebtRecord,
        repository_path: Path,
        repository_identity: tuple[int, int],
    ) -> None:
        mapping[record] = Binding(
            repository_path=repository_path,
            repository_identity=repository_identity,
            rule_digest=hashlib.sha256(record._canonical_document).hexdigest(),
        )

    def has_live_evidence(rule: RuleRecord) -> bool:
        binding = bindings.get(rule)
        if (
            binding is None
            or binding.rule_digest
            != hashlib.sha256(rule._canonical_document).hexdigest()
            or not _has_evidence_digests(rule)
        ):
            return False
        try:
            repository = _open_repository(binding.repository_path)
        except GovernanceError:
            return False
        try:
            if repository.identity != binding.repository_identity:
                return False
            for evidence in rule.evidence:
                _safe_relative_path(
                    repository.descriptor,
                    evidence.path,
                    label=f"rule {rule.rule_id} evidence {evidence.evidence_id}",
                )
                content = _read_regular_bytes(
                    repository.descriptor,
                    evidence.path,
                    label=f"rule {rule.rule_id} evidence {evidence.evidence_id}",
                )
                if hashlib.sha256(content).hexdigest() != evidence.sha256:
                    return False
            _verify_repository(repository)
            return True
        except GovernanceError:
            return False
        finally:
            os.close(repository.descriptor)

    def load(root: Path | str) -> GovernanceSnapshot:
        snapshot, repository_path, repository_identity = _load_governance_snapshot(
            root
        )
        for record in snapshot.rule_records:
            bind(record, repository_path, repository_identity)
        for record in snapshot.example_records:
            bind_other(example_bindings, record, repository_path, repository_identity)
        for record in snapshot.debt_records:
            bind_other(debt_bindings, record, repository_path, repository_identity)
        bind_snapshot(snapshot, repository_path, repository_identity)
        return snapshot

    def transition(
        rule: RuleRecord,
        target: RuleStatus,
        actor: ActorRef,
        *,
        at: datetime,
    ) -> RuleRecord:
        binding = bindings.get(rule)
        updated = _transition_rule(
            rule,
            target,
            actor,
            at=at,
            live_evidence=has_live_evidence(rule),
        )
        if (
            binding is not None
            and binding.rule_digest
            == hashlib.sha256(rule._canonical_document).hexdigest()
        ):
            bind(updated, binding.repository_path, binding.repository_identity)
        return updated

    def effective(
        snapshot: GovernanceSnapshot,
        *,
        now: datetime,
    ) -> tuple[RuleRecord, ...]:
        effective_at = _require_aware(now, label="now")
        records = _snapshot_rule_records(snapshot)
        return tuple(
            sorted(
                (
                    rule
                    for rule in records
                    if _rule_is_lifecycle_qualified(
                        rule, live_evidence=has_live_evidence(rule)
                    )
                    and _rule_is_unexpired(rule, effective_at)
                ),
                key=lambda rule: rule.rule_id,
            )
        )

    def effective_example_records(snapshot: GovernanceSnapshot) -> tuple[ExampleRecord, ...]:
        records = _snapshot_example_records(snapshot)
        if not records:
            return ()
        first_binding = example_bindings.get(records[0])
        if first_binding is None:
            return ()
        for record in records:
            binding = example_bindings.get(record)
            if (
                binding is None
                or binding.repository_path != first_binding.repository_path
                or binding.repository_identity != first_binding.repository_identity
                or binding.rule_digest != hashlib.sha256(record._canonical_document).hexdigest()
            ):
                return ()
        try:
            repository = _open_repository(first_binding.repository_path)
        except GovernanceError:
            return ()
        try:
            if repository.identity != first_binding.repository_identity:
                return ()
            findings = _example_findings(records, repository)
            _verify_repository(repository)
            if findings:
                return ()
            return tuple(sorted((record for record in records if record.status == "active"), key=lambda item: item.example_id))
        except GovernanceError:
            return ()
        finally:
            os.close(repository.descriptor)

    def open_debt_records(
        snapshot: GovernanceSnapshot,
        *,
        now: datetime,
    ) -> tuple[DebtRecord, ...]:
        evaluated_at = _require_aware(now, label="now")
        records = _snapshot_debt_records(snapshot)
        if not records:
            return ()
        first_binding = debt_bindings.get(records[0])
        if first_binding is None:
            return ()
        for record in records:
            binding = debt_bindings.get(record)
            if (
                binding is None
                or binding.repository_path != first_binding.repository_path
                or binding.repository_identity != first_binding.repository_identity
                or binding.rule_digest != hashlib.sha256(record._canonical_document).hexdigest()
            ):
                return ()
        try:
            repository = _open_repository(first_binding.repository_path)
        except GovernanceError:
            return ()
        try:
            if repository.identity != first_binding.repository_identity:
                return ()
            findings = _debt_findings(records, repository, now=evaluated_at)
            _verify_repository(repository)
            if any(item.code != "debt-overdue" for item in findings):
                return ()
            return tuple(sorted((record for record in records if record.status in {"open", "repaying"}), key=lambda item: item.debt_id))
        except GovernanceError:
            return ()
        finally:
            os.close(repository.descriptor)

    def validate_deviation(
        snapshot: GovernanceSnapshot,
        *,
        category: str,
        justification: str | None,
        criterion_ids: tuple[str, ...] = (),
        evidence: tuple[str, ...] = (),
    ) -> GovernanceFinding | None:
        applicable = [item for item in effective_example_records(snapshot) if item.category == category]
        if not applicable:
            return None
        valid = bool(isinstance(justification, str) and justification.strip())
        valid = valid and bool(criterion_ids) and all(isinstance(item, str) and item.strip() for item in criterion_ids)
        valid = valid and bool(evidence) and all(isinstance(item, str) and item.strip() for item in evidence)
        binding = example_bindings.get(applicable[0])
        if valid and binding is not None:
            try:
                repository = _open_repository(binding.repository_path)
                try:
                    if repository.identity != binding.repository_identity:
                        valid = False
                    for relative in evidence:
                        _safe_relative_path(repository.descriptor, relative, label="example deviation evidence")
                        _read_regular_bytes(repository.descriptor, relative, label="example deviation evidence")
                    _verify_repository(repository)
                finally:
                    os.close(repository.descriptor)
            except GovernanceError:
                valid = False
        if valid:
            return None
        return GovernanceFinding(
            "canonical-example-deviation",
            "deviation from an active canonical example requires justification, criterion_ids, and repository-contained evidence",
            f"examples[{category}]",
        )

    return (
        load,
        transition,
        effective,
        effective_example_records,
        open_debt_records,
        validate_deviation,
        snapshot_repository,
    )


(
    load_governance,
    transition_rule,
    effective_rules,
    effective_examples,
    open_debt,
    validate_example_deviation,
    _snapshot_repository,
) = _build_rule_lifecycle_api()


def _normalized_statement(statement: str) -> str:
    return " ".join(unicodedata.normalize("NFC", statement).split())


def _normalized_scope(rule: RuleRecord) -> dict[str, tuple[str, ...]]:
    scope = rule.to_dict()["scope"]
    return {
        field: tuple(sorted(scope[field]))
        for field in ("domains", "repository_paths", "route_intents")
    }


def _dimension_overlaps(first: tuple[str, ...], second: tuple[str, ...]) -> bool:
    return not first or not second or bool(set(first).intersection(second))


def _path_overlaps(first: str, second: str) -> bool:
    first_parts = PurePosixPath(first).parts
    second_parts = PurePosixPath(second).parts
    common = min(len(first_parts), len(second_parts))
    return first_parts[:common] == second_parts[:common]


def _scopes_overlap(
    first: dict[str, tuple[str, ...]], second: dict[str, tuple[str, ...]]
) -> bool:
    first_paths = first["repository_paths"]
    second_paths = second["repository_paths"]
    paths_overlap = (
        not first_paths
        or not second_paths
        or any(
            _path_overlaps(first_path, second_path)
            for first_path in first_paths
            for second_path in second_paths
        )
    )
    return (
        paths_overlap
        and _dimension_overlaps(first["domains"], second["domains"])
        and _dimension_overlaps(first["route_intents"], second["route_intents"])
    )


def _rule_pair_findings(
    rules: tuple[RuleRecord, ...], *, now: datetime
) -> list[GovernanceFinding]:
    findings: list[GovernanceFinding] = []
    ordered = sorted(rules, key=lambda rule: rule.rule_id)
    for index, first in enumerate(ordered):
        for second in ordered[index + 1 :]:
            path = f"rules[{first.rule_id},{second.rule_id}]"
            first_document = first.to_dict()
            second_document = second.to_dict()
            first_scope = _normalized_scope(first)
            second_scope = _normalized_scope(second)
            first_statement = _normalized_statement(first_document["statement"])
            second_statement = _normalized_statement(second_document["statement"])
            first_enforcement = first_document["enforcement"]
            second_enforcement = second_document["enforcement"]
            if (
                first_scope == second_scope
                and first_statement == second_statement
                and first_enforcement == second_enforcement
            ):
                findings.append(
                    GovernanceFinding(
                        "rule-duplicate",
                        f"rules {first.rule_id} and {second.rule_id} are duplicates",
                        path,
                    )
                )
                continue
            both_live_active = (
                first.status == "active"
                and second.status == "active"
                and _rule_is_unexpired(first, now)
                and _rule_is_unexpired(second, now)
            )
            if (
                both_live_active
                and _scopes_overlap(first_scope, second_scope)
                and first_enforcement["selector"] == second_enforcement["selector"]
                and (
                    first_statement != second_statement
                    or first_enforcement["kind"] != second_enforcement["kind"]
                )
            ):
                findings.append(
                    GovernanceFinding(
                        "rule-conflict",
                        f"rules {first.rule_id} and {second.rule_id} conflict",
                        path,
                    )
                )
    return findings


def validate_governance(
    snapshot: GovernanceSnapshot,
    root: Path | str,
    *,
    now: datetime,
) -> tuple[GovernanceFinding, ...]:
    validated_at = _require_aware(now, label="now")
    repository = _open_repository(root)
    try:
        _validate_structural_semantics(snapshot, repository.descriptor)
        rules = tuple(
            RuleRecord.from_dict(document) for document in snapshot.rules["rules"]
        )
        findings: list[GovernanceFinding] = []
        for rule in rules:
            path = f"rules[{rule.rule_id}]"
            if rule.status != "candidate":
                if not _has_independent_review(rule):
                    findings.append(
                        GovernanceFinding(
                            "rule-review-not-independent",
                            f"rule {rule.rule_id} requires an independent reviewer",
                            path,
                        )
                    )
                if rule.status in {"approved", "active", "deprecated", "revoked"} and not _has_human_governance_approval(rule):
                    findings.append(
                        GovernanceFinding(
                            "rule-approval-required",
                            f"rule {rule.rule_id} requires human governance approval",
                            path,
                        )
                    )
                for evidence in rule.evidence:
                    try:
                        content = _read_regular_bytes(
                            repository.descriptor,
                            evidence.path,
                            label=f"rule {rule.rule_id} evidence {evidence.evidence_id}",
                        )
                    except GovernanceError:
                        findings.append(
                            GovernanceFinding(
                                "rule-evidence-unavailable",
                                f"rule {rule.rule_id} evidence is unavailable",
                                evidence.path,
                            )
                        )
                        continue
                    if hashlib.sha256(content).hexdigest() != evidence.sha256:
                        findings.append(
                            GovernanceFinding(
                                "rule-evidence-digest-mismatch",
                                f"rule {rule.rule_id} evidence digest does not match",
                                evidence.path,
                            )
                        )
            if rule.status == "active" and not _rule_is_unexpired(rule, validated_at):
                findings.append(
                    GovernanceFinding(
                        "rule-expired",
                        f"rule {rule.rule_id} is expired",
                        path,
                    )
                )
        findings.extend(_rule_pair_findings(rules, now=validated_at))
        examples = tuple(
            ExampleRecord.from_dict(document)
            for document in snapshot.examples["examples"]
        )
        debts = tuple(
            DebtRecord.from_dict(document) for document in snapshot.debt["entries"]
        )
        findings.extend(_example_findings(examples, repository))
        findings.extend(_debt_findings(debts, repository, now=validated_at))
        _verify_repository(repository)
        return tuple(
            sorted(
                findings,
                key=lambda finding: (
                    finding.code,
                    finding.path,
                    finding.message,
                    finding.severity,
                ),
            )
        )
    finally:
        os.close(repository.descriptor)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def governance_digests(snapshot: GovernanceSnapshot) -> dict[str, str]:
    rules_schema_digest = _sha256(snapshot.rules_schema)
    debt_schema_digest = _sha256(snapshot.debt_schema)
    examples_schema_digest = _sha256(snapshot.examples_schema)
    handoff_schema_digest = _sha256(snapshot.handoff_schema)
    schema_digest = _sha256(
        {
            "rules_schema_digest": rules_schema_digest,
            "debt_schema_digest": debt_schema_digest,
            "examples_schema_digest": examples_schema_digest,
            "handoff_schema_digest": handoff_schema_digest,
        }
    )
    rules_digest = _sha256(
        _normalize_root(
            snapshot.rules,
            collection="rules",
            normalize_record=_normalize_rule,
            stable_fields=("rule_id", "revision"),
        )
    )
    debt_digest = _sha256(
        _normalize_root(
            snapshot.debt,
            collection="entries",
            normalize_record=_normalize_debt,
            stable_fields=("debt_id", "revision"),
        )
    )
    examples_digest = _sha256(
        _normalize_root(
            snapshot.examples,
            collection="examples",
            normalize_record=_normalize_example,
            stable_fields=("example_id", "version"),
        )
    )
    governance_digest = _sha256(
        {
            "contract": "adaptive-grok.governance",
            "contract_version": 1,
            "schema_digest": schema_digest,
            "rules_digest": rules_digest,
            "debt_digest": debt_digest,
            "examples_digest": examples_digest,
        }
    )
    return {
        "rules_schema_digest": rules_schema_digest,
        "debt_schema_digest": debt_schema_digest,
        "examples_schema_digest": examples_schema_digest,
        "handoff_schema_digest": handoff_schema_digest,
        "schema_digest": schema_digest,
        "rules_digest": rules_digest,
        "debt_digest": debt_digest,
        "examples_digest": examples_digest,
        "governance_digest": governance_digest,
    }


def _architecture_evidence_digest(value: dict[str, Any]) -> str:
    try:
        raw = (
            json.dumps(
                value,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise GovernanceError(
            "architecture evidence is not canonical JSON", code="architecture"
        ) from exc
    return hashlib.sha256(raw).hexdigest()


def load_architecture_evidence(path: Path | str) -> dict[str, Any]:
    evidence_path = Path(os.path.abspath(Path(path)))
    if not evidence_path.name or evidence_path.name in {".", ".."}:
        raise GovernanceError("architecture evidence path is invalid", code="path")
    repository = _open_repository(evidence_path.parent)
    try:
        data = _read_regular_bytes(
            repository.descriptor,
            evidence_path.name,
            label="architecture evidence",
        )
        document = load_bytes(data, label="architecture evidence")
        _verify_repository(repository)
        return document
    finally:
        os.close(repository.descriptor)


def _validate_architecture_evidence(
    architecture: dict[str, Any],
    *,
    base_sha: str,
    head_sha: str,
) -> str:
    if not isinstance(architecture, dict):
        raise GovernanceError("architecture evidence must be an object", code="architecture")
    fields = frozenset(architecture)
    if fields != _ARCHITECTURE_EVIDENCE_FIELDS:
        unknown = sorted(fields - _ARCHITECTURE_EVIDENCE_FIELDS)
        missing = sorted(_ARCHITECTURE_EVIDENCE_FIELDS - fields)
        details = []
        if missing:
            details.append(f"missing fields: {', '.join(missing)}")
        if unknown:
            details.append(f"unknown fields: {', '.join(unknown)}")
        raise GovernanceError(
            f"architecture evidence shape mismatch ({'; '.join(details)})",
            code="architecture",
        )
    if architecture["architecture_contract_version"] != 1:
        raise GovernanceError(
            "architecture evidence contract version is unsupported",
            code="architecture",
        )
    if architecture["head_kind"] != "commit":
        raise GovernanceError(
            "architecture worktree evidence cannot produce a governance handoff",
            code="architecture",
        )
    if architecture["exact_base_sha"] != base_sha:
        raise GovernanceError(
            "architecture evidence base SHA mismatch", code="architecture"
        )
    if architecture["exact_head_sha"] != head_sha:
        raise GovernanceError(
            "architecture evidence head SHA mismatch", code="architecture"
        )
    for label, value in (("base", base_sha), ("head", head_sha)):
        if not isinstance(value, str) or _SHA40_PATTERN.fullmatch(value) is None:
            raise GovernanceError(f"exact {label} SHA is invalid", code="sha")
    digest_fields = (
        "architecture_digest",
        "contract_inventory_digest",
        "diff_digest",
        "repository_inventory_digest",
        "rules_digest",
        "schema_digest",
        "system_digest",
    )
    for field in digest_fields:
        value = architecture[field]
        if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
            raise GovernanceError(
                f"architecture evidence {field} is invalid", code="architecture"
            )
    for field in ("base_adoption_digest", "head_adoption_digest"):
        value = architecture[field]
        if value is not None and (
            not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None
        ):
            raise GovernanceError(
                f"architecture evidence {field} is invalid", code="architecture"
            )
    claimed_evidence_digest = architecture["architecture_evidence_digest"]
    if (
        not isinstance(claimed_evidence_digest, str)
        or _SHA256_PATTERN.fullmatch(claimed_evidence_digest) is None
    ):
        raise GovernanceError(
            "architecture evidence digest is invalid", code="architecture"
        )
    evidence_core = dict(architecture)
    evidence_core.pop("architecture_evidence_digest")
    if _architecture_evidence_digest(evidence_core) != claimed_evidence_digest:
        raise GovernanceError(
            "architecture evidence digest mismatch", code="architecture"
        )
    expected_architecture_digest = _sha256(
        {
            "contract": "adaptive-grok.architecture",
            "contract_version": 1,
            "schema_digest": architecture["schema_digest"],
            "system_digest": architecture["system_digest"],
            "rules_digest": architecture["rules_digest"],
        }
    )
    if architecture["architecture_digest"] != expected_architecture_digest:
        raise GovernanceError(
            "architecture digest mismatch", code="architecture"
        )
    if (
        architecture["fitness_status"] != "pass"
        or architecture["overall_status"] != "pass"
    ):
        raise GovernanceError(
            "architecture evidence status is not pass", code="architecture"
        )
    return str(architecture["architecture_digest"])


def _git_output(root: Path, arguments: list[str], *, label: str) -> bytes:
    environment = dict(os.environ)
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    environment["LC_ALL"] = "C"
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            capture_output=True,
            timeout=30,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GovernanceError(f"{label} failed", code="git") from exc
    if result.returncode != 0:
        raise GovernanceError(f"{label} failed", code="git")
    if len(result.stdout) > MAX_DOCUMENT_BYTES:
        raise GovernanceError(f"{label} output limit exceeded", code="limit")
    return result.stdout


def _require_clean_exact_git_state(
    root: Path,
    *,
    base_sha: str,
    head_sha: str,
) -> None:
    for label, value in (("base", base_sha), ("head", head_sha)):
        if _SHA40_PATTERN.fullmatch(value) is None:
            raise GovernanceError(f"exact {label} SHA is invalid", code="sha")
    current_head = _git_output(
        root,
        ["rev-parse", "--verify", "HEAD^{commit}"],
        label="resolve exact Git head",
    ).decode("ascii", "strict").strip()
    if current_head != head_sha:
        raise GovernanceError("exact head SHA mismatch", code="sha")
    _git_output(
        root,
        ["cat-file", "-e", f"{base_sha}^{{commit}}"],
        label="resolve exact Git base",
    )
    dirty = _git_output(
        root,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
        label="inspect Git worktree",
    )
    if dirty:
        raise GovernanceError(
            "dirty worktree cannot produce exact governance evidence", code="dirty"
        )


def _finding_payload(findings: tuple[GovernanceFinding, ...]) -> list[dict[str, str]]:
    return [dataclasses.asdict(finding) for finding in findings]


def _governance_evaluation(
    snapshot: GovernanceSnapshot,
    *,
    now: datetime,
) -> tuple[GovernanceSnapshot, Path, dict[str, Any]]:
    evaluated_at = _require_aware(now, label="now")
    root = _snapshot_repository(snapshot)
    if root is None:
        raise GovernanceError(
            "governance snapshot lacks loader provenance", code="provenance"
        )
    current = load_governance(root)
    supplied_digests = governance_digests(snapshot)
    current_digests = governance_digests(current)
    if supplied_digests != current_digests:
        raise GovernanceError(
            "governance snapshot digest mismatch", code="digest"
        )
    findings = validate_governance(current, root, now=evaluated_at)
    active_rules = tuple(rule.rule_id for rule in effective_rules(current, now=evaluated_at))
    active_examples = tuple(
        {
            "example_id": record.example_id,
            "version": record.to_dict()["version"],
        }
        for record in effective_examples(current)
    )
    open_debt_ids = tuple(
        sorted(
            entry["debt_id"]
            for entry in current.debt["entries"]
            if entry["status"] in {"open", "repaying"}
        )
    )
    overdue_debt_ids = tuple(
        sorted(
            entry["debt_id"]
            for entry in current.debt["entries"]
            if entry["status"] in {"open", "repaying"}
            and _parse_timestamp(
                entry["deadline"], label=f"debt {entry['debt_id']} deadline"
            )
            <= evaluated_at
        )
    )
    status = "fail" if findings else "pass"
    return current, root, {
        "active_example_ids_versions": list(active_examples),
        "active_rule_ids": list(active_rules),
        "digests": current_digests,
        "findings": _finding_payload(findings),
        "open_debt_ids": list(open_debt_ids),
        "overall_status": status,
        "overdue_debt_ids": list(overdue_debt_ids),
    }


def governance_summary(
    snapshot: GovernanceSnapshot,
    *,
    now: datetime,
) -> dict[str, Any]:
    current, _, evaluation = _governance_evaluation(snapshot, now=now)
    return {
        "active_example_ids_versions": evaluation["active_example_ids_versions"],
        "active_rule_ids": evaluation["active_rule_ids"],
        "candidate_rule_ids": sorted(
            rule["rule_id"]
            for rule in current.rules["rules"]
            if rule["status"] == "candidate"
        ),
        "debt_count": len(current.debt["entries"]),
        **evaluation["digests"],
        "example_count": len(current.examples["examples"]),
        "findings": evaluation["findings"],
        "governance_id": current.rules["governance_id"],
        "ok": evaluation["overall_status"] == "pass",
        "open_debt_ids": evaluation["open_debt_ids"],
        "overall_status": evaluation["overall_status"],
        "overdue_debt_ids": evaluation["overdue_debt_ids"],
        "rule_count": len(current.rules["rules"]),
    }


def build_governance_handoff(
    snapshot: GovernanceSnapshot,
    *,
    architecture: dict[str, Any],
    base_sha: str,
    head_sha: str,
    now: datetime | None = None,
) -> GovernanceHandoffV1:
    evaluated_at = now or datetime.now(timezone.utc)
    _validate_architecture_evidence(
        architecture,
        base_sha=base_sha,
        head_sha=head_sha,
    )
    _, root, evaluation = _governance_evaluation(snapshot, now=evaluated_at)
    _require_clean_exact_git_state(root, base_sha=base_sha, head_sha=head_sha)
    try:
        derived_architecture = derive_architecture_evidence(
            root,
            base_sha=base_sha,
            head_sha=head_sha,
            pre_risk="red",
        )
    except (ArchitectureError, OSError, ValueError) as exc:
        raise GovernanceError(
            "M2 architecture evidence cannot be independently derived",
            code="architecture",
        ) from exc
    architecture_digest = _validate_architecture_evidence(
        derived_architecture,
        base_sha=base_sha,
        head_sha=head_sha,
    )
    if _canonical_bytes(architecture) != _canonical_bytes(derived_architecture):
        raise GovernanceError(
            "architecture evidence does not match independently derived M2 architecture evidence",
            code="architecture",
        )
    evidence_core = {
        "contract": "adaptive-grok.governance-evidence/v1",
        "rules_digest": evaluation["digests"]["rules_digest"],
        "debt_digest": evaluation["digests"]["debt_digest"],
        "examples_digest": evaluation["digests"]["examples_digest"],
        "schema_digest": evaluation["digests"]["schema_digest"],
        "active_rule_ids": evaluation["active_rule_ids"],
        "active_example_ids_versions": evaluation[
            "active_example_ids_versions"
        ],
        "open_debt_ids": evaluation["open_debt_ids"],
        "overdue_debt_ids": evaluation["overdue_debt_ids"],
        "findings": evaluation["findings"],
        "architecture_digest": architecture_digest,
        "exact_base_sha": base_sha,
        "exact_head_sha": head_sha,
        "overall_status": evaluation["overall_status"],
    }
    governance_evidence_digest = _sha256(evidence_core)
    if evaluation["findings"]:
        codes = ", ".join(item["code"] for item in evaluation["findings"])
        raise GovernanceError(
            f"governance findings block handoff: {codes}", code="findings"
        )
    _require_clean_exact_git_state(root, base_sha=base_sha, head_sha=head_sha)
    handoff = GovernanceHandoffV1(
        governance_contract_version=1,
        governance_digest=evaluation["digests"]["governance_digest"],
        governance_evidence_digest=governance_evidence_digest,
        architecture_digest=architecture_digest,
        exact_base_sha=base_sha,
        exact_head_sha=head_sha,
    )
    _validate_schema_checked(
        handoff.to_dict(), snapshot.handoff_schema, label="governance handoff"
    )
    return handoff


def _projection_banner(name: str) -> tuple[str, str]:
    return _PROJECTION_BEGIN.format(name=name), _PROJECTION_END.format(name=name)


def _projection_list(values: list[str], *, empty: str) -> list[str]:
    return [f"- `{value}`" for value in values] if values else [f"_{empty}_"]


def render_markdown_projections(
    snapshot: GovernanceSnapshot,
    *,
    now: datetime,
) -> dict[str, str]:
    evaluated_at = _require_aware(now, label="now")
    active_rules = sorted(
        rule["rule_id"]
        for rule in snapshot.rules["rules"]
        if rule["status"] == "active"
    )
    candidate_rules = sorted(
        rule["rule_id"]
        for rule in snapshot.rules["rules"]
        if rule["status"] == "candidate"
    )
    open_debt_ids = sorted(
        entry["debt_id"]
        for entry in snapshot.debt["entries"]
        if entry["status"] in {"open", "repaying"}
    )
    overdue_debt_ids = sorted(
        entry["debt_id"]
        for entry in snapshot.debt["entries"]
        if entry["status"] in {"open", "repaying"}
        and _parse_timestamp(
            entry["deadline"], label=f"debt {entry['debt_id']} deadline"
        )
        <= evaluated_at
    )
    notice = (
        "> **NON-AUTHORITATIVE PROJECTION.** Canonical JSON governance records "
        "remain authority; this Markdown cannot approve, activate, repay, or accept "
        "any record."
    )
    decisions_begin, decisions_end = _projection_banner("decisions.md")
    mistakes_begin, mistakes_end = _projection_banner("mistakes.md")
    decisions = [
        decisions_begin,
        notice,
        "",
        "## Active governance rules",
        "",
        *_projection_list(active_rules, empty="No active governance rules."),
        "",
        "## Candidate governance rules",
        "",
        *_projection_list(candidate_rules, empty="No candidate governance rules."),
        decisions_end,
        "",
    ]
    mistakes = [
        mistakes_begin,
        notice,
        "",
        "## Open governance debt",
        "",
        *_projection_list(open_debt_ids, empty="No open governance debt."),
        "",
        "## Overdue governance debt",
        "",
        *_projection_list(overdue_debt_ids, empty="No overdue governance debt."),
        mistakes_end,
        "",
    ]
    return {
        "decisions.md": "\n".join(decisions),
        "mistakes.md": "\n".join(mistakes),
    }
