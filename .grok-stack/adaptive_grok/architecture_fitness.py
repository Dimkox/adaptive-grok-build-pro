from __future__ import annotations

import ast
from collections import deque
import hashlib
import json
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, NamedTuple

from .architecture import (
    ArchitectureError,
    ArchitectureSnapshot,
    architecture_digests,
    compare_contracts,
    contract_inventory_digest,
    load_architecture,
)
from .architecture_diff import (
    ADOPTION_BASE_SHA,
    ArchitectureChange,
    ArchitectureDiff,
    ChangedArtifact,
    diff_architecture,
    git_tree_paths,
    read_diff_file,
    read_diff_files,
)
from .queue_provenance import QueueAnalysisLimit, analyze_queue_tree

FITNESS_CATEGORIES = (
    "background_job",
    "change_separation",
    "code_budget",
    "contract_compatibility",
    "forbidden_edge",
    "governance_promotion",
    "migration_safety",
    "module_boundary",
    "network_client",
    "production_import",
    "secret_flow",
    "tenant_authorization",
    "workspace_trust",
)
RISK_ORDER = {"green": 0, "yellow": 1, "red": 2}
MAX_ANALYZED_PYTHON_FILES = 2_000
MAX_ANALYZED_AST_NODES = 200_000
MAX_QUEUE_ADAPTER_MODULES = 32
MAX_QUEUE_ADAPTER_DEPTH = 8
MAX_QUEUE_SOURCE_ROOTS = 64
MAX_QUEUE_DEPENDENCY_WORK = 4_096
MAX_MIGRATION_WORK = 4_096
MAX_MIGRATION_FINDINGS = 256
MAX_MIGRATION_BATCH_PATHS = 8
MAX_MIGRATION_BYTES = 8 * 1024 * 1024
MAX_MIGRATION_STATEMENTS = 4_096
_PYTHON_SUFFIXES = {".py", ".pyi"}
_NETWORK_IMPORTS = {
    "aiohttp": "https",
    "docker": "docker_api",
    "ftplib": "ftp",
    "httpx": "https",
    "imaplib": "imap",
    "poplib": "pop3",
    "psycopg": "postgresql",
    "psycopg2": "postgresql",
    "requests": "https",
    "smtplib": "smtp",
    "socket": "tcp",
    "urllib": "https",
    "urllib.request": "https",
    "xmlrpc.client": "https",
}
_NETWORK_APPLICABILITY_TOKENS = {
    "connect",
    "connection",
    "ftp",
    "grpc",
    "http",
    "https",
    "imap",
    "network",
    "paramiko",
    "pop",
    "request",
    "smtp",
    "socket",
    "ssh",
    "tls",
    "urlopen",
    "websocket",
    "websockets",
}
_CLOUD_SDK_NETWORK_FACTORIES = {
    "boto3": {"client", "resource", "session"},
    "botocore": {"client", "create_client", "get_session", "session"},
}
_QUEUE_IMPORTS = {"celery", "confluent_kafka", "kafka", "kombu", "pika", "queue", "redis", "rq"}
_QUEUE_ADAPTER_MODULE_TOKENS = {
    *_QUEUE_IMPORTS,
    "background",
    "job",
    "jobs",
    "task",
    "tasks",
    "worker",
    "workers",
}
_FRAMEWORK_IMPORTS = {"django", "fastapi", "flask", "litestar", "starlette"}
_GOVERNANCE_IMPORTS = {"adaptive_grok", "architecture", "engineering", "scripts", "tests"}
_GOVERNANCE_PATHS = (".grok", ".grok-stack", "architecture", "docs", "engineering", "scripts", "tests")
_GOVERNANCE_FITNESS_PATHS = (
    ".grok-stack/adaptive_grok/governance.py",
    "schemas/canonical-example.schema.json",
    "schemas/debt-entry.schema.json",
    "schemas/governance-rule.schema.json",
    "scripts/grok_governance.py",
)
_GOVERNANCE_REGISTRIES = (
    ("governance/canonical-examples/index.json", "examples"),
    ("governance/debt/index.json", "entries"),
    ("governance/rules/index.json", "rules"),
)
_GOVERNANCE_SCHEMA_PATHS = (
    "schemas/canonical-example.schema.json",
    "schemas/debt-entry.schema.json",
    "schemas/governance-rule.schema.json",
)
_GOVERNANCE_SCHEMA_DIGESTS = {
    "schemas/canonical-example.schema.json": "1b32818fae37b2f6fbab1855d90e7edefb90f28c6491b661b47afcf4d438a846",
    "schemas/debt-entry.schema.json": "6eec2d5a9d1f465be38796c08cb5639c27452aa717d0e3eada5706904d533f42",
    "schemas/governance-rule.schema.json": "4c5f7c11d37aa330c3596ab423762c71c7eb259e7cfea3aba3f506cc4525382f",
}
_GOVERNANCE_HANDOFF_SCHEMA = "schemas/governance-handoff-v1.schema.json"
_GOVERNANCE_HANDOFF_SCHEMA_DIGEST = (
    "3527385869bc73f628e1dc0e22025d3e54b7e3972aba3703f9b579146a8c80ba"
)
_GOVERNANCE_PROJECTIONS = {"decisions.md", "mistakes.md"}
_GOVERNANCE_VERSION = 1
_MAX_GOVERNANCE_NODES = 100_000
_MAX_GOVERNANCE_DEPTH = 64
_MIGRATION_CANONICAL = re.compile(r"^(?P<group>00(?:1_schema|2_operational_indexes|3_database_roles))$")
_MIGRATION_PHASE = re.compile(r"^(?P<group>.+?)[_-](?P<phase>expand|migrate|contract)(?:[_-].*)?$")


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("ascii")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _matches(path: str, prefixes: Iterable[str]) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes)


@dataclass(frozen=True)
class ApplicabilityEvidence:
    predicate: str
    scanned_scope: tuple[str, ...]
    reason_code: str
    inventory_digest: str


@dataclass(frozen=True)
class FitnessResult:
    category: str
    status: str
    rule_ids: tuple[str, ...]
    findings: tuple[str, ...]
    applicability: ApplicabilityEvidence


@dataclass(frozen=True)
class FitnessReport:
    results: tuple[FitnessResult, ...]
    status: str
    pre_risk: str
    escalation: str
    post_risk: str
    triggers: tuple[str, ...]
    exemption_state: str
    required_scopes: tuple[str, ...]
    evidence_digest: str


class _QueueProvenanceResult(NamedTuple):
    state: str
    reason: str
    signals: tuple[str, ...]
    paths: tuple[str, ...] = ()


class _QueueAdapterResolution(NamedTuple):
    state: str
    reason: str
    exports: tuple[str, ...] = ()
    signals: tuple[str, ...] = ()
    declared_exports: tuple[str, ...] = ()
    sources: tuple[tuple[str, bytes, str], ...] = ()


class _QueueResolutionCache(NamedTuple):
    modules: tuple[str, ...]
    paths: tuple[str, ...]
    values: dict[str, _QueueAdapterResolution]


class _QueueAdapterNamesResult(NamedTuple):
    names: frozenset[str]
    unsupported: bool


class _OperationDependencies(NamedTuple):
    names: frozenset[str]
    frontier: frozenset[str] = frozenset()
    frontier_imports: frozenset[str] = frozenset()
    exhausted: bool = False


def _applicability(predicate: str, scope: Iterable[str], reason_code: str) -> ApplicabilityEvidence:
    scanned = tuple(sorted(set(scope)))
    return ApplicabilityEvidence(
        predicate=predicate,
        scanned_scope=scanned,
        reason_code=reason_code,
        inventory_digest=_digest({"predicate": predicate, "scope": scanned}),
    )


def _result(
    category: str,
    *,
    status: str,
    rules: Iterable[str] = (),
    findings: Iterable[str] = (),
    predicate: str,
    scope: Iterable[str] = (),
    reason: str = "applicable",
) -> FitnessResult:
    if category not in FITNESS_CATEGORIES or status not in {
        "pass",
        "fail",
        "not_applicable",
        "unsupported",
    }:
        raise ArchitectureError("invalid fitness result", code="fitness")
    return FitnessResult(
        category=category,
        status=status,
        rule_ids=tuple(sorted(set(rules))),
        findings=tuple(sorted(set(findings))),
        applicability=_applicability(predicate, scope, reason),
    )


def _not_applicable(
    category: str, predicate: str, scope: Iterable[str], reason: str, rules: Iterable[str] = ()
) -> FitnessResult:
    return _result(
        category,
        status="not_applicable",
        rules=rules,
        predicate=predicate,
        scope=scope,
        reason=reason,
    )


def _model_changed(diff: ArchitectureDiff) -> bool:
    return diff.baseline_introduced or bool(diff.changes)


def _governance_path(path: str) -> bool:
    return _matches(path, ("governance",)) or path in _GOVERNANCE_FITNESS_PATHS


def _parse_governance_json(value: bytes | None, *, path: str) -> dict[str, Any]:
    if value is None:
        raise ArchitectureError(f"required governance document is missing: {path}", code="missing")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in items:
            if key in result:
                raise ArchitectureError(
                    f"duplicate JSON key in governance document {path}: {key}",
                    code="schema",
                )
            result[key] = item
        return result

    def invalid_constant(constant: str) -> None:
        raise ArchitectureError(
            f"non-finite number in governance document {path}: {constant}",
            code="schema",
        )

    try:
        text = value.decode("utf-8")
        if text.startswith("\ufeff"):
            raise ArchitectureError(
                f"UTF-8 BOM is forbidden in governance document {path}", code="schema"
            )
        document = json.loads(
            text,
            object_pairs_hook=pairs,
            parse_constant=invalid_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArchitectureError(
            f"invalid governance JSON document {path}: {exc}", code="schema"
        ) from exc
    if not isinstance(document, dict):
        raise ArchitectureError(f"governance document must be an object: {path}", code="schema")

    nodes = 0
    stack: list[tuple[Any, int]] = [(document, 1)]
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > _MAX_GOVERNANCE_NODES or depth > _MAX_GOVERNANCE_DEPTH:
            raise ArchitectureError(f"governance document exceeds limits: {path}", code="limit")
        if isinstance(item, dict):
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
    return document


def _governance_registry(
    document: dict[str, Any], *, path: str, collection: str
) -> tuple[int, dict[str, dict[str, Any]]]:
    if set(document) != {"schema_version", "governance_id", collection}:
        raise ArchitectureError(f"unsupported governance registry shape: {path}", code="schema")
    version = document["schema_version"]
    if not isinstance(version, int) or isinstance(version, bool):
        raise ArchitectureError(f"unsupported governance schema version: {path}", code="version")
    if document["governance_id"] != "GOV-ADAPTIVE-GROK-M3":
        raise ArchitectureError(f"unsupported governance identity: {path}", code="version")
    records = document[collection]
    if not isinstance(records, list):
        raise ArchitectureError(f"unsupported governance registry collection: {path}", code="schema")
    identity_key = {
        "rules": "rule_id",
        "entries": "debt_id",
        "examples": "example_id",
    }[collection]
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get(identity_key), str):
            raise ArchitectureError(f"unsupported governance record shape: {path}", code="schema")
        identity = record[identity_key]
        if identity in indexed:
            raise ArchitectureError(f"duplicate governance record identity: {identity}", code="schema")
        indexed[identity] = record
    return version, indexed


