from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

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
)

FITNESS_CATEGORIES = (
    "background_job",
    "change_separation",
    "code_budget",
    "contract_compatibility",
    "forbidden_edge",
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
_PYTHON_SUFFIXES = {".py", ".pyi"}
_NETWORK_IMPORTS = {
    "aiohttp": "https",
    "docker": "docker_api",
    "ftplib": "ftp",
    "http.client": "https",
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
_AUTHORIZATION_EDGE_TYPES = {"control", "data_flow", "dependency", "publication"}
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


@dataclass(frozen=True)
class _QueueProvenanceResult:
    state: str
    reason: str
    signals: tuple[str, ...]
    paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class _QueueAdapterResolution:
    state: str
    reason: str
    exports: tuple[str, ...] = ()
    signals: tuple[str, ...] = ()


@dataclass(frozen=True)
class _QueueAdapterNamesResult:
    names: frozenset[str]
    unsupported: bool = False


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
            continue
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


def _migration_paths(root: Path, diff: ArchitectureDiff, prefixes: tuple[str, ...]) -> tuple[str, ...]:
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
    match = _MIGRATION_PHASE.fullmatch(Path(path).stem.lower())
    return None if match is None else (match.group("group"), match.group("phase"))


def _migration_mirrors(
    snapshot: ArchitectureSnapshot, prefix: str
) -> tuple[str, ...]:
    roots: set[str] = set()
    for node in snapshot.system["nodes"]:
        paths = node["repository_paths"]
        if prefix not in paths:
            continue
        roots.update(
            path
            for path in paths
            if path != prefix and Path(path).name.lower() in {"resources", "migrations"}
        )
    return tuple(sorted(roots))


def _migration_version(group: str) -> int | None:
    match = re.match(r"^(?:v)?(?P<version>[0-9]+)(?:[_-].*)?$", group)
    return None if match is None else int(match.group("version"))


def _bounded_migrate_predicate(statement: str) -> bool:
    where = re.search(r"\bWHERE\b(?P<predicate>.*?)(?:\bRETURNING\b|$)", statement)
    if where is None:
        return False
    predicate = where.group("predicate")
    identifier = r"[A-Z_][A-Z0-9_.]*"
    operand = r"(?:\?|\$[0-9]+|%S|:[A-Z_][A-Z0-9_]*|[-+]?[0-9]+)"
    if re.fullmatch(
        rf"\s*(?P<column>{identifier})\s+BETWEEN\s+{operand}\s+AND\s+{operand}\s*",
        predicate,
    ):
        return True
    return bool(
        re.fullmatch(
            rf"\s*(?P<column>{identifier})\s*(?:>=|>)\s*{operand}\s+AND\s+"
            rf"(?P=column)\s*(?:<=|<)\s*{operand}\s*",
            predicate,
        )
        or re.fullmatch(
            rf"\s*(?P<column>{identifier})\s*(?:<=|<)\s*{operand}\s+AND\s+"
            rf"(?P=column)\s*(?:>=|>)\s*{operand}\s*",
            predicate,
        )
    )


def _migration_source_findings(
    rule_id: str, path: str, phase: str, source: str
) -> tuple[list[str], list[str]]:
    findings: list[str] = []
    unsupported: list[str] = []
    statements = [
        statement.strip()
        for statement in re.split(r";", re.sub(r"--[^\n]*", "", source))
        if statement.strip()
    ]
    if not statements:
        unsupported.append(f"{rule_id}: migration contains no analyzable SQL: {path}")
        return findings, unsupported
    for statement in statements:
        normalized = " ".join(statement.upper().split())
        destructive = bool(
            re.search(r"\b(DROP|TRUNCATE)\b|\bALTER TABLE\b.*\bDROP\b", normalized)
        )
        if destructive and phase != "contract":
            findings.append(f"{rule_id}: destructive SQL outside contract phase: {path}")
            continue
        if phase == "expand":
            if re.search(r"\bNOT NULL\b", normalized):
                findings.append(f"{rule_id}: NOT NULL is unsafe in expand phase: {path}")
            elif not re.match(
                r"^(CREATE TABLE|CREATE (UNIQUE )?INDEX CONCURRENTLY|ALTER TABLE .* ADD )",
                normalized,
            ):
                unsupported.append(f"{rule_id}: unsupported expand SQL semantics: {path}")
        elif phase == "migrate":
            if re.match(r"^(UPDATE|DELETE)\b", normalized):
                if re.search(r"\bWHERE\b.*(?:\b1\s*=\s*1\b|\bTRUE\b)", normalized) or not re.search(
                    r"\bWHERE\b", normalized
                ):
                    findings.append(
                        f"{rule_id}: unbounded {normalized.split()[0]} in migrate phase: {path}"
                    )
                elif not _bounded_migrate_predicate(normalized):
                    unsupported.append(
                        f"{rule_id}: migrate bounded/resumable predicate is unproven: {path}"
                    )
            elif re.match(r"^INSERT\b", normalized):
                unsupported.append(f"{rule_id}: unsupported bounded INSERT semantics: {path}")
            else:
                unsupported.append(f"{rule_id}: unsupported migrate SQL semantics: {path}")
        elif phase == "contract":
            if re.match(r"^ALTER TABLE\b.*\bADD\b", normalized):
                findings.append(f"{rule_id}: expansive SQL in contract phase: {path}")
            elif not re.match(r"^(ALTER TABLE .* DROP|DROP|TRUNCATE)\b", normalized):
                unsupported.append(f"{rule_id}: unsupported contract SQL semantics: {path}")
        else:  # pragma: no cover - phase comes from the closed regex
            unsupported.append(f"{rule_id}: unsupported migration phase: {path}")
    return findings, unsupported


def _migration_safety(root: Path, snapshot: ArchitectureSnapshot, diff: ArchitectureDiff) -> FitnessResult:
    rules = snapshot.rules["migration_policies"]
    predicate = "changed SQL paths match a declared migration-history prefix"
    if not rules:
        return _not_applicable("migration_safety", predicate, (), "no_declared_rules")
    applicable = tuple(
        artifact
        for artifact in diff.artifacts
        if Path(artifact.path).suffix.lower() == ".sql"
        and any(_matches(artifact.path, rule["path_prefixes"]) for rule in rules)
    )
    if not applicable:
        return _not_applicable(
            "migration_safety", predicate, (), "no_matching_sql_change", (rule["id"] for rule in rules)
        )
    findings: list[str] = []
    unsupported: list[str] = []
    for rule in rules:
        relevant = [item for item in applicable if _matches(item.path, rule["path_prefixes"])]
        if rule["immutable_history"]:
            for item in relevant:
                if item.status in {"modified", "deleted"}:
                    findings.append(f"{rule['id']}: immutable migration history changed: {item.path}")
        head_paths = _migration_paths(root, diff, tuple(rule["path_prefixes"]))
        phases: dict[str, set[str]] = {}
        version_groups: dict[int, set[str]] = {}
        phase_paths: dict[tuple[int, str, str], list[str]] = {}
        for path in head_paths:
            parsed = _migration_phase(path)
            if parsed:
                phases.setdefault(parsed[0], set()).add(parsed[1])
                version = _migration_version(parsed[0])
                if version is None:
                    unsupported.append(f"{rule['id']}: migration version cannot be derived: {path}")
                else:
                    version_groups.setdefault(version, set()).add(parsed[0])
                    phase_paths.setdefault((version, parsed[0], parsed[1]), []).append(path)
        for (version, group, phase), paths in phase_paths.items():
            if len(paths) > 1:
                findings.append(
                    f"{rule['id']}: duplicate migration artifact for "
                    f"{version}/{group}/{phase}: {','.join(sorted(paths))}"
                )
        for version, groups in version_groups.items():
            if len(groups) > 1:
                findings.append(
                    f"{rule['id']}: duplicate migration version {version}: {','.join(sorted(groups))}"
                )
        versions = set(version_groups)
        if versions and versions != set(range(1, max(versions) + 1)):
            findings.append(f"{rule['id']}: migration version history is not contiguous")
        for item in relevant:
            if item.status == "deleted":
                findings.append(f"{rule['id']}: migration history removed: {item.path}")
                continue
            parsed = _migration_phase(item.path)
            if parsed is None:
                unsupported.append(f"{rule['id']}: migration phase cannot be derived: {item.path}")
                continue
            missing = sorted(set(rule["required_phases"]) - phases.get(parsed[0], set()))
            if missing:
                findings.append(
                    f"{rule['id']}: migration {parsed[0]} missing phases: {','.join(missing)}"
                )
            value = read_diff_file(root, diff, item.path)
            if value is None:
                unsupported.append(f"{rule['id']}: migration source unavailable: {item.path}")
                continue
            try:
                source = value.decode("utf-8")
            except UnicodeDecodeError:
                unsupported.append(f"{rule['id']}: migration is not UTF-8: {item.path}")
                continue
            source_findings, source_unsupported = _migration_source_findings(
                rule["id"], item.path, parsed[1], source
            )
            findings.extend(source_findings)
            unsupported.extend(source_unsupported)
            for prefix in rule["path_prefixes"]:
                if not _matches(item.path, (prefix,)):
                    continue
                relative = item.path[len(prefix) :].lstrip("/")
                for mirror_root in _migration_mirrors(snapshot, prefix):
                    mirror = f"{mirror_root}/{relative}"
                    mirror_value = read_diff_file(root, diff, mirror)
                    if mirror_value is None:
                        findings.append(f"{rule['id']}: migration mirror missing: {mirror}")
                    elif mirror_value != value:
                        findings.append(f"{rule['id']}: migration mirror differs: {mirror}")
    status = "unsupported" if unsupported else ("fail" if findings else "pass")
    return _result(
        "migration_safety",
        status=status,
        rules=(rule["id"] for rule in rules),
        findings=(*findings, *unsupported),
        predicate=predicate,
        scope=(item.path for item in applicable),
        reason="unsupported_migration_semantics" if unsupported else "applicable",
    )


def _tenant_authorization(snapshot: ArchitectureSnapshot, diff: ArchitectureDiff) -> FitnessResult:
    rules = snapshot.rules["tenant_authorization_policies"]
    predicate = "restricted declared data crosses a changed architecture edge"
    if not rules:
        return _not_applicable("tenant_authorization", predicate, (), "no_declared_rules")
    if not _model_changed(diff):
        return _not_applicable(
            "tenant_authorization", predicate, (), "architecture_unchanged", (rule["id"] for rule in rules)
        )
    findings: list[str] = []
    unsupported: list[str] = []
    scope: list[str] = []
    for rule in rules:
        for edge in snapshot.system["edges"]:
            if (
                edge["type"] in _AUTHORIZATION_EDGE_TYPES
                and set(edge["allowed_data"]) & set(rule["data_classifications"])
            ):
                scope.append(edge["id"])
                if rule["require_authorization"] and edge["authentication"] == "none":
                    findings.append(f"{rule['id']}: unauthenticated restricted edge {edge['id']}")
                if rule["require_tenant_filter"]:
                    unsupported.append(f"{rule['id']}: model v1 has no tenant-filter edge field")
    if not scope:
        return _not_applicable(
            "tenant_authorization", predicate, (), "no_restricted_data_edge", (rule["id"] for rule in rules)
        )
    status = "unsupported" if unsupported else ("fail" if findings else "pass")
    return _result(
        "tenant_authorization",
        status=status,
        rules=(rule["id"] for rule in rules),
        findings=(*findings, *unsupported),
        predicate=predicate,
        scope=scope,
        reason="unsupported_tenant_semantics" if unsupported else "applicable",
    )


def _owner_for_path(snapshot: ArchitectureSnapshot, path: str) -> dict[str, Any] | None:
    matches = [
        (len(repository_path), node)
        for node in snapshot.system["nodes"]
        for repository_path in node["repository_paths"]
        if _matches(path, (repository_path,))
    ]
    return None if not matches else max(matches, key=lambda item: item[0])[1]


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
    paths = _migration_paths(root, diff, prefixes) if prefixes else ()
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
        changed_lines = sum((item.added_lines or 0) + (item.deleted_lines or 0) for item in artifacts)
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


def _queue_provenance(
    tree: ast.AST,
    adapter_names: set[str] | None = None,
) -> tuple[set[str], set[str]]:
    queue_names = set(adapter_names or ())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                if alias.name.split(".")[0] in _QUEUE_IMPORTS:
                    queue_names.add(local)
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                local = alias.asname or alias.name
                if node.module.split(".")[0] in _QUEUE_IMPORTS:
                    queue_names.add(local)

    def queue_derived(value: ast.AST) -> bool:
        if isinstance(value, ast.Name):
            return value.id in queue_names
        if isinstance(value, ast.Attribute):
            return queue_derived(value.value)
        if isinstance(value, ast.Call):
            if queue_derived(value.func):
                return True
            return (
                isinstance(value.func, ast.Name)
                and value.func.id == "getattr"
                and bool(value.args)
                and queue_derived(value.args[0])
            )
        return False

    # Resolve simple assignment/factory chains to a fixed point. The global AST
    # node limit bounds both this loop and the values considered here.
    assignments = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
    ]
    for _ in range(min(len(assignments) + 1, 64)):
        changed = False
        for node in assignments:
            value = node.value
            if value is None or not queue_derived(value):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id not in queue_names:
                    queue_names.add(target.id)
                    changed = True
        if not changed:
            break

    signals = {
        f"import:{target}"
        for target in _import_targets(tree)
        if target.split(".")[0] in _QUEUE_IMPORTS
    }
    for imported, call in _called_imports(tree):
        if imported.split(".")[0] in _QUEUE_IMPORTS:
            signals.add(f"call:{call}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if queue_derived(node.func):
                signals.add(
                    "semantic-call:" + ast.dump(node, annotate_fields=True, include_attributes=False)
                )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if queue_derived(decorator):
                    signals.add(
                        f"semantic-decorator:{node.name}:"
                        + ast.dump(decorator, annotate_fields=True, include_attributes=False)
                    )
    return signals, queue_names


def _operation_dependencies(tree: ast.AST) -> set[str]:
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
    assignments: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assignments[node.target.id] = node.value
    for _ in range(min(len(assignments) + 1, 64)):
        expanded = set(dependencies)
        for name in dependencies:
            value = assignments.get(name)
            if value is not None:
                expanded.update(
                    child.id for child in ast.walk(value) if isinstance(child, ast.Name)
                )
        if expanded == dependencies:
            break
        dependencies = expanded
    return dependencies


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


def _module_package(path: str) -> str:
    module = path.rsplit(".", 1)[0].replace("/", ".")
    if module.endswith(".__init__"):
        return module.removesuffix(".__init__")
    return module.rsplit(".", 1)[0] if "." in module else ""


def _queue_adjacent_module(module: str) -> bool:
    tokens = {
        token
        for part in module.split(".")
        for token in re.split(r"[^A-Za-z0-9]+|_+", part.lower())
        if token
    }
    return bool(tokens & _QUEUE_ADAPTER_MODULE_TOKENS)


def _queue_source_roots(snapshot: ArchitectureSnapshot) -> tuple[str, ...]:
    roots = {""}
    file_suffixes = {
        ".json", ".md", ".py", ".pyi", ".sh", ".sql", ".toml", ".txt", ".yaml", ".yml"
    }
    for node in snapshot.system["nodes"]:
        for prefix in node["repository_paths"]:
            name = prefix.rsplit("/", 1)[-1]
            if Path(prefix).suffix.lower() not in file_suffixes:
                roots.add(prefix)
            if (
                "/" in prefix
                and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is not None
                and Path(prefix).suffix.lower() not in file_suffixes
            ):
                roots.add(prefix.rsplit("/", 1)[0])
    return tuple(sorted(roots))


def _source_root_path(source_root: str, relative: str) -> str:
    return f"{source_root}/{relative}" if source_root else relative


def _local_module_sources(
    root: Path,
    diff: ArchitectureDiff,
    module: str,
    side: str,
    source_roots: tuple[str, ...],
) -> tuple[tuple[str, bytes, str], ...]:
    relative = module.replace(".", "/")
    found: list[tuple[str, bytes, str]] = []
    for source_root in source_roots:
        module_path = _source_root_path(source_root, f"{relative}.py")
        module_value = read_diff_file(root, diff, module_path, side)
        if module_value is not None:
            package = module.rsplit(".", 1)[0] if "." in module else ""
            found.append((module_path, module_value, package))
        package_path = _source_root_path(source_root, f"{relative}/__init__.py")
        package_value = read_diff_file(root, diff, package_path, side)
        if package_value is not None:
            found.append((package_path, package_value, module))
    return tuple(found)


def _has_local_module_root(
    root: Path,
    diff: ArchitectureDiff,
    module: str,
    side: str,
    source_roots: tuple[str, ...],
) -> bool:
    root_name = module.split(".", 1)[0]
    return any(
        read_diff_file(root, diff, _source_root_path(source_root, candidate), side)
        is not None
        for source_root in source_roots
        for candidate in (f"{root_name}.py", f"{root_name}/__init__.py")
    )


def _local_queue_resolution(
    root: Path,
    diff: ArchitectureDiff,
    module: str,
    side: str,
    cache: dict[str, _QueueAdapterResolution],
    resolving: set[str],
    source_roots: tuple[str, ...],
) -> _QueueAdapterResolution:
    if module in cache:
        return cache[module]
    if (
        not module
        or any(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part) is None for part in module.split("."))
    ):
        return _QueueAdapterResolution("not_queue", "invalid_local_module")
    if len(cache) >= MAX_QUEUE_ADAPTER_MODULES:
        raise ArchitectureError("queue adapter module limit exceeded", code="limit")
    if len(resolving) >= MAX_QUEUE_ADAPTER_DEPTH:
        raise ArchitectureError("queue adapter depth limit exceeded", code="limit")
    if module in resolving:
        return _QueueAdapterResolution("unsupported", "cyclic_local_queue_adapter")
    resolving.add(module)
    try:
        sources = _local_module_sources(root, diff, module, side, source_roots)
        if len(sources) > 1:
            result = _QueueAdapterResolution(
                "unsupported", "ambiguous_local_queue_adapter"
            )
            cache[module] = result
            return result
        if not sources:
            result = _QueueAdapterResolution("not_queue", "local_module_missing")
            cache[module] = result
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
            current_package=current_package,
            source_roots=source_roots,
        )
        signals, derived = _queue_provenance(tree, set(imported.names))
        exports = tuple(sorted(name for name in derived if not name.startswith("_")))
        has_queue_provenance = bool(signals or exports)
        result = _QueueAdapterResolution(
            (
                "unsupported"
                if imported.unsupported and has_queue_provenance
                else ("resolved" if has_queue_provenance else "not_queue")
            ),
            (
                "local_queue_provenance_resolved"
                if has_queue_provenance
                else "local_module_not_queue"
            ),
            exports,
            tuple(sorted(signals)),
        )
        cache[module] = result
        return result
    finally:
        resolving.remove(module)


