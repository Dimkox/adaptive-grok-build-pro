from __future__ import annotations

import hashlib
import html
from pathlib import Path
from typing import Mapping

from .architecture import ArchitectureSnapshot
from .util import atomic_write_text

DIAGRAM_NAMES = ("context", "container", "deployment", "data-flow", "trust-boundary")
GENERATED_RELATIVE = Path("architecture/generated")


def _escape(value: object) -> str:
    text = " ".join(str(value).split())
    return html.escape(text, quote=True).replace("'", "&#x27;")


def _identifier(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _node_line(node: Mapping[str, object]) -> str:
    label = _escape(f"{node['id']} | {node['type']} | {node['owner']}")
    return f'  {_identifier("node", str(node["id"]))}["{label}"]'


def _edge_line(edge: Mapping[str, object], *, data: bool = False) -> str:
    source = _identifier("node", str(edge["from"]))
    target = _identifier("node", str(edge["to"]))
    details = [str(edge["id"]), str(edge["type"]), str(edge["protocol"])]
    if data:
        details.extend(str(item) for item in edge.get("allowed_data", []))
    return f'  {source} -->|"{_escape(" | ".join(details))}"| {target}'


def _plain_graph(snapshot: ArchitectureSnapshot, *, deployed_only: bool = False) -> str:
    nodes = sorted(snapshot.system["nodes"], key=lambda item: item["id"])
    if deployed_only:
        nodes = [node for node in nodes if node["runtime"]["kind"] != "none"]
    node_ids = {node["id"] for node in nodes}
    edges = [
        edge
        for edge in sorted(snapshot.system["edges"], key=lambda item: item["id"])
        if edge["from"] in node_ids and edge["to"] in node_ids
    ]
    lines = ["flowchart LR", *(_node_line(node) for node in nodes)]
    lines.extend(_edge_line(edge) for edge in edges)
    return "\n".join(lines) + "\n"


def _context(snapshot: ArchitectureSnapshot) -> str:
    domains = sorted(snapshot.system["trust_domains"], key=lambda item: item["id"])
    nodes = {node["id"]: node for node in snapshot.system["nodes"]}
    lines = ["flowchart LR"]
    for domain in domains:
        label = _escape(f"{domain['id']} | {domain['kind']} | {domain['owner']}")
        lines.append(f'  {_identifier("domain", domain["id"])}["{label}"]')
    seen: set[tuple[str, str, str]] = set()
    for edge in sorted(snapshot.system["edges"], key=lambda item: item["id"]):
        source = nodes[edge["from"]]["trust_domain"]
        target = nodes[edge["to"]]["trust_domain"]
        key = (source, target, edge["type"])
        if source == target or key in seen:
            continue
        seen.add(key)
        lines.append(
            f'  {_identifier("domain", source)} -->|"{_escape(edge["type"])}"| '
            f'{_identifier("domain", target)}'
        )
    return "\n".join(lines) + "\n"


def _data_flow(snapshot: ArchitectureSnapshot) -> str:
    nodes = sorted(snapshot.system["nodes"], key=lambda item: item["id"])
    edges = [
        edge for edge in sorted(snapshot.system["edges"], key=lambda item: item["id"])
        if edge["type"] in {"data_flow", "publication", "secret_flow"}
    ]
    used = {value for edge in edges for value in (edge["from"], edge["to"])}
    lines = ["flowchart LR", *(_node_line(node) for node in nodes if node["id"] in used)]
    lines.extend(_edge_line(edge, data=True) for edge in edges)
    return "\n".join(lines) + "\n"


def _trust_boundary(snapshot: ArchitectureSnapshot) -> str:
    lines = ["flowchart LR"]
    for domain in sorted(snapshot.system["trust_domains"], key=lambda item: item["id"]):
        domain_id = _identifier("domain", domain["id"])
        lines.append(f'  subgraph {domain_id}["{_escape(domain["id"])}"]')
        for node in sorted(snapshot.system["nodes"], key=lambda item: item["id"]):
            if node["trust_domain"] == domain["id"]:
                lines.append("  " + _node_line(node))
        lines.append("  end")
    lines.extend(_edge_line(edge) for edge in sorted(snapshot.system["edges"], key=lambda item: item["id"]))
    return "\n".join(lines) + "\n"


def render_diagrams(snapshot: ArchitectureSnapshot) -> dict[str, str]:
    return {
        "context": _context(snapshot),
        "container": _plain_graph(snapshot),
        "deployment": _plain_graph(snapshot, deployed_only=True),
        "data-flow": _data_flow(snapshot),
        "trust-boundary": _trust_boundary(snapshot),
    }


def artifact_digests(rendered: Mapping[str, str]) -> dict[str, str]:
    return {
        f"{name}.mmd": hashlib.sha256(rendered[name].encode("utf-8")).hexdigest()
        for name in DIAGRAM_NAMES
    }


def compare_generated(root: Path, rendered: Mapping[str, str]) -> tuple[str, ...]:
    mismatches: list[str] = []
    directory = root / GENERATED_RELATIVE
    for name in DIAGRAM_NAMES:
        path = directory / f"{name}.mmd"
        try:
            actual = path.read_bytes()
        except OSError:
            mismatches.append(path.relative_to(root).as_posix())
            continue
        if actual != rendered[name].encode("utf-8"):
            mismatches.append(path.relative_to(root).as_posix())
    return tuple(mismatches)


def write_generated(root: Path, rendered: Mapping[str, str]) -> tuple[str, ...]:
    paths: list[str] = []
    for name in DIAGRAM_NAMES:
        path = root / GENERATED_RELATIVE / f"{name}.mmd"
        atomic_write_text(path, rendered[name])
        paths.append(path.relative_to(root).as_posix())
    return tuple(paths)


__all__ = [
    "DIAGRAM_NAMES",
    "artifact_digests",
    "compare_generated",
    "render_diagrams",
    "write_generated",
]