def _schema_version(document: dict[str, Any], *, path: str) -> int:
    try:
        value = document["properties"]["schema_version"]["const"]
    except (KeyError, TypeError) as exc:
        raise ArchitectureError(f"unsupported governance schema contract: {path}", code="schema") from exc
    if not isinstance(value, int) or isinstance(value, bool):
        raise ArchitectureError(f"unsupported governance schema contract: {path}", code="schema")
    return value


def _handoff_shape_matches(document: dict[str, Any]) -> bool:
    return _digest(document) == _GOVERNANCE_HANDOFF_SCHEMA_DIGEST


def _activation_findings(
    before: dict[str, dict[str, Any]], head: dict[str, dict[str, Any]]
) -> tuple[str, ...]:
    findings: list[str] = []
    for rule_id, prior in before.items():
        current = head.get(rule_id)
        if prior.get("status") == "active" and current is None:
            findings.append(f"{rule_id}: active rule deletion requires an explicit revocation")

    for rule_id, rule in head.items():
        prior = before.get(rule_id)
        promoted = rule.get("status") == "active" and (
            prior is None or prior.get("status") != "active" or prior != rule
        )
        if not promoted:
            continue
        author = rule.get("author")
        author_id = author.get("actor_id") if isinstance(author, dict) else None
        reviewers = rule.get("reviewed_by")
        independent_review = isinstance(reviewers, list) and any(
            isinstance(reviewer, dict)
            and reviewer.get("actor_kind") in {"human", "system"}
            and reviewer.get("actor_id") != author_id
            for reviewer in reviewers
        )
        approvals = rule.get("approved_by")
        independent_approval = isinstance(approvals, list) and any(
            isinstance(approval, dict)
            and approval.get("actor_kind") == "human"
            and approval.get("scope") == "governance"
            and approval.get("actor_id") != author_id
            for approval in approvals
        )
        evidence = rule.get("evidence")
        evidence_paths = {
            item.get("path")
            for item in evidence
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        } if isinstance(evidence, list) else set()
        if not independent_review or not independent_approval or not evidence_paths:
            findings.append(
                f"{rule_id}: activation requires independent review, human governance approval, and evidence"
            )
        if evidence_paths and evidence_paths <= _GOVERNANCE_PROJECTIONS:
            findings.append(f"{rule_id}: projection-only evidence cannot supply governance authority")
        findings.append(f"{rule_id}: external exact-record governance authority is required")
    return tuple(sorted(findings))


