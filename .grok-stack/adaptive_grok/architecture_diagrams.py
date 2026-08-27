from __future__ import annotations

import hashlib
import html
import ctypes
import errno
import os
import secrets
import stat
from pathlib import Path
from typing import Mapping

from .architecture import ArchitectureError, ArchitectureSnapshot, _secure_open_flags

DIAGRAM_NAMES = ("context", "container", "deployment", "data-flow", "trust-boundary")
GENERATED_RELATIVE = Path("architecture/generated")
MAX_GENERATED_ARTIFACT_BYTES = 1_000_000
MAX_ARCHITECTURE_XATTRS = 64
MAX_ARCHITECTURE_XATTR_BYTES = 65_536
_RENAME_EXCHANGE = 2


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


def _directory_identity(descriptor: int) -> tuple[int, int, int]:
    info = os.fstat(descriptor)
    return info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)


def _open_generated_directory(root: Path, *, create: bool) -> tuple[int, int, int]:
    no_follow, directory_flag, _nonblock = _secure_open_flags(
        label="generated architecture diagrams"
    )
    supports_dir_fd = getattr(os, "supports_dir_fd", set())
    supports_follow = getattr(os, "supports_follow_symlinks", set())
    required = {os.mkdir, os.rename, os.stat, os.unlink} if create else set()
    if (
        not required.issubset(supports_dir_fd)
        or (create and os.stat not in supports_follow)
    ):
        raise ArchitectureError(
            "generated architecture diagrams: descriptor-relative mutation is unavailable",
            code="io",
        )
    root_fd = architecture_fd = generated_fd = -1
    try:
        root_fd = os.open(root.resolve(strict=True), os.O_RDONLY | directory_flag | no_follow)
        try:
            architecture_fd = os.open(
                "architecture", os.O_RDONLY | directory_flag | no_follow, dir_fd=root_fd
            )
        except FileNotFoundError:
            if not create:
                return root_fd, -1, -1
            os.mkdir("architecture", mode=0o755, dir_fd=root_fd)
            architecture_fd = os.open(
                "architecture", os.O_RDONLY | directory_flag | no_follow, dir_fd=root_fd
            )
        try:
            generated_fd = os.open(
                "generated", os.O_RDONLY | directory_flag | no_follow, dir_fd=architecture_fd
            )
        except FileNotFoundError:
            if not create:
                return root_fd, architecture_fd, -1
            os.mkdir("generated", mode=0o755, dir_fd=architecture_fd)
            generated_fd = os.open(
                "generated", os.O_RDONLY | directory_flag | no_follow, dir_fd=architecture_fd
            )
        return root_fd, architecture_fd, generated_fd
    except ArchitectureError:
        for descriptor in (generated_fd, architecture_fd, root_fd):
            if descriptor >= 0:
                os.close(descriptor)
        raise
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
        descriptor = os.open(
            filename, os.O_RDONLY | no_follow | nonblock, dir_fd=generated_fd
        )
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ArchitectureError(f"generated diagram is not a regular file: {filename}", code="io")
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
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        ):
            raise ArchitectureError(f"generated diagram changed while reading: {filename}", code="io")
        return value
    except FileNotFoundError:
        return None
    except ArchitectureError:
        raise
    except OSError as exc:
        raise ArchitectureError(f"cannot safely read generated diagram {filename}: {exc}", code="io") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _discard_entry(parent_fd: int, name: str) -> None:
    """Remove a bounded generated entry without following a symlink entry."""
    no_follow, directory_flag, _nonblock = _secure_open_flags(
        label="generated architecture diagrams"
    )
    try:
        info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(info.st_mode) or stat.S_ISREG(info.st_mode):
        os.unlink(name, dir_fd=parent_fd)
        return
    if not stat.S_ISDIR(info.st_mode):
        raise ArchitectureError("generated diagram publication encountered a special file", code="io")
    descriptor = os.open(name, os.O_RDONLY | directory_flag | no_follow, dir_fd=parent_fd)
    try:
        entries = sorted(os.listdir(descriptor))
        if len(entries) > len(DIAGRAM_NAMES):
            raise ArchitectureError("generated diagram directory has unexpected entries", code="io")
        for entry in entries:
            child = os.stat(entry, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISREG(child.st_mode) or child.st_size > MAX_GENERATED_ARTIFACT_BYTES:
                raise ArchitectureError("generated diagram backup is unsafe", code="io")
            os.unlink(entry, dir_fd=descriptor)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
        raise ArchitectureError("generated diagram directory changed during publication", code="io")
    os.rmdir(name, dir_fd=parent_fd)


def _entry_identity(root_fd: int, name: str) -> tuple[int, int, int]:
    try:
        info = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise ArchitectureError("architecture publication entry was relocated", code="io") from exc
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise ArchitectureError("architecture publication encountered an unsafe entry", code="io")
    return info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)


