from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass
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
_PYTHON_SUFFIXES = {".py", ".pyi"}
_NETWORK_IMPORTS = {
    "aiohttp": "https",
    "docker": "docker_api",
    "httpx": "https",
    "psycopg": "postgresql",
    "psycopg2": "postgresql",
    "requests": "https",
    "socket": "tcp",
    "urllib": "https",
}
_QUEUE_IMPORTS = {"celery", "confluent_kafka", "kafka", "kombu", "pika", "redis", "rq"}
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
        for path in head_paths:
            parsed = _migration_phase(path)
            if parsed:
                phases.setdefault(parsed[0], set()).add(parsed[1])
        for item in relevant:
            if item.status != "added":
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
            destructive = re.search(r"\b(DROP|TRUNCATE)\b|\bALTER\s+TABLE\b[^;]*\bDROP\b", source, re.I)
            if destructive and parsed[1] != "contract":
                findings.append(f"{rule['id']}: destructive SQL outside contract phase: {item.path}")
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


def _network_clients(
    snapshot: ArchitectureSnapshot,
    diff: ArchitectureDiff,
    python: _PythonInventory,
) -> FitnessResult:
    rules = snapshot.rules["network_policies"]
    predicate = "changed owned Python source imports a bounded network-client family"
    if not rules:
        return _not_applicable("network_client", predicate, (), "no_declared_rules")
    clients: list[tuple[str, str, dict[str, Any]]] = []
    unsupported: list[str] = []
    for path in _python_paths(diff):
        owner = _owner_for_path(snapshot, path)
        if owner is None:
            continue
        try:
            imports = _imports(python.tree(path))
        except SyntaxError as exc:
            unsupported.append(f"{path}: {exc}")
            continue
        for imported in imports:
            protocol = _NETWORK_IMPORTS.get(imported.split(".")[0])
            if protocol:
                clients.append((path, protocol, owner))
    applicable = [
        item for item in clients if any(item[2]["type"] in rule["node_types"] for rule in rules)
    ]
    if unsupported and any(_owner_for_path(snapshot, path) for path in _python_paths(diff)):
        return _result(
            "network_client",
            status="unsupported",
            rules=(rule["id"] for rule in rules),
            findings=unsupported,
            predicate=predicate,
            scope=_python_paths(diff),
            reason="unparseable_source",
        )
    if not applicable:
        return _not_applicable(
            "network_client", predicate, _python_paths(diff), "no_network_client",
            (rule["id"] for rule in rules),
        )
    findings: list[str] = []
    edges = snapshot.system["edges"]
    for path, protocol, owner in applicable:
        for rule in rules:
            if owner["type"] not in rule["node_types"]:
                continue
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
        scope=(item[0] for item in applicable),
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


def _background_jobs(snapshot: ArchitectureSnapshot, diff: ArchitectureDiff) -> FitnessResult:
    rules = snapshot.rules["background_job_policies"]
    predicate = "worker/runner asynchronous or batch edges are governed as background work"
    if not rules:
        return _not_applicable("background_job", predicate, (), "no_declared_rules")
    if not _model_changed(diff):
        return _not_applicable(
            "background_job", predicate, (), "architecture_unchanged", (rule["id"] for rule in rules)
        )
    nodes = {node["id"]: node for node in snapshot.system["nodes"]}
    findings: list[str] = []
    scope: list[str] = []
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
        status="fail" if findings else "pass",
        rules=(rule["id"] for rule in rules),
        findings=findings,
        predicate=predicate,
        scope=scope,
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


def _risk(
    root: Path,
    snapshot: ArchitectureSnapshot,
    diff: ArchitectureDiff,
    python: _PythonInventory,
    pre_risk: str,
) -> tuple[str, str, tuple[str, ...]]:
    if pre_risk not in RISK_ORDER:
        raise ArchitectureError("pre_risk must be green, yellow, or red", code="risk")
    triggers = set(_risk_triggers(snapshot, diff))
    if _new_import_family(root, diff, python, _QUEUE_IMPORTS):
        triggers.add("new_queue")
    if _new_import_family(root, diff, python, set(_NETWORK_IMPORTS)):
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
    results = tuple(
        sorted(
            (
                _background_jobs(snapshot, diff),
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
    if tuple(item.category for item in results) != FITNESS_CATEGORIES:
        raise ArchitectureError("mandatory fitness category coverage is incomplete", code="fitness")
    escalation, post_risk, triggers = _risk(
        repository, snapshot, diff, python, pre_risk
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