def _queue_adapter_names(
    root: Path,
    diff: ArchitectureDiff,
    tree: ast.AST,
    side: str,
    cache: dict[str, _QueueAdapterResolution],
    resolving: set[str] | None = None,
    *,
    current_package: str = "",
    source_roots: tuple[str, ...],
) -> _QueueAdapterNamesResult:
    proven: set[str] = set()
    unsupported = False
    active = resolving if resolving is not None else set()
    dependencies = _operation_dependencies(tree)
    if resolving is not None:
        dependencies.update(
            alias.asname or alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        )
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        candidates = [
            alias for alias in node.names if (alias.asname or alias.name) in dependencies
        ]
        if not candidates:
            continue
        module = _resolve_import_module(current_package, node.module, node.level)
        if module.split(".")[0] in _QUEUE_IMPORTS:
            continue
        for alias in candidates:
            target_module = module
            target_name = alias.name
            if node.module is None:
                target_module = f"{module}.{alias.name}" if module else alias.name
                target_name = ""
            queue_adjacent = _queue_adjacent_module(target_module)
            if len(source_roots) > MAX_QUEUE_SOURCE_ROOTS and queue_adjacent:
                proven.add(alias.asname or alias.name)
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
                bounded_source_roots,
            )
            export_resolved = (
                (target_name and target_name in resolution.exports)
                or (not target_name and bool(resolution.exports))
            )
            if (
                len(source_roots) > MAX_QUEUE_SOURCE_ROOTS
                and resolution.state == "resolved"
                and export_resolved
            ):
                proven.add(alias.asname or alias.name)
                unsupported = True
                continue
            if resolution.state == "unsupported" and export_resolved:
                proven.add(alias.asname or alias.name)
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
                    node.level > 0
                    or _has_local_module_root(
                        root, diff, target_module, side, bounded_source_roots
                    )
                )
                and not _local_module_sources(
                    root, diff, target_module, side, bounded_source_roots
                )
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
                proven.add(alias.asname or alias.name)
    return _QueueAdapterNamesResult(frozenset(proven), unsupported)