def _require_entry_identity(
    root_fd: int,
    name: str,
    expected: tuple[int, int, int],
) -> None:
    if _entry_identity(root_fd, name) != expected:
        raise ArchitectureError("architecture publication entry was relocated", code="io")


def _discard_architecture_entry(root_fd: int, name: str) -> None:
    """Remove a bounded root-contained tree without mutating through a held child fd."""
    no_follow, directory_flag, _nonblock = _secure_open_flags(
        label="generated architecture diagrams"
    )
    identity = _entry_identity(root_fd, name)
    descriptor = os.open(name, os.O_RDONLY | directory_flag | no_follow, dir_fd=root_fd)
    try:
        entries = sorted(os.listdir(descriptor))
        allowed = {"adoption.json", "system.yaml", "rules.yaml", "generated"}
        if not set(entries).issubset(allowed):
            raise ArchitectureError("architecture publication has unexpected entries", code="io")
        generated_entries: list[str] = []
        if "generated" in entries:
            generated = os.open(
                "generated", os.O_RDONLY | directory_flag | no_follow, dir_fd=descriptor
            )
            try:
                generated_entries = sorted(os.listdir(generated))
                if not set(generated_entries).issubset(
                    {f"{diagram}.mmd" for diagram in DIAGRAM_NAMES}
                ):
                    raise ArchitectureError(
                        "generated diagram directory has unexpected entries", code="io"
                    )
            finally:
                os.close(generated)
    finally:
        os.close(descriptor)

    # Never unlink through the descriptors used to inventory the tree. Reprove
    # the root-relative entry identity before each bounded mutation.
    for entry in generated_entries:
        _require_entry_identity(root_fd, name, identity)
        relative = f"{name}/generated/{entry}"
        child = os.stat(relative, dir_fd=root_fd, follow_symlinks=False)
        if not stat.S_ISREG(child.st_mode) or child.st_size > MAX_GENERATED_ARTIFACT_BYTES:
            raise ArchitectureError("generated diagram backup is unsafe", code="io")
        os.unlink(relative, dir_fd=root_fd)
    if "generated" in entries:
        _require_entry_identity(root_fd, name, identity)
        os.rmdir(f"{name}/generated", dir_fd=root_fd)
    for entry in ("adoption.json", "system.yaml", "rules.yaml"):
        if entry not in entries:
            continue
        _require_entry_identity(root_fd, name, identity)
        relative = f"{name}/{entry}"
        child = os.stat(relative, dir_fd=root_fd, follow_symlinks=False)
        if not stat.S_ISREG(child.st_mode):
            raise ArchitectureError("architecture authority backup is unsafe", code="io")
        os.unlink(relative, dir_fd=root_fd)
    _require_entry_identity(root_fd, name, identity)
    os.rmdir(name, dir_fd=root_fd)


def _directory_metadata(descriptor: int) -> tuple[int, int, int, tuple[tuple[str, bytes], ...]]:
    info = os.fstat(descriptor)
    try:
        names = sorted(os.listxattr(descriptor))
    except (AttributeError, NotImplementedError, OSError) as exc:
        raise ArchitectureError("architecture directory metadata is unavailable", code="io") from exc
    if len(names) > MAX_ARCHITECTURE_XATTRS:
        raise ArchitectureError("architecture directory xattr limit exceeded", code="limit")
    attributes: list[tuple[str, bytes]] = []
    total = 0
    for name in names:
        value = os.getxattr(descriptor, name)
        total += len(name.encode("utf-8")) + len(value)
        if total > MAX_ARCHITECTURE_XATTR_BYTES:
            raise ArchitectureError("architecture directory xattr byte limit exceeded", code="limit")
        attributes.append((name, value))
    return stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid, tuple(attributes)


def _copy_directory_metadata(source_fd: int, destination_fd: int) -> None:
    mode, uid, gid, attributes = _directory_metadata(source_fd)
    destination = os.fstat(destination_fd)
    if (destination.st_uid, destination.st_gid) != (uid, gid):
        try:
            os.fchown(destination_fd, uid, gid)
        except (AttributeError, PermissionError, OSError) as exc:
            raise ArchitectureError("architecture directory ownership cannot be preserved", code="io") from exc
    os.fchmod(destination_fd, mode)
    for name, value in attributes:
        try:
            os.setxattr(destination_fd, name, value)
        except (AttributeError, NotImplementedError, OSError) as exc:
            raise ArchitectureError("architecture directory xattrs cannot be preserved", code="io") from exc
    if _directory_metadata(destination_fd) != (mode, uid, gid, attributes):
        raise ArchitectureError("architecture directory metadata changed during staging", code="io")