def _governance_record_deletion_findings(
    base_debt: dict[str, dict[str, Any]],
    head_debt: dict[str, dict[str, Any]],
    base_examples: dict[str, dict[str, Any]],
    head_examples: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    findings: list[str] = []
    for debt_id, prior in base_debt.items():
        if debt_id in head_debt:
            continue
        if prior.get("status") in {"open", "repaying"}:
            findings.append(
                f"{debt_id}: live debt deletion requires an explicit terminal record"
            )
        else:
            findings.append(
                f"{debt_id}: terminal debt history must remain explicitly represented"
            )
    for example_id, prior in base_examples.items():
        if prior.get("status") == "active" and example_id not in head_examples:
            findings.append(
                f"{example_id}: active example deletion requires an explicit deprecated or revoked record"
            )
    return tuple(sorted(findings))


def _governance_promotion(root: Path, diff: ArchitectureDiff) -> FitnessResult:
    predicate = (
        "governance/**, the three governance registry schemas, governance.py, or "
        "grok_governance.py changed"
    )
    governed_scope = (*_GOVERNANCE_FITNESS_PATHS, "governance/**")
    applicable = tuple(path for path in diff.changed_paths if _governance_path(path))
    if not applicable:
        return _not_applicable(
            "governance_promotion",
            predicate,
            governed_scope,
            "governance_paths_unchanged",
            ("FIT-GOVERNANCE-PROMOTION",),
        )

    required_paths = tuple(
        sorted(
            {
                *(path for path, _collection in _GOVERNANCE_REGISTRIES),
                *_GOVERNANCE_SCHEMA_PATHS,
                _GOVERNANCE_HANDOFF_SCHEMA,
            }
        )
    )
    try:
        base_values = read_diff_files(root, diff, required_paths, side="base")
        head_values = read_diff_files(root, diff, required_paths, side="head")
        base_rules: dict[str, dict[str, Any]] = {}
        head_rules: dict[str, dict[str, Any]] = {}
        base_debt: dict[str, dict[str, Any]] = {}
        head_debt: dict[str, dict[str, Any]] = {}
        base_examples: dict[str, dict[str, Any]] = {}
        head_examples: dict[str, dict[str, Any]] = {}
        findings: list[str] = []
        for path, collection in _GOVERNANCE_REGISTRIES:
            head_version, head_records = _governance_registry(
                _parse_governance_json(head_values[path], path=path),
                path=path,
                collection=collection,
            )
            if base_values[path] is None:
                base_version, base_records = head_version, {}
            else:
                base_version, base_records = _governance_registry(
                    _parse_governance_json(base_values[path], path=path),
                    path=path,
                    collection=collection,
                )
            if head_version < base_version:
                findings.append(
                    f"{path}: governance schema downgrade {base_version} -> {head_version}"
                )
            elif base_version != _GOVERNANCE_VERSION or head_version != _GOVERNANCE_VERSION:
                raise ArchitectureError(
                    f"unknown governance schema version in {path}", code="version"
                )
            if collection == "rules":
                base_rules = base_records
                head_rules = head_records
            elif collection == "entries":
                base_debt = base_records
                head_debt = head_records
            elif collection == "examples":
                base_examples = base_records
                head_examples = head_records

        for path in _GOVERNANCE_SCHEMA_PATHS:
            head_schema = _parse_governance_json(head_values[path], path=path)
            base_schema = (
                head_schema
                if base_values[path] is None
                else _parse_governance_json(base_values[path], path=path)
            )
            head_version = _schema_version(head_schema, path=path)
            base_version = _schema_version(base_schema, path=path)
            if head_version < base_version:
                findings.append(
                    f"{path}: governance schema downgrade {base_version} -> {head_version}"
                )
            elif base_version != _GOVERNANCE_VERSION or head_version != _GOVERNANCE_VERSION:
                raise ArchitectureError(
                    f"unknown governance schema version in {path}", code="version"
                )
            expected_digest = _GOVERNANCE_SCHEMA_DIGESTS[path]
            if _digest(base_schema) != expected_digest:
                findings.append(f"{path}: base does not match the frozen v1 contract")
            if _digest(head_schema) != expected_digest:
                findings.append(f"{path}: head does not match the frozen v1 contract")

        handoff = _parse_governance_json(
            head_values[_GOVERNANCE_HANDOFF_SCHEMA], path=_GOVERNANCE_HANDOFF_SCHEMA
        )
        if not _handoff_shape_matches(handoff):
            findings.append("governance handoff does not match the frozen v1 contract")
        findings.extend(_activation_findings(base_rules, head_rules))
        findings.extend(
            _governance_record_deletion_findings(
                base_debt, head_debt, base_examples, head_examples
            )
        )
    except ArchitectureError as exc:
        return _result(
            "governance_promotion",
            status="unsupported",
            rules=("FIT-GOVERNANCE-PROMOTION",),
            findings=(f"unsupported governance analysis: {exc}",),
            predicate=predicate,
            scope=(*governed_scope, *applicable),
            reason="unsupported_governance_semantics",
        )
    return _result(
        "governance_promotion",
        status="fail" if findings else "pass",
        rules=("FIT-GOVERNANCE-PROMOTION",),
        findings=findings,
        predicate=predicate,
        scope=(*governed_scope, *applicable),
    )


def _forbidden_edges(snapshot: ArchitectureSnapshot, diff: ArchitectureDiff) -> FitnessResult:
    rules = snapshot.rules["forbidden_edges"]
    predicate = "forbidden edge rules exist and the architecture model changed"
    if not rules:
        return _not_applicable("forbidden_edge", predicate, (), "no_declared_rules")
    if not _model_changed(diff):
        return _not_applicable(
            "forbidden_edge", predicate, (), "architecture_unchanged", (rule["id"] for rule in rules)
        )
    nodes = {node["id"]: node for node in snapshot.system["nodes"]}
    findings = []
    for rule in rules:
        for edge in snapshot.system["edges"]:
            if (
                nodes[edge["from"]]["trust_domain"] in rule["from_trust_domains"]
                and nodes[edge["to"]]["trust_domain"] in rule["to_trust_domains"]
                and edge["type"] in rule["edge_types"]
            ):
                findings.append(f"{rule['id']}: forbidden edge {edge['id']}")
    return _result(
        "forbidden_edge",
        status="fail" if findings else "pass",
        rules=(rule["id"] for rule in rules),
        findings=findings,
        predicate=predicate,
        scope=(edge["id"] for edge in snapshot.system["edges"]),
    )


def _python_paths(diff: ArchitectureDiff) -> tuple[str, ...]:
    paths = tuple(
        artifact.path
        for artifact in diff.artifacts
        if Path(artifact.path).suffix in _PYTHON_SUFFIXES and artifact.status != "deleted"
    )
    if len(paths) > MAX_ANALYZED_PYTHON_FILES:
        raise ArchitectureError("Python analysis file limit exceeded", code="limit")
    return paths


class _PythonInventory:
    def __init__(self, root: Path, diff: ArchitectureDiff) -> None:
        self.root = root
        self.diff = diff
        self._trees: dict[str, ast.AST | SyntaxError] = {}

    def tree(self, path: str) -> ast.AST:
        cached = self._trees.get(path)
        if isinstance(cached, SyntaxError):
            raise cached
        if cached is not None:
            return cached
        value = read_diff_file(self.root, self.diff, path)
        if value is None:
            error = SyntaxError("source is unavailable")
            self._trees[path] = error
            raise error
        try:
            text = value.decode("utf-8")
            tree = ast.parse(text, filename=path)
        except (UnicodeDecodeError, SyntaxError) as exc:
            error = SyntaxError(str(exc))
            self._trees[path] = error
            raise error
        if sum(1 for _ in ast.walk(tree)) > MAX_ANALYZED_AST_NODES:
            raise ArchitectureError(f"Python AST node limit exceeded: {path}", code="limit")
        self._trees[path] = tree
        return tree


def _imports(tree: ast.AST) -> tuple[str, ...]:
    values: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            values.add(node.module)
    return tuple(sorted(values))


def _network_protocol(imported: str) -> str | None:
    matches = [
        (len(family), protocol)
        for family, protocol in _NETWORK_IMPORTS.items()
        if imported == family or imported.startswith(family + ".")
    ]
    return None if not matches else max(matches)[1]


def _http_client_protocol(imported: str, call: str) -> str | None:
    if imported != "http.client" and not imported.startswith("http.client."):
        return None
    return {
        "HTTPConnection": "http",
        "HTTPSConnection": "https",
    }.get(call.rsplit(".", 1)[-1])


def _import_targets(tree: ast.AST) -> set[str]:
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.update(f"{node.module}.{alias.name}" for alias in node.names)
    return targets


def _called_imports(tree: ast.AST) -> set[tuple[str, str]]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    called: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        parts: list[str] = []
        value: ast.AST = node.func
        while isinstance(value, ast.Attribute):
            parts.append(value.attr)
            value = value.value
        if isinstance(value, ast.Name) and value.id in aliases:
            imported = aliases[value.id]
            chain = ".".join((imported, *reversed(parts)))
            called.add((imported, chain))
    return called


def _module_boundaries(
    snapshot: ArchitectureSnapshot,
    diff: ArchitectureDiff,
    python: _PythonInventory,
) -> FitnessResult:
    rules = snapshot.rules["path_boundaries"]
    predicate = "changed Python sources match a declared module-boundary source prefix"
    if not rules:
        return _not_applicable("module_boundary", predicate, (), "no_declared_rules")
    applicable = tuple(
        path
        for path in _python_paths(diff)
        if any(_matches(path, rule["source_prefixes"]) for rule in rules)
    )
    if not applicable:
        return _not_applicable(
            "module_boundary", predicate, _python_paths(diff), "no_matching_changed_source",
            (rule["id"] for rule in rules),
        )
    findings: list[str] = []
    try:
        for path in applicable:
            imports = _imports(python.tree(path))
            for rule in rules:
                if not _matches(path, rule["source_prefixes"]):
                    continue
                forbidden = {
                    prefix.replace("/", ".").replace("-", "_").lstrip(".")
                    for prefix in rule["forbidden_dependency_prefixes"]
                }
                if "trust_ci" in forbidden:
                    forbidden.add("adaptive_trust_ci")
                for imported in imports:
                    if any(imported == prefix or imported.startswith(prefix + ".") for prefix in forbidden):
                        findings.append(f"{rule['id']}: {path} imports forbidden {imported}")
    except SyntaxError as exc:
        return _result(
            "module_boundary",
            status="unsupported",
            rules=(rule["id"] for rule in rules),
            findings=(f"Python source analysis unsupported: {exc}",),
            predicate=predicate,
            scope=applicable,
            reason="unparseable_source",
        )
    return _result(
        "module_boundary",
        status="fail" if findings else "pass",
        rules=(rule["id"] for rule in rules),
        findings=findings,
        predicate=predicate,
        scope=applicable,
    )


def _contract_compatibility(snapshot: ArchitectureSnapshot, diff: ArchitectureDiff) -> FitnessResult:
    rules = snapshot.rules["contract_policies"]
    predicate = "declared contract policy intersects an added, removed, or changed contract"
    if not rules:
        return _not_applicable("contract_compatibility", predicate, (), "no_declared_rules")
    changed_ids = {item.id for item in diff.changes if item.kind == "contract"}
    if not changed_ids:
        return _not_applicable(
            "contract_compatibility", predicate, (), "contracts_unchanged", (rule["id"] for rule in rules)
        )
    before = {item.id: item for item in (diff._base_state.contracts if diff._base_state else ())}
    after = {item.id: item for item in diff._head_state.contracts}
    findings: list[str] = []
    unsupported: list[str] = []
    used_rules: set[str] = set()
    for identity in sorted(changed_ids):
        old, new = before.get(identity), after.get(identity)
        record = new if new is not None else old
        if record is None:
            raise ArchitectureError("changed contract is absent from both states", code="fitness")
        kind = record.kind
        matching = [rule for rule in rules if kind in rule["contract_kinds"]]
        used_rules.update(rule["id"] for rule in matching)
        if not matching:
            unsupported.append(f"{identity}: no compatibility policy for {kind}")
        elif old is None:
            for rule in matching:
                result = compare_contracts(new, new, rule["compatibility"])
                if result.status == "unsupported":
                    unsupported.append(
                        f"{identity}: unsupported added-contract baseline semantics"
                    )
        elif new is None:
            findings.append(f"{identity}: declared contract removed")
        else:
            for rule in matching:
                result = compare_contracts(old, new, rule["compatibility"])
                if result.status == "unsupported":
                    unsupported.append(f"{identity}: unsupported compatibility semantics")
                elif result.status != "compatible":
                    findings.append(f"{identity}: {','.join(result.reasons)}")
    if unsupported:
        status = "unsupported"
    elif findings:
        status = "fail"
    else:
        status = "pass"
    return _result(
        "contract_compatibility",
        status=status,
        rules=used_rules,
        findings=(*findings, *unsupported),
        predicate=predicate,
        scope=changed_ids,
        reason="unsupported_contract_semantics" if unsupported else "applicable",
    )


def _repository_paths(root: Path, diff: ArchitectureDiff, prefixes: tuple[str, ...]) -> tuple[str, ...]:
    if diff.head_kind == "commit":
        if diff.head_sha is None:
            raise ArchitectureError("commit diff is missing exact head_sha", code="git")
        return git_tree_paths(root, diff.head_sha, prefixes)
    base_paths = set(git_tree_paths(root, diff.base_sha, prefixes))
    for artifact in diff.artifacts:
        if not _matches(artifact.path, prefixes):
            continue
        if artifact.status == "deleted":
            base_paths.discard(artifact.path)
        else:
            base_paths.add(artifact.path)
    return tuple(sorted(base_paths))


def _migration_phase(path: str) -> tuple[str, str] | None:
    match = _MIGRATION_PHASE.fullmatch(Path(path).stem.lower()) or _MIGRATION_CANONICAL.fullmatch(Path(path).stem.lower())
    return None if match is None else (match.group("group"), match.groupdict().get("phase") or "legacy")


def _migration_roots(snapshot: ArchitectureSnapshot, prefixes: tuple[str, ...]) -> tuple[str, ...]:
    primary = set(prefixes)
    return tuple(sorted(primary | {
        path for node in snapshot.system["nodes"] if primary & set(node["repository_paths"])
        for path in node["repository_paths"]
        if Path(path).name.lower() in {"resources", "migrations"}
    }))


def _bounded_migrate_predicate(statement: str) -> bool:
    where = re.search(r"\bWHERE\b(?P<predicate>.*?)(?:\bRETURNING\b|$)", statement)
    predicate = where.group("predicate") if where else ""
    identifier = r"[A-Z_][A-Z0-9_.]*"
    operand = r"(?:\?|\$[0-9]+|%S|:[A-Z_][A-Z0-9_]*|[-+]?[0-9]+)"
    pattern = (rf"\s*(?P<column>{identifier})\s*(?P<first>>=?|<=?)\s*{operand}\s+AND\s+"
               rf"(?P=column)\s*(?P<second>>=?|<=?)\s*{operand}\s*")
    match = re.fullmatch(pattern, predicate)
    between = re.fullmatch(rf"\s*{identifier}\s+BETWEEN\s+{operand}\s+AND\s+{operand}\s*", predicate)
    return bool(between or match and (match["first"].startswith(">") != match["second"].startswith(">")))


class _MigrationPlan(NamedTuple):
    rule: dict[str, Any]
    roots: tuple[str, ...]
    relevant: tuple[ChangedArtifact, ...]
    primary: tuple[ChangedArtifact, ...]
    head_paths: tuple[str, ...]
    copies: dict[str, tuple[str, ...]]


class _MigrationAnalysis:
    def __init__(self) -> None:
        self.plans: list[_MigrationPlan] = []
        self.root_plans: dict[str, list[int]] = {}
        self.scope: tuple[str, ...] = ()
        self.issues: list[tuple[bool, str]] = []
        self.statements = self.work = 0

    def bound(self, amount: int) -> None:
        self.work += amount
        if self.work > MAX_MIGRATION_WORK:
            raise ArchitectureError("migration aggregate work limit exceeded", code="limit")

    def record(self, unsupported: bool, message: str) -> None:
        if len(self.issues) >= MAX_MIGRATION_FINDINGS - 1:
            raise ArchitectureError("migration finding limit exceeded", code="limit")
        self.issues.append((unsupported, message))

    def read(self, root: Path, diff: ArchitectureDiff, paths: Iterable[str]) -> dict[str, bytes | None]:
        values: dict[str, bytes | None] = {}
        ordered = tuple(sorted(set(paths)))
        total = 0
        for start in range(0, len(ordered), MAX_MIGRATION_BATCH_PATHS):
            batch = read_diff_files(root, diff, ordered[start:start + MAX_MIGRATION_BATCH_PATHS])
            total += sum(len(value or b"") for value in batch.values())
            if total > MAX_MIGRATION_BYTES:
                raise ArchitectureError("migration aggregate byte limit exceeded", code="limit")
            values.update(batch)
        return values

    def source(self, rule_id: str, path: str, phase: str, source: str) -> None:
        found = False
        statements = (re.sub(r"--[^\n]*", "", part[0]).strip() for part in re.finditer(r"(?m)(?:--[^\n]*(?:\n|$)|[^;])+", source))
        for statement in filter(None, statements):
            found = True
            if (statement_limit := self.statements >= MAX_MIGRATION_STATEMENTS) or len(self.issues) >= MAX_MIGRATION_FINDINGS - 1:
                raise ArchitectureError("migration statement work limit exceeded" if statement_limit else "migration finding limit exceeded", code="limit")
            self.statements += 1
            normalized = " ".join(statement.upper().split())
            verb = normalized.split()[0]
            unbounded = phase == "migrate" and verb in {"UPDATE", "DELETE"} and (
                not re.search(r"\bWHERE\b", normalized)
                or re.search(r"\bWHERE\b.*(?:\b1\s*=\s*1\b|\bTRUE\b)", normalized)
            )
            unproven = (phase == "migrate" and verb in {"UPDATE", "DELETE"}
                        and not unbounded and not _bounded_migrate_predicate(normalized))
            checks = (
                (phase != "contract" and re.search(r"\b(DROP|TRUNCATE)\b|\bALTER TABLE\b.*\bDROP\b", normalized), False, "destructive SQL outside contract phase"),
                (phase == "expand" and " NOT NULL" in normalized, False, "NOT NULL is unsafe in expand phase"),
                (phase == "expand" and not re.match(r"^(CREATE TABLE|CREATE (UNIQUE )?INDEX CONCURRENTLY|ALTER TABLE .* ADD )", normalized), True, "unsupported expand SQL semantics"),
                (unbounded, False, f"unbounded {verb} in migrate phase"),
                (unproven, True, "migrate bounded/resumable predicate is unproven"),
                (phase == "migrate" and verb not in {"UPDATE", "DELETE"}, True, "unsupported bounded INSERT semantics" if verb == "INSERT" else "unsupported migrate SQL semantics"),
                (phase == "contract" and re.match(r"^ALTER TABLE\b.*\bADD\b", normalized), False, "expansive SQL in contract phase"),
                (phase == "contract" and not re.match(r"^(ALTER TABLE .* DROP|DROP|TRUNCATE)\b", normalized), True, "unsupported contract SQL semantics"),
            )
            if issue := next(((unsupported, message) for applies, unsupported, message in checks if applies), None):
                self.record(issue[0], f"{rule_id}: {issue[1]}: {path}")
        if not found:
            self.record(True, f"{rule_id}: migration contains no analyzable SQL: {path}")

    def check(self, plan: _MigrationPlan, blobs: dict[str, bytes | None]) -> None:
        rule, rule_id = plan.rule, plan.rule["id"]
        changed_primary = {
            item.path[len(prefix):].lstrip("/") for item in plan.primary for prefix in rule["path_prefixes"]
            if _matches(item.path, (prefix,))
        }
        for item in plan.relevant:
            relative = next(item.path[len(prefix):].lstrip("/") for prefix in plan.roots if _matches(item.path, (prefix,)))
            if item not in plan.primary and relative not in changed_primary:
                self.record(False, f"{rule_id}: migration mirror differs: {item.path}")
            if rule["immutable_history"] and item.status in {"modified", "deleted"}:
                self.record(False, f"{rule_id}: immutable migration history changed: {item.path}")
        phases, version_groups, phase_paths = {}, {}, set()
        for path in plan.head_paths:
            parsed = _migration_phase(path)
            if parsed is None:
                continue
            group, phase = parsed
            phases.setdefault(group, set()).add(phase)
            if (match := re.match(r"^(?:v)?(?P<version>[0-9]+)(?:[_-].*)?$", group)) is None:
                self.record(True, f"{rule_id}: migration version cannot be derived: {path}")
                continue
            version = int(match.group("version"))
            version_groups.setdefault(version, set()).add((group, phase == "legacy"))
            if (version, group, phase) in phase_paths:
                self.record(False, f"{rule_id}: duplicate migration artifact for {version}/{group}/{phase}: {path}")
            phase_paths.add((version, group, phase))
        for version, groups in version_groups.items():
            if len(groups) > 1:
                self.record(False, f"{rule_id}: duplicate migration version {version}: {','.join(sorted(group for group, _ in groups))}")
        if version_groups and set(version_groups) != set(range(1, max(version_groups) + 1)):
            self.record(False, f"{rule_id}: migration version history is not contiguous")
        for item in plan.primary:
            if item.status == "deleted":
                self.record(False, f"{rule_id}: migration history removed: {item.path}")
                continue
            parsed = _migration_phase(item.path)
            if parsed is None:
                self.record(True, f"{rule_id}: migration phase cannot be derived: {item.path}")
                continue
            missing = sorted(set(rule["required_phases"]) - phases.get(parsed[0], set()))
            if missing:
                self.record(False, f"{rule_id}: migration {parsed[0]} missing phases: {','.join(missing)}")
            value = blobs.get(item.path)
            if value is None:
                self.record(True, f"{rule_id}: migration source unavailable: {item.path}")
                continue
            try:
                source = value.decode("utf-8")
            except UnicodeDecodeError:
                self.record(True, f"{rule_id}: migration is not UTF-8: {item.path}")
                continue
            self.source(rule_id, item.path, parsed[1], source)
            for mirror in plan.copies[item.path]:
                mirror_value = blobs.get(mirror)
                if mirror_value != value:
                    self.record(False, f"{rule_id}: migration mirror {'missing' if mirror_value is None else 'differs'}: {mirror}")


def _migration_safety(root: Path, snapshot: ArchitectureSnapshot, diff: ArchitectureDiff) -> FitnessResult:
    rules = snapshot.rules["migration_policies"]
    predicate = "changed SQL paths match a declared migration-history or derived mirror prefix"
    if not rules:
        return _not_applicable("migration_safety", predicate, (), "no_declared_rules")
    analysis = _MigrationAnalysis()
    try:
        analysis.bound(sum(len(rule["path_prefixes"]) for rule in rules) * sum(
            max(1, len(node["repository_paths"])) for node in snapshot.system["nodes"]))
        seeds = []
        for rule in rules:
            mirrors = tuple(
                (prefix, tuple(path for path in _migration_roots(snapshot, (prefix,)) if path != prefix))
                for prefix in rule["path_prefixes"])
            analysis.bound(len(roots := tuple(sorted(set(rule["path_prefixes"]).union(*(paths for _, paths in mirrors))))))
            seeds.append((rule, roots, mirrors))
            for migration_root in roots:
                analysis.root_plans.setdefault(migration_root, []).append(len(seeds) - 1)
        sql = tuple(item for item in diff.artifacts if Path(item.path).suffix.lower() == ".sql")
        analysis.bound(len(sql) * max(1, root_memberships := sum(len(v) for v in analysis.root_plans.values())))
        matches = {item.path: {index for prefix, indices in analysis.root_plans.items()
                               if _matches(item.path, (prefix,)) for index in indices}
                   for item in sql}
        applicable = tuple(item for item in sql if matches[item.path])
        analysis.bound(root_memberships + len(applicable) * len(seeds))
        inventory = _repository_paths(root, diff, tuple(analysis.root_plans))
        analysis.scope = (*analysis.root_plans, *inventory, *(item.path for item in applicable))
        analysis.bound(len(inventory) * max(len(seeds), sum(len(rule["path_prefixes"]) for rule in rules))
                       + 2 * len(applicable) * max(1, root_memberships))
        if not applicable:
            return _not_applicable("migration_safety", predicate, analysis.scope,
                                   "no_matching_sql_change", (rule["id"] for rule in rules))
        reads: set[str] = set()
        for index, (rule, roots, mirrors) in enumerate(seeds):
            relevant = tuple(item for item in applicable if index in matches[item.path])
            primary = tuple(item for item in relevant if _matches(item.path, tuple(rule["path_prefixes"])))
            head_paths = tuple(path for path in inventory if _matches(path, tuple(rule["path_prefixes"])))
            copies: dict[str, tuple[str, ...]] = {}
            reads.update(item.path for item in primary if item.status != "deleted")
            for item in primary:
                prefix = next(path for path in rule["path_prefixes"] if _matches(item.path, (path,)))
                relative = item.path[len(prefix):].lstrip("/")
                copies[item.path] = tuple(
                    f"{mirror}/{relative}" for prefix, mirror_roots in mirrors
                    if _matches(item.path, (prefix,)) for mirror in mirror_roots)
                reads.update(copies[item.path])
            analysis.plans.append(_MigrationPlan(rule, roots, relevant, primary, head_paths, copies))
        analysis.bound(len(reads))
        blobs = analysis.read(root, diff, reads)
        for plan in analysis.plans:
            analysis.check(plan, blobs)
    except ArchitectureError as exc:
        analysis.issues.append((True, str(exc)))
    unsupported = any(item[0] for item in analysis.issues)
    status = "unsupported" if unsupported else ("fail" if analysis.issues else "pass")
    return _result("migration_safety", status=status, rules=(rule["id"] for rule in rules),
                   findings=(item[1] for item in analysis.issues), predicate=predicate, scope=analysis.scope,
                   reason="unsupported_migration_semantics" if unsupported else "applicable")


def _tenant_authorization(snapshot: ArchitectureSnapshot, diff: ArchitectureDiff) -> FitnessResult:
    rules = snapshot.rules["tenant_authorization_policies"]
    predicate = "tenant-scoped declared data is covered and authorized on every architecture edge"
    tenant_data = {item["id"] for item in snapshot.system["data_classifications"] if item["tenant_scoped"]}
    if not tenant_data:
        return _not_applicable("tenant_authorization", predicate, (), "no_tenant_scoped_data")
    if not _model_changed(diff):
        return _not_applicable(
            "tenant_authorization", predicate, (), "architecture_unchanged", (rule["id"] for rule in rules)
        )
    edges = [edge for edge in snapshot.system["edges"] if tenant_data & set(edge["allowed_data"])]
    covered = {item for rule in rules for item in rule["data_classifications"]}
    missing = tenant_data - covered
    findings = [f"unauthenticated tenant edge {edge['id']}"
                for edge in edges if edge["authentication"] == "none"]
    unsupported = [f"missing tenant policy coverage: {','.join(sorted(missing))}"] if missing else []
    unsupported.extend(
        f"{rule['id']}: model v1 has no tenant-filter edge field"
        for edge in edges for rule in rules if rule["require_tenant_filter"]
        and set(edge["allowed_data"]) & set(rule["data_classifications"]) & tenant_data)
    status = "unsupported" if unsupported else ("fail" if findings else "pass")
    return _result("tenant_authorization", status=status, rules=(rule["id"] for rule in rules),
                   findings=(*findings, *unsupported), predicate=predicate,
                   scope=(*tenant_data, *(edge["id"] for edge in edges)),
                   reason="unsupported_tenant_semantics" if status == "unsupported" else "applicable")


def _owner_for_path(snapshot: ArchitectureSnapshot, path: str) -> dict[str, Any] | None:
    matches = [
        (len(repository_path), node)
        for node in snapshot.system["nodes"]
        for repository_path in node["repository_paths"]
        if _matches(path, (repository_path,))
    ]
    if not matches:
        return None
    specificity = max(length for length, _ in matches)
    owners = {node["id"]: node for length, node in matches if length == specificity}
    if len(owners) != 1:
        raise ArchitectureError(
            f"ambiguous repository owner for {path}: {sorted(owners)}",
            code="fitness",
        )
    return next(iter(owners.values()))


def _project_import_roots(
    snapshot: ArchitectureSnapshot, diff: ArchitectureDiff, root: Path
) -> set[str]:
    prefixes = tuple(
        sorted(
            {
                repository_path
                for node in snapshot.system["nodes"]
                for repository_path in node["repository_paths"]
            }
        )
    )
    paths = _repository_paths(root, diff, prefixes) if prefixes else ()
    roots = set(_GOVERNANCE_IMPORTS)
    for path in paths:
        if Path(path).suffix not in _PYTHON_SUFFIXES:
            continue
        matching = [prefix for prefix in prefixes if _matches(path, (prefix,))]
        if not matching:
            continue
        prefix = max(matching, key=len)
        relative = path[len(prefix) :].lstrip("/")
        if not relative:
            roots.add(Path(prefix).stem)
            continue
        if relative == "__init__.py":
            roots.add(Path(prefix).name)
        first = relative.split("/", 1)[0]
        roots.add(Path(first).stem if first.endswith(tuple(_PYTHON_SUFFIXES)) else first)
    return roots


def _is_external_import(imported: str, project_roots: set[str]) -> bool:
    top = imported.split(".")[0]
    return top not in sys.stdlib_module_names and top not in project_roots


def _network_call_is_applicable(
    imported: str, call: str, project_roots: set[str]
) -> bool:
    if not _is_external_import(imported, project_roots):
        return False
    family = imported.split(".")[0].lower()
    factory = call.rsplit(".", 1)[-1].lower()
    if factory in _CLOUD_SDK_NETWORK_FACTORIES.get(family, set()):
        return True
    tokens = {
        token.lower()
        for token in re.findall(
            r"[A-Z]+(?=[A-Z][a-z]|[^A-Za-z]|$)|[A-Z]?[a-z]+|[0-9]+",
            f"{imported}.{call}",
        )
    }
    return bool(tokens & _NETWORK_APPLICABILITY_TOKENS)


def _network_clients(
    snapshot: ArchitectureSnapshot,
    diff: ArchitectureDiff,
    python: _PythonInventory,
) -> FitnessResult:
    rules = snapshot.rules["network_policies"]
    predicate = "changed owned Python source imports a bounded network-client family"
    if not rules:
        return _not_applicable("network_client", predicate, (), "no_declared_rules")
    clients: list[tuple[str, str, dict[str, Any] | None]] = []
    unsupported: list[str] = []
    project_roots = _project_import_roots(snapshot, diff, python.root)
    for path in _python_paths(diff):
        owner = _owner_for_path(snapshot, path)
        try:
            tree = python.tree(path)
            imports = _import_targets(tree)
        except SyntaxError as exc:
            unsupported.append(f"{path}: {exc}")
            continue
        for imported in imports:
            protocol = _network_protocol(imported)
            if protocol:
                clients.append((path, protocol, owner))
        for imported, call in _called_imports(tree):
            protocol = _http_client_protocol(imported, call)
            if protocol is not None:
                clients.append((path, protocol, owner))
                continue
            if _network_protocol(imported) is not None:
                continue
            if _network_call_is_applicable(imported, call, project_roots):
                unsupported.append(f"{path}: unsupported external-client semantics for {call}")
    if unsupported:
        return _result(
            "network_client",
            status="unsupported",
            rules=(rule["id"] for rule in rules),
            findings=unsupported,
            predicate=predicate,
            scope=_python_paths(diff),
            reason="unparseable_source",
        )
    if not clients:
        return _not_applicable(
            "network_client", predicate, _python_paths(diff), "no_network_client",
            (rule["id"] for rule in rules),
        )
    findings: list[str] = []
    edges = snapshot.system["edges"]
    for path, protocol, owner in clients:
        if owner is None:
            findings.append(f"unowned network client {protocol} in {path}")
            continue
        matching_rules = [rule for rule in rules if owner["type"] in rule["node_types"]]
        if not matching_rules:
            findings.append(f"no network policy for {protocol} in {path} for {owner['id']}")
            continue
        for rule in matching_rules:
            declared = any(
                edge["from"] == owner["id"] and edge["protocol"] == protocol for edge in edges
            )
            if protocol not in rule["allowed_protocols"] or (rule["require_declared_edge"] and not declared):
                findings.append(
                    f"{rule['id']}: undeclared network client {protocol} in {path} for {owner['id']}"
                )
    return _result(
        "network_client",
        status="fail" if findings else "pass",
        rules=(rule["id"] for rule in rules),
        findings=findings,
        predicate=predicate,
        scope=(item[0] for item in clients),
    )


def _production_imports(diff: ArchitectureDiff, python: _PythonInventory) -> FitnessResult:
    predicate = "changed production Python source imports test or governance modules"
    applicable = tuple(
        path for path in _python_paths(diff) if not _matches(path, _GOVERNANCE_PATHS)
    )
    if not applicable:
        return _not_applicable(
            "production_import", predicate, _python_paths(diff), "no_changed_production_source"
        )
    findings: list[str] = []
    try:
        for path in applicable:
            for imported in _imports(python.tree(path)):
                if imported.split(".")[0] in _GOVERNANCE_IMPORTS:
                    findings.append(f"{path} imports governance/test module {imported}")
    except SyntaxError as exc:
        return _result(
            "production_import",
            status="unsupported",
            findings=(f"Python source analysis unsupported: {exc}",),
            predicate=predicate,
            scope=applicable,
            reason="unparseable_source",
        )
    return _result(
        "production_import",
        status="fail" if findings else "pass",
        findings=findings,
        predicate=predicate,
        scope=applicable,
    )


def _change_separation(snapshot: ArchitectureSnapshot, diff: ArchitectureDiff) -> FitnessResult:
    rules = snapshot.rules["change_separation_policies"]
    predicate = "changed paths intersect an implementation or Trust CI separation boundary"
    if not rules:
        return _not_applicable("change_separation", predicate, diff.changed_paths, "no_declared_rules")
    findings: list[str] = []
    applicable = False
    for rule in rules:
        implementation = tuple(path for path in diff.changed_paths if _matches(path, rule["implementation_prefixes"]))
        trust_ci = tuple(path for path in diff.changed_paths if _matches(path, rule["trust_ci_prefixes"]))
        applicable = applicable or bool(implementation or trust_ci)
        if implementation and trust_ci:
            findings.append(f"{rule['id']}: implementation and trust-ci mutations are mixed")
    if not applicable:
        return _not_applicable(
            "change_separation", predicate, diff.changed_paths, "no_separation_path_changed",
            (rule["id"] for rule in rules),
        )
    return _result(
        "change_separation",
        status="fail" if findings else "pass",
        rules=(rule["id"] for rule in rules),
        findings=findings,
        predicate=predicate,
        scope=diff.changed_paths,
    )


_COMPLEXITY_NODES = (
    ast.AsyncFor,
    ast.BoolOp,
    ast.comprehension,
    ast.ExceptHandler,
    ast.For,
    ast.If,
    ast.IfExp,
    ast.Match,
    ast.Try,
    ast.While,
)


def _code_budget(
    snapshot: ArchitectureSnapshot,
    diff: ArchitectureDiff,
    python: _PythonInventory,
) -> FitnessResult:
    rules = snapshot.rules["code_budgets"]
    predicate = "changed code intersects a declared changed-code budget"
    if not rules:
        return _not_applicable("code_budget", predicate, diff.changed_paths, "no_declared_rules")
    findings: list[str] = []
    unsupported: list[str] = []
    applicable_paths: set[str] = set()
    for rule in rules:
        artifacts = [item for item in diff.artifacts if _matches(item.path, rule["path_prefixes"])]
        if not artifacts:
            continue
        applicable_paths.update(item.path for item in artifacts)
        changed_bytes = sum(max(item.base_size, item.head_size) for item in artifacts)
        unknown_line_items = [
            item.path
            for item in artifacts
            if item.added_lines is None or item.deleted_lines is None
        ]
        unsupported.extend(
            f"{rule['id']}: unknown line statistics for {path}"
            for path in unknown_line_items
        )
        changed_lines = sum(
            item.added_lines + item.deleted_lines
            for item in artifacts
            if item.added_lines is not None and item.deleted_lines is not None
        )
        complexity = 0
        for item in artifacts:
            if Path(item.path).suffix not in _PYTHON_SUFFIXES:
                continue
            try:
                tree = python.tree(item.path) if item.status != "deleted" else ast.parse(
                    (read_diff_file(python.root, diff, item.path, "base") or b"").decode("utf-8"),
                    filename=item.path,
                )
            except (SyntaxError, UnicodeDecodeError) as exc:
                unsupported.append(f"{rule['id']}: cannot analyze {item.path}: {exc}")
                continue
            complexity += sum(isinstance(node, _COMPLEXITY_NODES) for node in ast.walk(tree))
        metrics = {
            "max_changed_bytes": changed_bytes,
            "max_changed_lines": changed_lines,
            "max_ast_complexity": complexity,
        }
        for field, actual in metrics.items():
            if actual > rule[field]:
                findings.append(f"{rule['id']}: {field} {actual} exceeds {rule[field]}")
    if not applicable_paths:
        return _not_applicable(
            "code_budget", predicate, diff.changed_paths, "no_budget_path_changed",
            (rule["id"] for rule in rules),
        )
    status = "unsupported" if unsupported else ("fail" if findings else "pass")
    return _result(
        "code_budget",
        status=status,
        rules=(rule["id"] for rule in rules),
        findings=(*findings, *unsupported),
        predicate=predicate,
        scope=applicable_paths,
        reason="unsupported_source" if unsupported else "applicable",
    )


def _operation_dependencies(
    tree: ast.AST,
    *,
    work_limit: int = MAX_QUEUE_DEPENDENCY_WORK,
) -> _OperationDependencies:
    """Return names that can feed a changed callable/decorator expression."""
    dependencies: set[str] = set()
    for node in ast.walk(tree):
        values: list[ast.AST] = []
        if isinstance(node, ast.Call):
            values.append(node.func)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            values.extend(node.decorator_list)
        for value in values:
            dependencies.update(
                child.id for child in ast.walk(value) if isinstance(child, ast.Name)
            )
    assignments: dict[str, set[str]] = {}
    imported_names = {
        alias.asname or alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    def target_names(target: ast.AST) -> set[str]:
        if isinstance(target, ast.Name):
            return {target.id}
        if isinstance(target, ast.Starred):
            return target_names(target.value)
        if isinstance(target, (ast.List, ast.Tuple)):
            return set().union(*(target_names(item) for item in target.elts))
        if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
            return {target.value.id}
        return set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                for name in target_names(target):
                    assignments.setdefault(name, set()).update(
                        child.id
                        for child in ast.walk(node.value)
                        if isinstance(child, ast.Name)
                    )
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            for name in target_names(node.target):
                assignments.setdefault(name, set()).update(
                    child.id
                    for child in ast.walk(node.value)
                    if isinstance(child, ast.Name)
                )
        elif (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and isinstance(node.value.func.value, ast.Name)
            and node.value.func.attr in {"append", "extend"}
        ):
            assignments.setdefault(node.value.func.value.id, set()).update(
                child.id
                for argument in node.value.args
                for child in ast.walk(argument)
                if isinstance(child, ast.Name)
            )
    pending = deque(sorted(dependencies))
    processed: set[str] = set()
    work = 0
    while pending:
        name = pending.popleft()
        if name in processed:
            continue
        if work >= work_limit:
            frontier = {name, *pending}
            unresolved = set(frontier)
            unresolved_pending = deque(sorted(frontier))
            while unresolved_pending:
                unresolved_name = unresolved_pending.popleft()
                for dependency in sorted(assignments.get(unresolved_name, ())):
                    if dependency not in unresolved:
                        unresolved.add(dependency)
                        unresolved_pending.append(dependency)
            return _OperationDependencies(
                frozenset(dependencies), frozenset(unresolved),
                frozenset(unresolved & imported_names), True
            )
        work += 1
        processed.add(name)
        for dependency in sorted(assignments.get(name, ())):
            if dependency not in dependencies:
                dependencies.add(dependency)
                pending.append(dependency)
    return _OperationDependencies(frozenset(dependencies))


def _declared_module_exports(tree: ast.Module) -> tuple[str, ...]:
    declared: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            declared.add(node.name)
        elif isinstance(node, ast.Assign):
            declared.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            declared.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            declared.update(alias.asname or alias.name for alias in node.names)
    return tuple(sorted(name for name in declared if not name.startswith("_")))


def _resolve_import_module(current_package: str, module: str | None, level: int) -> str:
    if not level:
        return module or ""
    package = current_package.split(".") if current_package else []
    remove = level - 1
    if remove > len(package):
        raise ArchitectureError("relative queue adapter import escapes its package", code="fitness")
    prefix = package[: len(package) - remove] if remove else package
    suffix = module.split(".") if module else []
    return ".".join((*prefix, *suffix))


def _module_package(path: str, source_roots: tuple[str, ...] = ()) -> str:
    relative = path
    matching_roots = [
        root for root in source_roots if root and _matches(path, (root,))
    ]
    if matching_roots:
        relative = path[len(max(matching_roots, key=len)) + 1:]
    module = relative.rsplit(".", 1)[0].replace("/", ".")
    if module.endswith(".__init__"):
        return module.removesuffix(".__init__")
    return module.rsplit(".", 1)[0] if "." in module else ""


def _queue_adjacent_module(module: str) -> bool:
    tokens = set(filter(None, re.split(r"[^A-Za-z0-9]+|_+", module.lower())))
    return bool(tokens & _QUEUE_ADAPTER_MODULE_TOKENS)


def _queue_source_roots(snapshot: ArchitectureSnapshot) -> tuple[str, ...]:
    roots = {""}
    file_suffixes = {
        ".json", ".md", ".py", ".pyi", ".sh", ".sql", ".toml", ".txt", ".yaml", ".yml"
    }
    for node in snapshot.system["nodes"]:
        for prefix in node["repository_paths"]:
            name = prefix.rsplit("/", 1)[-1]
            if Path(prefix).suffix.lower() in file_suffixes:
                continue
            roots.add(prefix)
            if "/" in prefix and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                roots.add(prefix.rsplit("/", 1)[0])
    return tuple(sorted(roots))


def _queue_module_inventory(root: Path, diff: ArchitectureDiff, side: str, source_roots: tuple[str, ...]) -> _QueueResolutionCache:
    paths = _repository_paths(root, diff, source_roots) if side == "head" else git_tree_paths(root, diff.base_sha, source_roots)
    modules = {relative.removesuffix("/__init__.py").removesuffix(".py").replace("/", ".") for path in paths for prefix in source_roots if not prefix or _matches(path, (prefix,)) for relative in (path[len(prefix) + 1:] if prefix else path,) if relative.endswith(".py")}
    return _QueueResolutionCache(tuple(sorted(modules)), tuple(sorted(path for path in paths if path.endswith(".py"))), {})


def _prime_local_module_sources(
    root: Path, diff: ArchitectureDiff, modules: set[str], side: str,
    cache: _QueueResolutionCache, source_roots: tuple[str, ...],
    remaining: int,
) -> None:
    pending = sorted(module for module in modules if module in cache.modules and module not in cache.values)
    if len(pending) > remaining:
        raise ArchitectureError("queue adapter module limit exceeded", code="limit")
    paths_by_module = {
        module: tuple(path for source_root in source_roots for path in (
            f"{source_root + '/' if source_root else ''}{module.replace('.', '/')}.py",
            f"{source_root + '/' if source_root else ''}{module.replace('.', '/')}/__init__.py",
        ) if path in cache.paths)
        for module in pending
    }
    for module, paths in paths_by_module.items():
        if len(paths) > 1:
            cache.values[module] = _QueueAdapterResolution("unsupported", "ambiguous_local_queue_adapter")
    values = read_diff_files(root, diff, tuple(paths[0] for module, paths in paths_by_module.items() if module not in cache.values and paths), side)
    for module, paths in paths_by_module.items():
        if module in cache.values:
            continue
        sources = tuple((path, values[path], module if path.endswith("/__init__.py") else module.rsplit(".", 1)[0] if "." in module else "") for path in paths if values[path] is not None)
        cache.values[module] = _QueueAdapterResolution("prefetched", "local_module_prefetched", sources=sources)


def _is_local_package(cache: _QueueResolutionCache, module: str) -> bool:
    package_path = f"{module.replace('.', '/')}/__init__.py"
    return any(path.endswith(package_path) for path in cache.paths) or module not in cache.modules and any(name.startswith(module + ".") for name in cache.modules)


def _local_queue_resolution(
    root: Path,
    diff: ArchitectureDiff,
    module: str,
    side: str,
    cache: _QueueResolutionCache,
    resolving: set[str],
    visited: set[str],
    source_roots: tuple[str, ...],
) -> _QueueAdapterResolution:
    if (
        not module
        or any(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part) is None for part in module.split("."))
    ):
        return _QueueAdapterResolution("not_queue", "invalid_local_module")
    if module not in cache.modules:
        return _QueueAdapterResolution("not_queue", "local_module_missing")
    if module not in visited:
        if len(visited) >= MAX_QUEUE_ADAPTER_MODULES:
            raise ArchitectureError("queue adapter module limit exceeded", code="limit")
        visited.add(module)
    prefetched = cache.values.get(module)
    if prefetched is not None and prefetched.state != "prefetched":
        return prefetched
    if len(resolving) >= MAX_QUEUE_ADAPTER_DEPTH:
        raise ArchitectureError("queue adapter depth limit exceeded", code="limit")
    if module in resolving:
        return _QueueAdapterResolution("unsupported", "cyclic_local_queue_adapter")
    resolving.add(module)
    try:
        sources = prefetched.sources if prefetched is not None else ()
        if not sources:
            result = _QueueAdapterResolution("not_queue", "local_module_missing")
            cache.values[module] = result
            return result
        source_path, value, current_package = sources[0]
        try:
            tree = ast.parse(value.decode("utf-8"), filename=source_path)
        except (SyntaxError, UnicodeDecodeError) as exc:
            raise ArchitectureError(
                f"relevant local queue adapter is not analyzable: {module}",
                code="fitness",
            ) from exc
        if sum(1 for _ in ast.walk(tree)) > MAX_ANALYZED_AST_NODES:
            raise ArchitectureError(f"Python AST node limit exceeded: {module}", code="limit")
        imported = _queue_adapter_names(
            root,
            diff,
            tree,
            side,
            cache,
            resolving,
            visited,
            current_package=current_package,
            source_roots=source_roots,
        )
        try:
            analysis = analyze_queue_tree(tree, imported.names)
        except QueueAnalysisLimit as exc:
            raise ArchitectureError(str(exc), code="limit") from exc
        exports = tuple(sorted(
            name for name in analysis.derived_names if not name.startswith("_")
        ))
        has_queue_provenance = bool(analysis.signals or exports)
        state = (
            "unsupported"
            if (imported.unsupported or analysis.uncertain) and has_queue_provenance
            else ("resolved" if has_queue_provenance else "not_queue")
        )
        reason = "local_queue_provenance_resolved" if has_queue_provenance else "local_module_not_queue"
        result = _QueueAdapterResolution(
            state, reason, exports, analysis.signals, _declared_module_exports(tree)
        )
        cache.values[module] = result
        return result
    finally:
        resolving.remove(module)


def _queue_adapter_names(
    root: Path,
    diff: ArchitectureDiff,
    tree: ast.AST,
    side: str,
    cache: _QueueResolutionCache,
    resolving: set[str] | None = None,
    visited: set[str] | None = None,
    *, current_package: str = "",
    source_roots: tuple[str, ...],
) -> _QueueAdapterNamesResult:
    proven: set[str] = set()
    unsupported = False
    active = resolving if resolving is not None else set()
    seen = visited if visited is not None else set()
    dependency_result = _operation_dependencies(tree)
    dependencies = set(dependency_result.names)
    reachable = dependencies | set(dependency_result.frontier)
    if resolving is not None:
        dependencies.update(
            alias.asname or alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        )
    normalized: list[tuple[str, str, str, str, int, bool, bool]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports = tuple((alias.name, "", alias.asname or alias.name.split(".", 1)[0], alias.asname or alias.name, 0, True, False) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = _resolve_import_module(current_package, node.module, node.level)
            imports = tuple((
                f"{module}.{alias.name}" if node.module is None else module,
                "" if node.module is None else alias.name,
                alias.asname or alias.name,
                alias.asname or alias.name,
                node.level, node.module is None, alias.name == "*",
            ) for alias in node.names)
        else:
            continue
        normalized.extend(imports)
    relevant = [item for item in normalized if item[0].split(".")[0] not in _QUEUE_IMPORTS and (item[6] and reachable or item[2] in dependencies or item[2] in dependency_result.frontier_imports)]
    _prime_local_module_sources(root, diff, {item[0] for item in relevant}, side, cache, source_roots[:MAX_QUEUE_SOURCE_ROOTS], MAX_QUEUE_ADAPTER_MODULES - len(seen))
    for target_module, target_name, local_name, access_name, level, whole_module, wildcard in normalized:
            if target_module.split(".")[0] in _QUEUE_IMPORTS or not (wildcard and reachable or local_name in dependencies or local_name in dependency_result.frontier_imports):
                continue
            queue_adjacent = _queue_adjacent_module(target_module)
            frontier_reachable = local_name in dependency_result.frontier_imports
            if len(source_roots) > MAX_QUEUE_SOURCE_ROOTS and (queue_adjacent or frontier_reachable):
                proven.add(local_name)
                unsupported = True
                continue
            bounded_source_roots = source_roots[:MAX_QUEUE_SOURCE_ROOTS]
            resolution = _local_queue_resolution(
                root,
                diff,
                target_module,
                side,
                cache,
                active,
                seen,
                bounded_source_roots,
            )
            if target_name and not wildcard and target_name not in resolution.declared_exports and _is_local_package(cache, target_module):
                target_module, target_name, whole_module = f"{target_module}.{target_name}", "", True
                _prime_local_module_sources(root, diff, {target_module}, side, cache, bounded_source_roots, MAX_QUEUE_ADAPTER_MODULES - len(seen))
                resolution = _local_queue_resolution(root, diff, target_module, side, cache, active, seen, bounded_source_roots)
                queue_adjacent = _queue_adjacent_module(target_module)
            export_resolved = (
                (target_name and target_name in resolution.exports)
                or (not target_name and bool(resolution.exports))
            )
            local_values = tuple(sorted(reachable & set(resolution.exports))) if wildcard else (local_name,)
            if whole_module and resolution.reason in {"local_queue_provenance_resolved", "local_module_not_queue"}:
                proven.update(f"{access_name}.{export}" for export in resolution.exports)
                unsupported = unsupported or bool(resolution.exports)
                continue
            if (frontier_reachable or whole_module or wildcard) and (
                level > 0
                or resolution.reason != "local_module_missing"
                or any(name == target_module.split(".", 1)[0] or name.startswith(target_module.split(".", 1)[0] + ".") for name in cache.modules)
            ):
                declared = resolution.reason == "local_module_not_queue" and (
                    whole_module or wildcard or target_name in resolution.declared_exports)
                if declared or wildcard and not local_values and (
                    resolution.reason == "local_queue_provenance_resolved"
                ):
                    continue
                proven.update(local_values or reachable)
                unsupported = True
                continue
            if (
                len(source_roots) > MAX_QUEUE_SOURCE_ROOTS
                and resolution.state == "resolved"
                and export_resolved
            ):
                proven.add(local_name)
                unsupported = True
                continue
            if resolution.state == "unsupported" and export_resolved:
                proven.add(local_name)
                unsupported = True
                continue
            if (
                resolution.state == "unsupported"
                and queue_adjacent
            ):
                raise ArchitectureError(
                    f"relevant local queue adapter is unsupported: {target_module}"
                    f" ({resolution.reason})",
                    code="fitness",
                )
            if (
                not resolution.exports
                and queue_adjacent
                and (
                    level > 0
                    or any(name == target_module.split(".", 1)[0] or name.startswith(target_module.split(".", 1)[0] + ".") for name in cache.modules)
                )
                and resolution.reason == "local_module_missing"
            ):
                raise ArchitectureError(
                    f"relevant local queue adapter is unresolved: {target_module}",
                    code="fitness",
                )
            if (
                target_name
                and target_name not in resolution.exports
                and resolution.state == "resolved"
                and queue_adjacent
            ):
                raise ArchitectureError(
                    f"relevant local queue adapter export is unresolved: "
                    f"{target_module}.{target_name}",
                    code="fitness",
                )
            if (
                target_name and target_name in resolution.exports
            ) or (not target_name and resolution.exports):
                proven.add(local_name)
    return _QueueAdapterNamesResult(frozenset(proven), unsupported)


def _queue_signals(
    root: Path,
    diff: ArchitectureDiff,
    tree: ast.AST,
    side: str,
    cache: _QueueResolutionCache,
    current_package: str,
    source_roots: tuple[str, ...],
) -> _QueueProvenanceResult:
    adapters = _queue_adapter_names(
        root,
        diff,
        tree,
        side,
        cache,
        current_package=current_package,
        source_roots=source_roots,
    )
    try:
        analysis = analyze_queue_tree(tree, adapters.names)
    except QueueAnalysisLimit as exc:
        raise ArchitectureError(str(exc), code="limit") from exc
    unresolved = bool((adapters.unsupported or analysis.uncertain) and analysis.signals)
    return _QueueProvenanceResult(
        "unsupported" if unresolved else ("resolved" if analysis.signals else "not_queue"),
        "queue_provenance_unresolved" if unresolved else ("queue_signals_resolved" if analysis.signals else "no_queue_signal"),
        analysis.signals)


def _new_queue_sources(
    root: Path,
    diff: ArchitectureDiff,
    python: _PythonInventory,
    source_roots: tuple[str, ...],
) -> _QueueProvenanceResult:
    applicable: list[str] = []
    unsupported: list[str] = []
    changed_signals: set[str] = set()
    head_cache = _queue_module_inventory(root, diff, "head", source_roots)
    base_cache = _queue_module_inventory(root, diff, "base", source_roots)
    for path in _python_paths(diff):
        try:
            current_package = _module_package(path, source_roots)
            head = _queue_signals(
                root,
                diff,
                python.tree(path),
                "head",
                head_cache,
                current_package,
                source_roots,
            )
            base_value = read_diff_file(root, diff, path, "base")
            base = _QueueProvenanceResult("not_queue", "no_base_source", ())
            if base_value is not None:
                base_tree = ast.parse(base_value.decode("utf-8"), filename=path)
                if sum(1 for _ in ast.walk(base_tree)) > MAX_ANALYZED_AST_NODES:
                    raise ArchitectureError(f"Python AST node limit exceeded: {path}", code="limit")
                base = _queue_signals(
                    root,
                    diff,
                    base_tree,
                    "base",
                    base_cache,
                    current_package,
                    source_roots,
                )
            delta = set(head.signals) - set(base.signals)
            if delta:
                changed_signals.update(f"{path}:{signal}" for signal in delta)
                if head.state == "unsupported":
                    unsupported.append(path)
                else:
                    applicable.append(path)
        except ArchitectureError as exc:
            unsupported.append(path)
            changed_signals.add(f"{path}:unsupported:{exc.code}")
        except (SyntaxError, UnicodeDecodeError):
            value = read_diff_file(root, diff, path, "head") or b""
            if re.search(
                rb"\b(celery|rq|redis|kombu|pika|kafka|confluent_kafka|enqueue|apply_async|send_task)\b",
                value,
            ):
                unsupported.append(path)
                changed_signals.add(f"{path}:unsupported:syntax")
    if unsupported:
        return _QueueProvenanceResult(
            "unsupported",
            "queue_provenance_unresolved",
            tuple(sorted(changed_signals)),
            tuple(sorted(set((*applicable, *unsupported)))),
        )
    if applicable:
        return _QueueProvenanceResult(
            "resolved",
            "new_queue_signal",
            tuple(sorted(changed_signals)),
            tuple(sorted(set(applicable))),
        )
    return _QueueProvenanceResult("not_queue", "no_queue_signal", ())


def _background_jobs(
    root: Path,
    snapshot: ArchitectureSnapshot,
    diff: ArchitectureDiff,
    python: _PythonInventory,
    queue_provenance: _QueueProvenanceResult,
) -> FitnessResult:
    rules = snapshot.rules["background_job_policies"]
    predicate = "declared background edges and exact changed-source queue signals are governed"
    source_scope = queue_provenance.paths
    if not rules:
        if source_scope:
            return _result(
                "background_job",
                status="unsupported",
                findings=(
                    f"unsupported changed-source background job semantics: {path}"
                    for path in source_scope
                ),
                predicate=predicate,
                scope=source_scope,
                reason="source_signal_without_policy",
            )
        return _not_applicable("background_job", predicate, (), "no_declared_rules")
    if not _model_changed(diff) and not source_scope:
        return _not_applicable(
            "background_job", predicate, _python_paths(diff), "no_background_signal", (rule["id"] for rule in rules)
        )
    nodes = {node["id"]: node for node in snapshot.system["nodes"]}
    findings: list[str] = []
    scope: list[str] = []
    if source_scope:
        scope.extend(source_scope)
        findings.extend(
            f"unsupported changed-source background job semantics: {path}"
            for path in source_scope
        )
    for rule in rules:
        for edge in snapshot.system["edges"]:
            node = nodes[edge["from"]]
            if node["type"] not in rule["node_types"] or edge["sync_or_async"] == "synchronous":
                continue
            scope.append(edge["id"])
            behavior = edge["failure_behavior"]
            if behavior["max_retries"] > rule["max_retries"]:
                findings.append(f"{rule['id']}: {edge['id']} exceeds bounded retries")
            if (
                rule["require_idempotency"]
                and behavior["max_retries"] > 0
                and behavior["idempotency"] != "required"
            ):
                findings.append(f"{rule['id']}: {edge['id']} lacks retry idempotency")
            if rule["require_correlation_id"] and behavior["correlation_id"] != "required":
                findings.append(f"{rule['id']}: {edge['id']} lacks correlation id")
            if behavior["terminal_action"] not in rule["terminal_actions"]:
                findings.append(f"{rule['id']}: {edge['id']} has unsupported terminal action")
            if not behavior["observable_signal"]:
                findings.append(f"{rule['id']}: {edge['id']} lacks observable failure")
    if not scope:
        return _not_applicable(
            "background_job", predicate, (), "no_background_edge", (rule["id"] for rule in rules)
        )
    return _result(
        "background_job",
        status="unsupported" if source_scope else ("fail" if findings else "pass"),
        rules=(rule["id"] for rule in rules),
        findings=findings,
        predicate=predicate,
        scope=scope,
        reason=queue_provenance.reason if source_scope else "applicable",
    )


def _secret_flows(snapshot: ArchitectureSnapshot, diff: ArchitectureDiff) -> FitnessResult:
    rules = snapshot.rules["secret_flow_policies"]
    predicate = "declared secret classes are held or flow across architecture trust domains"
    if not rules:
        return _not_applicable("secret_flow", predicate, (), "no_declared_rules")
    if not _model_changed(diff):
        return _not_applicable(
            "secret_flow", predicate, (), "architecture_unchanged", (rule["id"] for rule in rules)
        )
    nodes = {node["id"]: node for node in snapshot.system["nodes"]}
    findings: list[str] = []
    scope: list[str] = []
    for rule in rules:
        secrets = set(rule["secret_classes"])
        allowed = set(rule["allowed_trust_domains"])
        for node in nodes.values():
            if secrets & set(node["secrets"]):
                scope.append(node["id"])
                if node["trust_domain"] not in allowed:
                    findings.append(f"{rule['id']}: secret held by untrusted node {node['id']}")
        for edge in snapshot.system["edges"]:
            if edge["type"] == "secret_flow":
                scope.append(edge["id"])
                if nodes[edge["from"]]["trust_domain"] not in allowed or nodes[edge["to"]]["trust_domain"] not in allowed:
                    findings.append(f"{rule['id']}: secret flow crosses untrusted edge {edge['id']}")
    if not scope:
        return _not_applicable(
            "secret_flow", predicate, (), "no_governed_secret_subject", (rule["id"] for rule in rules)
        )
    return _result(
        "secret_flow",
        status="fail" if findings else "pass",
        rules=(rule["id"] for rule in rules),
        findings=findings,
        predicate=predicate,
        scope=scope,
    )


def _workspace_trust(snapshot: ArchitectureSnapshot, diff: ArchitectureDiff) -> FitnessResult:
    rules = snapshot.rules["workspace_trust_policies"]
    predicate = "repository/runner nodes are checked for forbidden trust material"
    if not rules:
        return _not_applicable("workspace_trust", predicate, (), "no_declared_rules")
    if not _model_changed(diff):
        return _not_applicable(
            "workspace_trust", predicate, (), "architecture_unchanged", (rule["id"] for rule in rules)
        )
    findings: list[str] = []
    scope: list[str] = []
    for rule in rules:
        for node in snapshot.system["nodes"]:
            if node["type"] not in rule["node_types"]:
                continue
            scope.append(node["id"])
            forbidden = set(node["secrets"]) & set(rule["forbidden_secret_classes"])
            if forbidden:
                findings.append(
                    f"{rule['id']}: {node['id']} exposes forbidden secrets {','.join(sorted(forbidden))}"
                )
    return _result(
        "workspace_trust",
        status="fail" if findings else "pass",
        rules=(rule["id"] for rule in rules),
        findings=findings,
        predicate=predicate,
        scope=scope,
    )


def _risk_triggers(snapshot: ArchitectureSnapshot, diff: ArchitectureDiff) -> tuple[str, ...]:
    triggers: set[str] = set()
    before_nodes = {
        node["id"]: node for node in (diff._base_state.snapshot.system["nodes"] if diff._base_state else [])
    }
    after_nodes = {node["id"]: node for node in snapshot.system["nodes"]}
    for change in diff.changes:
        if change.change != "added" and change.kind not in {"node", "runtime"}:
            continue
        if change.kind == "edge" and change.change == "added":
            triggers.add("new_edge")
        elif change.kind == "contract" and change.change == "added":
            triggers.add("new_contract")
        elif change.kind == "secret" and change.change == "added":
            triggers.add("new_secret")
    for identity, node in after_nodes.items():
        old = before_nodes.get(identity)
        if old is None or old["type"] != node["type"]:
            mapping = {
                "datastore": "new_datastore",
                "external_system": "new_external_integration",
                "runner": "new_job",
                "service": "new_service",
                "worker": "new_job",
            }
            if node["type"] in mapping:
                triggers.add(mapping[node["type"]])
        if old is None or set(node["secrets"]) - set(old["secrets"]):
            if node["secrets"]:
                triggers.add("new_secret")
    nodes = after_nodes
    for change in diff.changes:
        if change.kind == "edge" and change.change == "added":
            edge = next(item for item in snapshot.system["edges"] if item["id"] == change.id)
            if nodes[edge["from"]]["trust_domain"] != nodes[edge["to"]]["trust_domain"]:
                triggers.add("new_trust_crossing")
    for artifact in diff.artifacts:
        name = Path(artifact.path).name.lower()
        if artifact.status == "added" and name in {
            "package.json",
            "pyproject.toml",
            "requirements.txt",
            "go.mod",
            "cargo.toml",
        }:
            triggers.add("new_framework")
    return tuple(sorted(triggers))


def _new_import_family(
    root: Path,
    diff: ArchitectureDiff,
    python: _PythonInventory,
    families: set[str],
) -> bool:
    for path in _python_paths(diff):
        try:
            head_imports = {name.split(".")[0] for name in _imports(python.tree(path))}
            base_value = read_diff_file(root, diff, path, "base")
            base_imports = set()
            if base_value is not None:
                base_tree = ast.parse(base_value.decode("utf-8"), filename=path)
                base_imports = {name.split(".")[0] for name in _imports(base_tree)}
            if (head_imports - base_imports) & families:
                return True
        except (SyntaxError, UnicodeDecodeError):
            continue
    return False


def _network_families(tree: ast.AST, project_roots: set[str]) -> set[str]:
    values = {
        imported for imported in _import_targets(tree) if _network_protocol(imported) is not None
    }
    for imported, call in _called_imports(tree):
        protocol = _http_client_protocol(imported, call)
        if protocol is not None:
            values.add(f"http.client:{protocol}")
        elif _network_protocol(imported) is not None:
            values.add(imported)
        elif _network_call_is_applicable(imported, call, project_roots):
            values.add(f"unsupported:{call}")
    return values


def _new_network_client(
    root: Path,
    snapshot: ArchitectureSnapshot,
    diff: ArchitectureDiff,
    python: _PythonInventory,
) -> bool:
    project_roots = _project_import_roots(snapshot, diff, root)
    for path in _python_paths(diff):
        try:
            head = _network_families(python.tree(path), project_roots)
            base_value = read_diff_file(root, diff, path, "base")
            base = set() if base_value is None else _network_families(
                ast.parse(base_value.decode("utf-8"), filename=path), project_roots
            )
            if head - base:
                return True
        except (SyntaxError, UnicodeDecodeError):
            continue
    return False


def _risk(
    root: Path,
    snapshot: ArchitectureSnapshot,
    diff: ArchitectureDiff,
    python: _PythonInventory,
    pre_risk: str,
    queue_provenance: _QueueProvenanceResult,
) -> tuple[str, str, tuple[str, ...]]:
    if pre_risk not in RISK_ORDER:
        raise ArchitectureError("pre_risk must be green, yellow, or red", code="risk")
    triggers = set(_risk_triggers(snapshot, diff))
    if queue_provenance.state != "not_queue":
        triggers.add("new_queue")
    if _new_network_client(root, snapshot, diff, python):
        triggers.add("new_network_client")
    if _new_import_family(root, diff, python, _FRAMEWORK_IMPORTS):
        triggers.add("new_framework")
    escalation = "green"
    for rule in snapshot.rules["risk_escalations"]:
        if triggers & set(rule["triggers"]) and RISK_ORDER[rule["risk"]] > RISK_ORDER[escalation]:
            escalation = rule["risk"]
    post = max((pre_risk, escalation), key=RISK_ORDER.__getitem__)
    return escalation, post, tuple(sorted(triggers))


def _result_payload(result: FitnessResult) -> dict[str, Any]:
    return {
        "category": result.category,
        "status": result.status,
        "rule_ids": result.rule_ids,
        "findings": result.findings,
        "applicability": {
            "predicate": result.applicability.predicate,
            "scanned_scope": result.applicability.scanned_scope,
            "reason_code": result.applicability.reason_code,
            "inventory_digest": result.applicability.inventory_digest,
        },
    }


_CATEGORY_RULES = {
    "background_job": "background_job_policies",
    "change_separation": "change_separation_policies",
    "code_budget": "code_budgets",
    "contract_compatibility": "contract_policies",
    "forbidden_edge": "forbidden_edges",
    "migration_safety": "migration_policies",
    "module_boundary": "path_boundaries",
    "network_client": "network_policies",
    "tenant_authorization": "tenant_authorization_policies",
    "workspace_trust": "workspace_trust_policies",
}


def _bind_applicability_inventory(
    root: Path,
    snapshot: ArchitectureSnapshot,
    diff: ArchitectureDiff,
    result: FitnessResult,
) -> FitnessResult:
    collection = (
        "secret_flow_policies"
        if result.category == "secret_flow"
        else _CATEGORY_RULES.get(result.category)
    )
    rules = [] if collection is None else snapshot.rules[collection]
    scope = set(result.applicability.scanned_scope)
    scope.update(rule["id"] for rule in rules)
    for rule in rules:
        for key, value in rule.items():
            if key.endswith("prefixes") and isinstance(value, list):
                scope.update(item for item in value if isinstance(item, str))
    if result.category == "contract_compatibility":
        scope.update(record.id for record in diff._head_state.contracts)
    model_ids = {
        item["id"]
        for collection_name in (
            "trust_domains", "data_classifications", "secret_classes", "nodes", "edges", "signals"
        )
        for item in snapshot.system[collection_name]
    }
    payload = {
        "category": result.category,
        "predicate": result.applicability.predicate,
        "reason_code": result.applicability.reason_code,
        "scanned_scope": tuple(sorted(scope)),
        "repository_inventory_digest": diff.repository_inventory_digest,
        "architecture_digest": diff.head_architecture_digest,
        "model_ids": tuple(sorted(model_ids)),
        "rules": rules,
        "contracts": [
            {
                "id": record.id,
                "kind": record.kind,
                "path": record.path,
                "version": record.version,
                "role": record.role,
                "compatibility": record.compatibility,
                "document_digest": record.digest,
            }
            for record in diff._head_state.contracts
        ] if result.category == "contract_compatibility" else [],
    }
    return replace(
        result,
        applicability=replace(
            result.applicability,
            scanned_scope=tuple(sorted(scope)),
            inventory_digest=_digest(payload),
        ),
    )


def evaluate_fitness(
    root: Path | str,
    snapshot: ArchitectureSnapshot,
    diff: ArchitectureDiff,
    changed_paths: Iterable[str],
    *,
    pre_risk: str,
) -> FitnessReport:
    repository = Path(root).resolve(strict=True)
    supplied_paths = tuple(sorted(set(changed_paths)))
    if supplied_paths != diff.changed_paths:
        raise ArchitectureError("changed_paths must exactly match the architecture diff", code="fitness")
    if architecture_digests(snapshot)["architecture_digest"] != diff.head_architecture_digest:
        raise ArchitectureError("fitness snapshot does not match the diff head", code="fitness")
    python = _PythonInventory(repository, diff)
    queue_provenance = _new_queue_sources(
        repository, diff, python, _queue_source_roots(snapshot)
    )
    raw_results = tuple(
        sorted(
            (
                _background_jobs(
                    repository, snapshot, diff, python, queue_provenance
                ),
                _change_separation(snapshot, diff),
                _code_budget(snapshot, diff, python),
                _contract_compatibility(snapshot, diff),
                _forbidden_edges(snapshot, diff),
                _governance_promotion(repository, diff),
                _migration_safety(repository, snapshot, diff),
                _module_boundaries(snapshot, diff, python),
                _network_clients(snapshot, diff, python),
                _production_imports(diff, python),
                _secret_flows(snapshot, diff),
                _tenant_authorization(snapshot, diff),
                _workspace_trust(snapshot, diff),
            ),
            key=lambda item: item.category,
        )
    )
    results = tuple(
        _bind_applicability_inventory(repository, snapshot, diff, result)
        for result in raw_results
    )
    if tuple(item.category for item in results) != FITNESS_CATEGORIES:
        raise ArchitectureError("mandatory fitness category coverage is incomplete", code="fitness")
    escalation, post_risk, triggers = _risk(
        repository, snapshot, diff, python, pre_risk, queue_provenance
    )
    architecture_significant = diff.baseline_introduced or bool(diff.changes or triggers)
    docs_only = bool(diff.changed_paths) and all(
        _matches(path, ("docs",)) or path.endswith(".md") for path in diff.changed_paths
    )
    exemption_state = "eligible" if docs_only and not architecture_significant else "revoked"
    scopes = set()
    trigger_set = set(triggers)
    if architecture_significant:
        scopes.add("architecture")
    if trigger_set & {"new_network_client", "new_secret", "new_trust_crossing"}:
        scopes.add("security")
    if trigger_set & {"new_datastore"} or any(
        item.category == "migration_safety" and item.status != "not_applicable" for item in results
    ):
        scopes.add("data")
    if trigger_set & {"new_contract"}:
        scopes.add("contract")
    overall = "fail" if any(item.status in {"fail", "unsupported"} for item in results) else "pass"
    payload = {
        "results": [_result_payload(item) for item in results],
        "status": overall,
        "pre_risk": pre_risk,
        "escalation": escalation,
        "post_risk": post_risk,
        "triggers": triggers,
        "exemption_state": exemption_state,
        "required_scopes": tuple(sorted(scopes)),
    }
    return FitnessReport(
        results=results,
        status=overall,
        pre_risk=pre_risk,
        escalation=escalation,
        post_risk=post_risk,
        triggers=triggers,
        exemption_state=exemption_state,
        required_scopes=tuple(sorted(scopes)),
        evidence_digest=_digest(payload),
    )


def architecture_evidence(
    root: Path | str,
    *,
    base_sha: str,
    head_sha: str,
    pre_risk: str,
) -> dict[str, Any]:
    repository = Path(root).resolve(strict=True)
    diff = diff_architecture(repository, base_sha=base_sha, head_sha=head_sha)
    snapshot = diff._head_state.snapshot
    report = evaluate_fitness(
        repository, snapshot, diff, diff.changed_paths, pre_risk=pre_risk
    )
    digests = architecture_digests(snapshot)
    core: dict[str, Any] = {
        "architecture_contract_version": 1,
        "architecture_digest": digests["architecture_digest"],
        "schema_digest": digests["schema_digest"],
        "system_digest": digests["system_digest"],
        "rules_digest": digests["rules_digest"],
        "contract_inventory_digest": contract_inventory_digest(diff._head_state.contracts),
        "repository_inventory_digest": diff.repository_inventory_digest,
        "diff_digest": diff.digest,
        "exact_base_sha": diff.base_sha,
        "exact_head_sha": diff.head_sha,
        "head_kind": diff.head_kind,
        "baseline_introduced": diff.baseline_introduced,
        "base_adoption_state": diff.base_adoption_state,
        "head_adoption_state": diff.head_adoption_state,
        "base_adoption_digest": diff.base_adoption_digest,
        "head_adoption_digest": diff.head_adoption_digest,
        "fitness_results": [_result_payload(item) for item in report.results],
        "fitness_status": report.status,
        "risk_pre": report.pre_risk,
        "risk_escalation": report.escalation,
        "risk_post": report.post_risk,
        "risk_triggers": report.triggers,
        "exemption_state": report.exemption_state,
        "required_scopes": report.required_scopes,
        "overall_status": report.status,
    }
    core["architecture_evidence_digest"] = _digest(core)
    return core


__all__ = [
    "ADOPTION_BASE_SHA",
    "ApplicabilityEvidence",
    "ArchitectureChange",
    "ArchitectureDiff",
    "ArchitectureError",
    "ChangedArtifact",
    "FitnessReport",
    "FitnessResult",
    "architecture_evidence",
    "diff_architecture",
    "evaluate_fitness",
    "load_architecture",
]
