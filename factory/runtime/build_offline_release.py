#!/usr/bin/env python3
"""Build a canonical Factory release from an exact Git tree and closed wheelhouse."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import subprocess
import tempfile
import tomllib
import zipfile

from setup_manager import InstallerError, verify_release


PROFILE = "ubuntu-24.04-x86_64-cpython312"
HEX = re.compile(r"[0-9a-f]{64}\Z")
GIT_HEX = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
CANONICAL_TIME = (1980, 1, 1, 0, 0, 0)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _host_supported() -> bool:
    try:
        values = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)
        version = subprocess.run(["/usr/bin/python3.12", "--version"], capture_output=True, text=True,
                                 timeout=5, check=False, env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"})
        return (platform.system() == "Linux" and platform.machine() == "x86_64"
                and values.get("ID", "").strip('"') == "ubuntu"
                and values.get("VERSION_ID", "").strip('"') == "24.04"
                and version.returncode == 0 and version.stdout.startswith("Python 3.12."))
    except (OSError, subprocess.SubprocessError):
        return False


def _selected_wheel(package: dict) -> dict | None:
    if package["name"] == "tzdata":  # locked only for psycopg's Windows marker
        return None
    matches = []
    for wheel in package.get("wheels", []):
        filename = wheel["url"].rsplit("/", 1)[-1]
        universal = filename.endswith(("-py3-none-any.whl", "-py2.py3-none-any.whl"))
        native = "-cp312-cp312-" in filename and "manylinux" in filename and "x86_64" in filename
        if universal or native:
            matches.append((filename, wheel))
    if len(matches) != 1:
        raise InstallerError("LOCK_PROFILE_UNRESOLVED")
    filename, wheel = matches[0]
    digest = wheel.get("hash", "").removeprefix("sha256:")
    if not HEX.fullmatch(digest):
        raise InstallerError("LOCK_PROFILE_UNRESOLVED")
    return {"name": package["name"], "version": package["version"], "filename": filename, "sha256": digest}


def derive_inventory(lock: Path) -> dict:
    content = Path(lock).read_bytes()
    try:
        data = tomllib.loads(content.decode())
        packages = []
        for package in data["package"]:
            if package["name"] == "adaptive-factory":
                continue
            selected = _selected_wheel(package)
            if selected is not None:
                packages.append(selected)
    except (KeyError, TypeError, ValueError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise InstallerError("INVALID_LOCK") from exc
    return {"schema_version": "factory-runtime-wheels/v1", "profile": PROFILE,
            "lock_sha256": _digest(content), "wheels": sorted(packages, key=lambda item: item["name"])}


def _load_inventory(path: Path) -> dict:
    try:
        value = json.loads(Path(path).read_bytes())
    except (OSError, ValueError, UnicodeError) as exc:
        raise InstallerError("INVALID_WHEEL_INVENTORY") from exc
    if (not isinstance(value, dict) or set(value) != {"schema_version", "profile", "lock_sha256", "wheels"}
            or value["schema_version"] != "factory-runtime-wheels/v1" or value["profile"] != PROFILE
            or not HEX.fullmatch(value.get("lock_sha256", "")) or not isinstance(value["wheels"], list)):
        raise InstallerError("INVALID_WHEEL_INVENTORY")
    names = set()
    filenames = set()
    for item in value["wheels"]:
        if (not isinstance(item, dict) or set(item) != {"name", "version", "filename", "sha256"}
                or not all(isinstance(item[key], str) and item[key] for key in ("name", "version", "filename"))
                or not HEX.fullmatch(item["sha256"]) or PurePosixPath(item["filename"]).name != item["filename"]
                or not item["filename"].endswith(".whl") or item["name"] in names or item["filename"] in filenames):
            raise InstallerError("INVALID_WHEEL_INVENTORY")
        names.add(item["name"])
        filenames.add(item["filename"])
    if not value["wheels"] or value["wheels"] != sorted(value["wheels"], key=lambda item: item["name"]):
        raise InstallerError("INVALID_WHEEL_INVENTORY")
    return value


def validate_committed_inventory(lock: Path, inventory: Path) -> None:
    if _load_inventory(inventory) != derive_inventory(lock):
        raise InstallerError("WHEEL_INVENTORY_DRIFT")


def _safe_member(name: str) -> str:
    path = PurePosixPath(name)
    if (path.is_absolute() or not name or "\\" in name or any(part in {"", ".", ".."} for part in path.parts)
            or len(path.parts) > 32):
        raise InstallerError("UNSAFE_WHEEL")
    return str(path)


def _wheel_files(path: Path) -> dict[str, bytes]:
    result = {}
    try:
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                name = _safe_member(member.filename)
                mode = member.external_attr >> 16
                if member.is_dir():
                    continue
                if stat.S_IFMT(mode) not in {0, stat.S_IFREG} or member.flag_bits & 1 or member.file_size > 16 * 1024 * 1024:
                    raise InstallerError("UNSAFE_WHEEL")
                content = archive.read(member)
                if name in result:
                    raise InstallerError("UNSAFE_WHEEL")
                result[name] = content
    except (OSError, zipfile.BadZipFile, RuntimeError, ValueError) as exc:
        if isinstance(exc, InstallerError):
            raise
        raise InstallerError("UNSAFE_WHEEL") from exc
    return result


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(["git", *arguments], cwd=repository, stdin=subprocess.DEVNULL,
                            capture_output=True, text=True, timeout=20, check=False,
                            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"})
    if result.returncode:
        raise InstallerError("INVALID_SOURCE")
    return result.stdout


def build_release(*, repository: Path, expected_head: str, wheelhouse: Path, inventory: Path,
                  output: Path, product_version: str, enforce_host: bool = True) -> dict:
    repository = Path(repository).resolve()
    wheelhouse = Path(wheelhouse).resolve()
    output = Path(output).resolve()
    if enforce_host and not _host_supported():
        raise InstallerError("UNSUPPORTED_HOST")
    if not GIT_HEX.fullmatch(expected_head) or _git(repository, "rev-parse", "HEAD").strip() != expected_head:
        raise InstallerError("SOURCE_HEAD_MISMATCH")
    if _git(repository, "status", "--porcelain=v1", "--untracked-files=all"):
        raise InstallerError("SOURCE_NOT_CLEAN")
    lock = repository / "factory/uv.lock"
    validate_committed_inventory(lock, inventory)
    wheels = _load_inventory(inventory)["wheels"]
    entries = list(wheelhouse.iterdir())
    if any(entry.is_symlink() or not entry.is_file() for entry in entries):
        raise InstallerError("WHEELHOUSE_MISMATCH")
    actual = {entry.name for entry in entries}
    expected = {item["filename"] for item in wheels}
    if actual != expected:
        raise InstallerError("WHEELHOUSE_MISMATCH")
    files: dict[str, tuple[bytes, int]] = {}
    for item in wheels:
        wheel = wheelhouse / item["filename"]
        content = wheel.read_bytes()
        if _digest(content) != item["sha256"]:
            raise InstallerError("WHEEL_DIGEST_MISMATCH")
        for name, payload in _wheel_files(wheel).items():
            target = "site-packages/" + name
            if target in files:
                raise InstallerError("WHEEL_FILE_COLLISION")
            files[target] = (payload, 0o644)
    tracked = _git(repository, "ls-files", "factory/src/adaptive_factory").splitlines()
    if not tracked:
        raise InstallerError("INVALID_SOURCE")
    for relative in tracked:
        path = repository / relative
        if not path.is_file() or path.is_symlink():
            raise InstallerError("INVALID_SOURCE")
        target = "app/" + str(Path(relative).relative_to("factory/src"))
        files[target] = (path.read_bytes(), 0o644)
    archive_path = Path(str(output) + ".zip")
    manifest_path = Path(str(output) + ".manifest.json")
    sidecar_path = Path(str(output) + ".sha256")
    for path in (archive_path, manifest_path, sidecar_path):
        if path.exists():
            raise InstallerError("OUTPUT_EXISTS")
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".factory-release-", dir=archive_path.parent) as temporary:
        staged_archive = Path(temporary) / "release.zip"
        with zipfile.ZipFile(staged_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in sorted(files):
                info = zipfile.ZipInfo(name, CANONICAL_TIME)
                info.create_system = 3
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | files[name][1]) << 16
                archive.writestr(info, files[name][0])
        manifest = {"schema_version": "factory-release/v1", "product_version": product_version,
                    "profile": "factory-python", "data_schema": 0,
                    "files": [{"path": name, "size": len(files[name][0]), "sha256": _digest(files[name][0]),
                               "mode": files[name][1]} for name in sorted(files)]}
        manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        staged_manifest = Path(temporary) / "release.manifest.json"
        staged_manifest.write_bytes(manifest_bytes)
        archive_sha = _digest(staged_archive.read_bytes())
        manifest_sha = _digest(manifest_bytes)
        verify_release(archive=staged_archive, manifest=staged_manifest,
                       archive_sha256=archive_sha, manifest_sha256=manifest_sha)
        staged_sidecar = Path(temporary) / "release.sha256"
        staged_sidecar.write_text(
            f"{archive_sha}  {archive_path.name}\n{manifest_sha}  {manifest_path.name}\n"
        )
        try:
            os.replace(staged_archive, archive_path)
            os.replace(staged_manifest, manifest_path)
            os.replace(staged_sidecar, sidecar_path)
        except OSError as exc:
            for path in (archive_path, manifest_path, sidecar_path):
                path.unlink(missing_ok=True)
            raise InstallerError("OUTPUT_PUBLICATION_FAILED") from exc
    return {"archive": str(archive_path), "manifest": str(manifest_path),
            "sidecar": str(sidecar_path), "archive_sha256": archive_sha, "manifest_sha256": manifest_sha,
            "source_head": expected_head, "profile": PROFILE}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--product-version", required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build_release(**vars(args)), sort_keys=True))
        return 0
    except InstallerError as exc:
        print(json.dumps({"schema_version": "factory-error/v1", "error": exc.code}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
