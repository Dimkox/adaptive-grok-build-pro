from __future__ import annotations

import hashlib
import html
import os
import stat
from pathlib import Path
from typing import Mapping

from .architecture import ArchitectureError, ArchitectureSnapshot, _secure_open_flags

DIAGRAM_NAMES = ("context", "container", "deployment", "data-flow", "trust-boundary")
GENERATED_RELATIVE = Path("architecture/generated")
MAX_GENERATED_ARTIFACT_BYTES = 1_000_000


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
        edge
        for edge in sorted(snapshot.system["edges"], key=lambda item: item["id"])
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
    lines.extend(
        _edge_line(edge)
        for edge in sorted(snapshot.system["edges"], key=lambda item: item["id"])
    )
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


def _directory_identity(descriptor: int) -> tuple[int, int, int]:
    info = os.fstat(descriptor)
    return info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)


def _open_generated_directory(root: Path) -> tuple[int, int, int]:
    no_follow, directory_flag, _nonblock = _secure_open_flags(
        label="generated architecture diagrams"
    )
    root_fd = architecture_fd = generated_fd = -1
    try:
        root_fd = os.open(root.resolve(strict=True), os.O_RDONLY | directory_flag | no_follow)
        try:
            architecture_fd = os.open(
                "architecture", os.O_RDONLY | directory_flag | no_follow, dir_fd=root_fd
            )
        except FileNotFoundError:
            return root_fd, -1, -1
        try:
            generated_fd = os.open(
                "generated", os.O_RDONLY | directory_flag | no_follow, dir_fd=architecture_fd
            )
        except FileNotFoundError:
            return root_fd, architecture_fd, -1
        return root_fd, architecture_fd, generated_fd
    except OSError as exc:
        for descriptor in (generated_fd, architecture_fd, root_fd):
            if descriptor >= 0:
                os.close(descriptor)
        raise ArchitectureError(
            f"generated architecture diagrams: unsafe directory: {exc}", code="io"
        ) from exc
    except BaseException:
        for descriptor in (generated_fd, architecture_fd, root_fd):
            if descriptor >= 0:
                os.close(descriptor)
        raise


def _verify_contained_directory(
    root_fd: int,
    architecture_fd: int,
    generated_fd: int,
) -> None:
    no_follow, directory_flag, _nonblock = _secure_open_flags(
        label="generated architecture diagrams"
    )
    reopened_architecture = reopened_generated = -1
    try:
        reopened_architecture = os.open(
            "architecture", os.O_RDONLY | directory_flag | no_follow, dir_fd=root_fd
        )
        reopened_generated = os.open(
            "generated",
            os.O_RDONLY | directory_flag | no_follow,
            dir_fd=reopened_architecture,
        )
        if _directory_identity(reopened_architecture) != _directory_identity(architecture_fd):
            raise ArchitectureError("architecture diagram directory changed", code="io")
        if _directory_identity(reopened_generated) != _directory_identity(generated_fd):
            raise ArchitectureError("generated diagram directory changed", code="io")
    except ArchitectureError:
        raise
    except OSError as exc:
        raise ArchitectureError(
            f"generated architecture diagram directory changed: {exc}", code="io"
        ) from exc
    finally:
        if reopened_generated >= 0:
            os.close(reopened_generated)
        if reopened_architecture >= 0:
            os.close(reopened_architecture)


def _rendered_bytes(rendered: Mapping[str, str], name: str) -> bytes:
    try:
        value = rendered[name].encode("utf-8")
    except (KeyError, AttributeError, UnicodeEncodeError) as exc:
        raise ArchitectureError(f"invalid generated diagram: {name}", code="parse") from exc
    if len(value) > MAX_GENERATED_ARTIFACT_BYTES:
        raise ArchitectureError(f"generated diagram exceeds byte limit: {name}", code="limit")
    return value


def _read_generated(generated_fd: int, filename: str, expected_limit: int) -> bytes | None:
    no_follow, _directory_flag, nonblock = _secure_open_flags(
        label="generated architecture diagrams"
    )
    descriptor = -1
    try:
        descriptor = os.open(filename, os.O_RDONLY | no_follow | nonblock, dir_fd=generated_fd)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ArchitectureError(
                f"generated diagram is not a regular file: {filename}", code="io"
            )
        if before.st_size > expected_limit:
            raise ArchitectureError(f"generated diagram exceeds byte limit: {filename}", code="limit")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
        value = b"".join(chunks)
        if (
            len(value) != before.st_size
            or (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            )
            != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            )
        ):
            raise ArchitectureError(f"generated diagram changed while reading: {filename}", code="io")
        return value
    except FileNotFoundError:
        return None
    except ArchitectureError:
        raise
    except OSError as exc:
        raise ArchitectureError(
            f"cannot safely read generated diagram {filename}: {exc}", code="io"
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def compare_generated(root: Path, rendered: Mapping[str, str]) -> tuple[str, ...]:
    mismatches: list[str] = []
    root_fd = architecture_fd = generated_fd = -1
    try:
        root_fd, architecture_fd, generated_fd = _open_generated_directory(root)
        if generated_fd < 0:
            return tuple(f"architecture/generated/{name}.mmd" for name in DIAGRAM_NAMES)
        for name in DIAGRAM_NAMES:
            expected = _rendered_bytes(rendered, name)
            actual = _read_generated(
                generated_fd,
                f"{name}.mmd",
                min(MAX_GENERATED_ARTIFACT_BYTES, len(expected) + 1),
            )
            if actual != expected:
                mismatches.append(f"architecture/generated/{name}.mmd")
        _verify_contained_directory(root_fd, architecture_fd, generated_fd)
        return tuple(mismatches)
    finally:
        for descriptor in (generated_fd, architecture_fd, root_fd):
            if descriptor >= 0:
                os.close(descriptor)


__all__ = [
    "DIAGRAM_NAMES",
    "artifact_digests",
    "compare_generated",
    "render_diagrams",
]