def _queue_signals(
    root: Path,
    diff: ArchitectureDiff,
    tree: ast.AST,
    side: str,
    cache: dict[str, _QueueAdapterResolution],
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
    signals = tuple(sorted(_queue_provenance(tree, set(adapters.names))[0]))
    return _QueueProvenanceResult(
        state=("unsupported" if adapters.unsupported and signals else (
            "resolved" if signals else "not_queue"
        )),
        reason=(
            "queue_provenance_unresolved"
            if adapters.unsupported and signals
            else ("queue_signals_resolved" if signals else "no_queue_signal")
        ),
        signals=signals,
    )


def _new_queue_sources(
    root: Path,
    diff: ArchitectureDiff,
    python: _PythonInventory,
    source_roots: tuple[str, ...],
) -> _QueueProvenanceResult:
    applicable: list[str] = []
    unsupported: list[str] = []
    changed_signals: set[str] = set()
    head_cache: dict[str, _QueueAdapterResolution] = {}
    base_cache: dict[str, _QueueAdapterResolution] = {}
    for path in _python_paths(diff):
        try:
            current_package = _module_package(path)
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
        if _network_protocol(imported) is not None:
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
    if result.category == "migration_safety":
        prefixes = tuple(
            sorted({prefix for rule in rules for prefix in rule["path_prefixes"]})
        )
        scope.update(prefixes)
        if prefixes:
            scope.update(_migration_paths(root, diff, prefixes))
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