def _authority_inventory(descriptor: int) -> tuple[tuple[str, int, int, int, int], ...]:
    entries = sorted(os.listdir(descriptor))
    if len(entries) > 4:
        raise ArchitectureError("architecture directory has unexpected entries", code="io")
    inventory: list[tuple[str, int, int, int, int]] = []
    for entry in entries:
        if entry == "generated":
            continue
        info = os.stat(entry, dir_fd=descriptor, follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode):
            raise ArchitectureError("architecture authority entry is unsafe", code="io")
        inventory.append((entry, info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns))
    return tuple(inventory)


def _exchange_entries(root_fd: int, left: str, right: str) -> None:
    try:
        function = ctypes.CDLL(None, use_errno=True).renameat2
    except (AttributeError, OSError) as exc:
        raise ArchitectureError("atomic architecture exchange is unavailable", code="io") from exc
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    result = function(
        root_fd,
        os.fsencode(left),
        root_fd,
        os.fsencode(right),
        _RENAME_EXCHANGE,
    )
    if result != 0:
        code = ctypes.get_errno()
        if code in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP}:
            raise ArchitectureError("atomic architecture exchange is unavailable", code="io")
        raise ArchitectureError(
            f"atomic architecture exchange failed: {os.strerror(code)}", code="io"
        )


def _replace_generated(root_fd: int, staging: str, destination: str) -> None:
    """CAS-publish a complete architecture entry relative to the held root."""
    _entry_identity(root_fd, destination)
    _entry_identity(root_fd, staging)
    _exchange_entries(root_fd, destination, staging)
    current_fd = previous_fd = -1
    try:
        no_follow, directory_flag, _nonblock = _secure_open_flags(
            label="generated architecture diagrams"
        )
        current_fd = os.open(
            destination, os.O_RDONLY | directory_flag | no_follow, dir_fd=root_fd
        )
        previous_fd = os.open(staging, os.O_RDONLY | directory_flag | no_follow, dir_fd=root_fd)
        if (
            _authority_inventory(current_fd) != _authority_inventory(previous_fd)
            or _directory_metadata(current_fd) != _directory_metadata(previous_fd)
        ):
            raise ArchitectureError(
                "architecture authority changed before diagram publication", code="io"
            )
    except BaseException as exc:
        for descriptor in (previous_fd, current_fd):
            if descriptor >= 0:
                os.close(descriptor)
        previous_fd = current_fd = -1
        try:
            _exchange_entries(root_fd, destination, staging)
        except BaseException as rollback_exc:
            raise ArchitectureError(
                "architecture publication rollback failed", code="io"
            ) from rollback_exc
        try:
            _discard_architecture_entry(root_fd, staging)
        except ArchitectureError as cleanup_exc:
            raise cleanup_exc from exc
        raise
    finally:
        for descriptor in (previous_fd, current_fd):
            if descriptor >= 0:
                os.close(descriptor)
    _discard_architecture_entry(root_fd, staging)
    os.fsync(root_fd)


def compare_generated(root: Path, rendered: Mapping[str, str]) -> tuple[str, ...]:
    mismatches: list[str] = []
    root_fd = architecture_fd = generated_fd = -1
    try:
        root_fd, architecture_fd, generated_fd = _open_generated_directory(root, create=False)
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


