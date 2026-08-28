from __future__ import annotations

import errno
import hashlib
import json
import math
import os
import stat
import unicodedata
import weakref
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Literal

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
        snapshot = GovernanceSnapshot(
            rules=normalized_rules,
            debt=_normalize_root(
                registry_documents[DEBT_PATH],
                collection="entries",
                normalize_record=_normalize_debt,
                stable_fields=("debt_id", "revision"),
            ),
            examples=_normalize_root(
                registry_documents[EXAMPLES_PATH],
                collection="examples",
                normalize_record=_normalize_example,
                stable_fields=("example_id", "version"),
            ),
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


def _build_rule_lifecycle_api() -> tuple[
    Callable[[Path | str], GovernanceSnapshot],
    Callable[..., RuleRecord],
    Callable[..., tuple[RuleRecord, ...]],
]:
    @dataclass(frozen=True)
    class Binding:
        repository_path: Path
        repository_identity: tuple[int, int]
        rule_digest: str

    bindings: weakref.WeakKeyDictionary[RuleRecord, Binding]
    bindings = weakref.WeakKeyDictionary()

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

    return load, transition, effective


load_governance, transition_rule, effective_rules = _build_rule_lifecycle_api()


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