def write_generated(root: Path, rendered: Mapping[str, str]) -> tuple[str, ...]:
    paths = tuple(f"architecture/generated/{name}.mmd" for name in DIAGRAM_NAMES)
    root_fd = architecture_fd = staging_architecture_fd = staging_fd = -1
    published_architecture_fd = published_fd = -1
    staging = f".architecture.{secrets.token_hex(12)}.tmp"
    try:
        no_follow, directory_flag, _nonblock = _secure_open_flags(
            label="generated architecture diagrams"
        )
        supports_dir_fd = getattr(os, "supports_dir_fd", set())
        required = {os.link, os.mkdir, os.rename, os.stat, os.unlink, os.rmdir}
        if not required.issubset(supports_dir_fd) or os.stat not in getattr(
            os, "supports_follow_symlinks", set()
        ) or os.link not in getattr(os, "supports_follow_symlinks", set()):
            raise ArchitectureError(
                "generated architecture diagrams: safe publication is unavailable", code="io"
            )
        # Validate an existing destination, but never retain its descriptor for writes.
        check_root = check_architecture = check_generated = -1
        try:
            check_root, check_architecture, check_generated = _open_generated_directory(
                root, create=False
            )
            if check_generated >= 0:
                entries = sorted(os.listdir(check_generated))
                expected_names = {f"{name}.mmd" for name in DIAGRAM_NAMES}
                if not set(entries).issubset(expected_names):
                    raise ArchitectureError("generated diagram directory has unexpected entries", code="io")
                for filename in entries:
                    _read_generated(check_generated, filename, MAX_GENERATED_ARTIFACT_BYTES)
                _verify_contained_directory(check_root, check_architecture, check_generated)
        finally:
            for descriptor in (check_generated, check_architecture, check_root):
                if descriptor >= 0:
                    os.close(descriptor)

        root_fd = os.open(root.resolve(strict=True), os.O_RDONLY | directory_flag | no_follow)
        architecture_fd = os.open(
            "architecture", os.O_RDONLY | directory_flag | no_follow, dir_fd=root_fd
        )
        architecture_identity = _directory_identity(architecture_fd)
        entries = sorted(os.listdir(architecture_fd))
        allowed_entries = {"adoption.json", "system.yaml", "rules.yaml", "generated"}
        if not set(entries).issubset(allowed_entries):
            raise ArchitectureError("architecture directory has unexpected entries", code="io")
        os.mkdir(staging, mode=0o755, dir_fd=root_fd)
        staging_architecture_fd = os.open(
            staging, os.O_RDONLY | directory_flag | no_follow, dir_fd=root_fd
        )
        _copy_directory_metadata(architecture_fd, staging_architecture_fd)
        for authority in ("adoption.json", "system.yaml", "rules.yaml"):
            if authority not in entries:
                continue
            before = os.stat(authority, dir_fd=architecture_fd, follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode):
                raise ArchitectureError("architecture authority entry is unsafe", code="io")
            os.link(
                authority,
                authority,
                src_dir_fd=architecture_fd,
                dst_dir_fd=staging_architecture_fd,
                follow_symlinks=False,
            )
            linked = os.stat(authority, dir_fd=staging_architecture_fd, follow_symlinks=False)
            after = os.stat(authority, dir_fd=architecture_fd, follow_symlinks=False)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                linked.st_dev,
                linked.st_ino,
                linked.st_size,
                linked.st_mtime_ns,
            ) or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
            ):
                raise ArchitectureError("architecture authority changed during staging", code="io")
        if _directory_identity(architecture_fd) != architecture_identity:
            raise ArchitectureError("architecture directory changed during staging", code="io")
        os.mkdir("generated", mode=0o755, dir_fd=staging_architecture_fd)
        staging_fd = os.open(
            "generated",
            os.O_RDONLY | directory_flag | no_follow,
            dir_fd=staging_architecture_fd,
        )
        for name in DIAGRAM_NAMES:
            value = _rendered_bytes(rendered, name)
            filename = f"{name}.mmd"
            descriptor = -1
            try:
                descriptor = os.open(
                    filename,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | no_follow,
                    0o644,
                    dir_fd=staging_fd,
                )
                written = 0
                while written < len(value):
                    count = os.write(descriptor, value[written:])
                    if count <= 0:
                        raise ArchitectureError(
                            f"generated diagram write made no progress: {filename}",
                            code="io",
                        )
                    written += count
                os.fsync(descriptor)
                os.close(descriptor)
                descriptor = -1
            except ArchitectureError:
                raise
            except OSError as exc:
                raise ArchitectureError(f"cannot safely write generated diagram {filename}: {exc}", code="io") from exc
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
        os.fsync(staging_fd)
        os.close(staging_fd)
        staging_fd = -1
        os.fsync(staging_architecture_fd)
        os.close(staging_architecture_fd)
        staging_architecture_fd = -1
        os.close(architecture_fd)
        architecture_fd = -1
        _replace_generated(root_fd, staging, "architecture")
        staging = ""
        published_architecture_fd = os.open(
            "architecture", os.O_RDONLY | directory_flag | no_follow, dir_fd=root_fd
        )
        published_fd = os.open(
            "generated",
            os.O_RDONLY | directory_flag | no_follow,
            dir_fd=published_architecture_fd,
        )
        _verify_contained_directory(root_fd, published_architecture_fd, published_fd)
        return paths
    except ArchitectureError:
        raise
    except OSError as exc:
        raise ArchitectureError(f"cannot safely publish generated diagrams: {exc}", code="io") from exc
    finally:
        for descriptor in (
            published_fd,
            published_architecture_fd,
            staging_fd,
            staging_architecture_fd,
        ):
            if descriptor >= 0:
                os.close(descriptor)
        if staging and root_fd >= 0:
            try:
                _discard_architecture_entry(root_fd, staging)
            except (ArchitectureError, OSError):
                pass
        for descriptor in (architecture_fd, root_fd):
            if descriptor >= 0:
                os.close(descriptor)


__all__ = [
    "DIAGRAM_NAMES",
    "artifact_digests",
    "compare_generated",
    "render_diagrams",
    "write_generated",
]
