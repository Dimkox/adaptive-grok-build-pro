#!/usr/bin/env python3
"""Opt-in, unprivileged Ubuntu process adapter for immutable Factory releases."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import platform
import re
import signal
import socket
import stat
import subprocess
import time

from setup_manager import InstallerError, _atomic_json, _json, _read


PROFILE = "factory-python"
CONFIG_SCHEMA = "factory-linux-process/v1"
ARGV = ("/usr/bin/python3.12", "-m", "adaptive_factory.server")
HEX = re.compile(r"[0-9a-f]{64}\Z")
ENV_NAME = re.compile(r"FACTORY_[A-Z0-9_]{1,96}\Z")
MAX_LOG_BYTES = 65_536


def _safe_directory_info(metadata: os.stat_result, *, final: bool) -> bool:
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid not in {0, os.getuid()}:
        return False
    if final:
        return metadata.st_uid == os.getuid() and stat.S_IMODE(metadata.st_mode) == 0o700
    return not metadata.st_mode & 0o022 or (
        metadata.st_uid == 0 and metadata.st_mode & stat.S_ISVTX
    )


def _open_path(path: Path, *, directory: bool = False) -> int:
    """Open an absolute path through owner-pinned, no-follow directory descriptors."""
    path = Path(path)
    if not path.is_absolute() or path == Path("/"):
        raise InstallerError("UNSAFE_RUNTIME_CONFIG")
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        parts = path.parts[1:]
        for index, part in enumerate(parts):
            final = index == len(parts) - 1
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
            if not final or directory:
                flags |= os.O_DIRECTORY
            child = os.open(part, flags, dir_fd=descriptor)
            metadata = os.fstat(child)
            if not final and not _safe_directory_info(metadata, final=False):
                os.close(child)
                raise InstallerError("UNSAFE_RUNTIME_CONFIG")
            os.close(descriptor)
            descriptor = child
        return descriptor
    except (OSError, InstallerError) as exc:
        os.close(descriptor)
        if isinstance(exc, InstallerError):
            raise
        raise InstallerError("UNSAFE_RUNTIME_CONFIG") from exc


def _host_supported(python: str = ARGV[0], *, timeout: int = 5) -> bool:
    try:
        values = {}
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip('"')
        result = subprocess.run(
            [python, "--version"], stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=timeout, check=False, env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        )
        return (
            platform.system() == "Linux"
            and platform.machine() == "x86_64"
            and values.get("ID") == "ubuntu"
            and values.get("VERSION_ID") == "24.04"
            and result.returncode == 0
            and result.stdout.strip().startswith("Python 3.12.")
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return False


def _private_config(path: Path, root: Path) -> dict:
    del root
    descriptor = None
    try:
        path = Path(path)
        descriptor = _open_path(path)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_size > 65_536
        ):
            raise InstallerError("UNSAFE_RUNTIME_CONFIG")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = None
            content = handle.read(65_537)
            after = os.fstat(handle.fileno())
        if len(content) > 65_536 or (metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns) != (
            after.st_size, after.st_mtime_ns, after.st_ctime_ns
        ):
            raise InstallerError("UNSAFE_RUNTIME_CONFIG")
        value = _json(content)
    except (OSError, InstallerError) as exc:
        if isinstance(exc, InstallerError) and exc.code == "UNSAFE_RUNTIME_CONFIG":
            raise
        raise InstallerError("UNSAFE_RUNTIME_CONFIG") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if set(value) != {"schema_version", "python", "runtime_directory", "environment"}:
        raise InstallerError("INVALID_RUNTIME_CONFIG")
    if value["schema_version"] != CONFIG_SCHEMA or value["python"] != ARGV[0]:
        raise InstallerError("UNSUPPORTED_HOST")
    runtime = Path(value["runtime_directory"])
    runtime_descriptor = None
    try:
        runtime_descriptor = _open_path(runtime, directory=True)
        runtime_metadata = os.fstat(runtime_descriptor)
    except (OSError, TypeError, InstallerError) as exc:
        raise InstallerError("UNSAFE_RUNTIME_CONFIG") from exc
    finally:
        if runtime_descriptor is not None:
            os.close(runtime_descriptor)
    if not _safe_directory_info(runtime_metadata, final=True):
        raise InstallerError("UNSAFE_RUNTIME_CONFIG")
    environment = value["environment"]
    if not isinstance(environment, dict) or len(environment) > 64:
        raise InstallerError("INVALID_RUNTIME_CONFIG")
    for name, item in environment.items():
        if (
            not isinstance(name, str)
            or not ENV_NAME.fullmatch(name)
            or name == "FACTORY_SOCKET_PATH"
            or not isinstance(item, str)
            or not item
            or len(item) > 8192
            or "\x00" in item
        ):
            raise InstallerError("INVALID_RUNTIME_CONFIG")
    return value


def _boot_id() -> str:
    value = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    if not re.fullmatch(r"[0-9a-f-]{36}", value):
        raise InstallerError("RUNTIME_IDENTITY_UNAVAILABLE")
    return value


def _process_identity(pid: int) -> tuple[str, tuple[str, ...]]:
    try:
        fields = (Path("/proc") / str(pid) / "stat").read_text().split()
        raw = (Path("/proc") / str(pid) / "cmdline").read_bytes()
        argv = tuple(item.decode() for item in raw.rstrip(b"\0").split(b"\0"))
        if len(fields) < 22 or not fields[21].isdigit() or not argv:
            raise ValueError
        return fields[21], argv
    except (OSError, UnicodeError, ValueError) as exc:
        raise InstallerError("RUNTIME_IDENTITY_UNAVAILABLE") from exc


def _process_groups() -> set[int]:
    groups = set()
    try:
        entries = Path("/proc").iterdir()
        for entry in entries:
            if not entry.name.isdigit():
                continue
            try:
                raw = (entry / "stat").read_text()
                tail = raw[raw.rfind(")") + 2:].split()
                if len(tail) >= 3 and tail[2].isdigit():
                    groups.add(int(tail[2]))
            except (OSError, ValueError):
                continue
    except OSError as exc:
        raise InstallerError("RUNTIME_IDENTITY_UNAVAILABLE") from exc
    return groups


class LinuxProcessRuntimeAdapter:
    """Own one exact, unprivileged child process per immutable release."""

    def __init__(self, root: Path, config: Path):
        self.root = Path(root)
        self.config_path = Path(config)
        self.config = _private_config(self.config_path, self.root)
        self.runtime_directory = Path(self.config["runtime_directory"])
        self._runtime_fd = _open_path(self.runtime_directory, directory=True)
        if not _safe_directory_info(os.fstat(self._runtime_fd), final=True):
            os.close(self._runtime_fd)
            raise InstallerError("UNSAFE_RUNTIME_CONFIG")
        self._children: dict[int, subprocess.Popen] = {}

    def _paths(self, release: Path) -> tuple[Path, Path, Path]:
        release = Path(release)
        if release.parent != self.root / "releases" or not HEX.fullmatch(release.name):
            raise InstallerError("INVALID_RELEASE")
        state = self.root / "state" / "process"
        state.mkdir(mode=0o700, exist_ok=True)
        if stat.S_IMODE(state.stat().st_mode) != 0o700 or state.stat().st_uid != os.getuid():
            raise InstallerError("UNSAFE_INSTALLATION")
        # AF_UNIX is commonly limited to 108 bytes; the full identity stays in the
        # authenticated PID record while its collision-resistant prefix bounds the socket path.
        socket_path = Path("/proc/self/fd") / str(self._runtime_fd) / ("p-" + release.name[:16] + ".sock")
        return state / (release.name + ".json"), socket_path, self.root / "logs" / (release.name + ".log")

    def _log(self, path: Path, event: str | None = None) -> bytes:
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        try:
            metadata = os.fstat(descriptor)
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                    or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600):
                raise InstallerError("UNSAFE_INSTALLATION")
            size = metadata.st_size
            if size > MAX_LOG_BYTES:
                os.lseek(descriptor, -MAX_LOG_BYTES, os.SEEK_END)
                tail = os.read(descriptor, MAX_LOG_BYTES)
                os.ftruncate(descriptor, 0)
                os.lseek(descriptor, 0, os.SEEK_SET)
                os.write(descriptor, tail)
                size = len(tail)
            if event is not None:
                payload = (event + "\n").encode()
                if size + len(payload) > MAX_LOG_BYTES:
                    keep = max(0, MAX_LOG_BYTES - len(payload))
                    os.lseek(descriptor, -keep, os.SEEK_END)
                    tail = os.read(descriptor, keep)
                    os.ftruncate(descriptor, 0)
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    os.write(descriptor, tail)
                os.lseek(descriptor, 0, os.SEEK_END)
                os.write(descriptor, payload)
                os.fsync(descriptor)
            os.lseek(descriptor, 0, os.SEEK_SET)
            return os.read(descriptor, MAX_LOG_BYTES)
        finally:
            os.close(descriptor)

    def _record(self, release: Path) -> dict | None:
        record_path, _, _ = self._paths(release)
        if not record_path.exists():
            return None
        value = _json(_read(record_path, 16_384))
        if (
            set(value) != {"schema_version", "release", "pid", "pgid", "boot_id", "start_time", "argv", "argv_sha256"}
            or value["schema_version"] != "factory-process/v1"
            or value["release"] != release.name
            or type(value["pid"]) is not int
            or value["pid"] < 2
            or type(value["pgid"]) is not int
            or value["pgid"] != value["pid"]
            or value["pgid"] == os.getpgrp()
            or not isinstance(value["start_time"], str)
            or value["argv"] != list(ARGV)
            or value["argv_sha256"] != hashlib.sha256(b"\0".join(item.encode() for item in ARGV)).hexdigest()
        ):
            raise InstallerError("RUNTIME_IDENTITY_MISMATCH")
        return value

    def _group_exists(self, record: dict) -> bool:
        if record["boot_id"] != _boot_id():
            raise InstallerError("RUNTIME_IDENTITY_MISMATCH")
        if record["pgid"] < 2 or record["pgid"] == os.getpgrp() or record["pgid"] != record["pid"]:
            raise InstallerError("RUNTIME_IDENTITY_MISMATCH")
        if (Path("/proc") / str(record["pid"])).exists():
            self._matches(record)
        return record["pgid"] in _process_groups()

    def _open_group(self, record: dict) -> dict[int, int]:
        """Pin every current group member; a missing leader is never signalled."""
        if not self._group_exists(record) or not (Path("/proc") / str(record["pid"])).exists():
            raise InstallerError("RUNTIME_LEADER_REQUIRED")
        self._matches(record)
        pinned = {}
        try:
            for entry in Path("/proc").iterdir():
                if not entry.name.isdigit():
                    continue
                try:
                    raw = (entry / "stat").read_text()
                    tail = raw[raw.rfind(")") + 2:].split()
                    if len(tail) < 3 or int(tail[2]) != record["pgid"]:
                        continue
                    pid = int(entry.name)
                    descriptor = os.pidfd_open(pid, 0)
                    current = (Path("/proc") / str(pid) / "stat").read_text()
                    current_tail = current[current.rfind(")") + 2:].split()
                    if len(current_tail) < 3 or int(current_tail[2]) != record["pgid"]:
                        os.close(descriptor)
                        raise InstallerError("RUNTIME_IDENTITY_MISMATCH")
                    pinned[pid] = descriptor
                except FileNotFoundError:
                    continue
            if record["pid"] not in pinned:
                raise InstallerError("RUNTIME_LEADER_REQUIRED")
            return pinned
        except BaseException:
            for descriptor in pinned.values():
                os.close(descriptor)
            raise

    @staticmethod
    def _signal_pinned(pinned: dict[int, int], signal_number: int) -> None:
        for descriptor in pinned.values():
            try:
                signal.pidfd_send_signal(descriptor, signal_number)
            except ProcessLookupError:
                pass

    def _extend_pinned_group(self, record: dict, pinned: dict[int, int]) -> None:
        """Pin members that appeared after the prior snapshot before signalling them."""
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit() or int(entry.name) in pinned:
                continue
            try:
                raw = (entry / "stat").read_text()
                tail = raw[raw.rfind(")") + 2:].split()
                if len(tail) < 3 or int(tail[2]) != record["pgid"]:
                    continue
                pid = int(entry.name)
                descriptor = os.pidfd_open(pid, 0)
                current = (Path("/proc") / str(pid) / "stat").read_text()
                current_tail = current[current.rfind(")") + 2:].split()
                if len(current_tail) < 3 or int(current_tail[2]) != record["pgid"]:
                    os.close(descriptor)
                    raise InstallerError("RUNTIME_IDENTITY_MISMATCH")
                pinned[pid] = descriptor
            except FileNotFoundError:
                continue

    def _matches(self, record: dict) -> bool:
        try:
            start_time, argv = _process_identity(record["pid"])
        except InstallerError as exc:
            if exc.code == "RUNTIME_IDENTITY_UNAVAILABLE" and not (Path("/proc") / str(record["pid"])).exists():
                child = self._children.pop(record["pid"], None)
                if child is not None:
                    child.poll()
                return False
            raise
        if record["boot_id"] != _boot_id() or record["start_time"] != start_time or argv != ARGV:
            raise InstallerError("RUNTIME_IDENTITY_MISMATCH")
        return True

    def preflight(self, profile: str, timeout: int) -> bool:
        return profile == PROFILE and 0 < timeout <= 30 and _host_supported(self.config["python"], timeout=min(timeout, 5))

    def start(self, release: Path, timeout: int) -> None:
        if not self.preflight(PROFILE, timeout):
            raise InstallerError("UNSUPPORTED_HOST")
        record_path, socket_path, log_path = self._paths(release)
        prior = self._record(release)
        if prior is not None:
            if self._group_exists(prior):
                raise InstallerError("RUNTIME_ALREADY_RUNNING")
        record_path.unlink(missing_ok=True)
        socket_path.unlink(missing_ok=True)
        self._log(log_path, "starting " + release.name)
        environment = {
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(release / "app") + ":" + str(release / "site-packages"),
            "FACTORY_SOCKET_PATH": str(socket_path),
            **self.config["environment"],
        }
        process = subprocess.Popen(
            list(ARGV), cwd=release, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, close_fds=True,
            pass_fds=(self._runtime_fd,), start_new_session=True,
        )
        try:
            start_time, actual_argv = _process_identity(process.pid)
            pgid = os.getpgid(process.pid)
            if actual_argv != ARGV or pgid != process.pid or pgid == os.getpgrp():
                raise InstallerError("RUNTIME_IDENTITY_MISMATCH")
            _atomic_json(record_path, {
                "schema_version": "factory-process/v1", "release": release.name,
                "pid": process.pid, "pgid": pgid, "boot_id": _boot_id(), "start_time": start_time,
                "argv": list(ARGV),
                "argv_sha256": hashlib.sha256(b"\0".join(item.encode() for item in ARGV)).hexdigest(),
            })
            self._children[process.pid] = process
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise InstallerError("RUNTIME_FAILED")
                if socket_path.exists():
                    self._log(log_path, "started " + release.name)
                    return
                time.sleep(0.02)
            raise InstallerError("RUNTIME_TIMEOUT")
        except BaseException:
            pgid = process.pid
            if pgid > 1 and pgid != os.getpgrp() and pgid in _process_groups():
                os.killpg(pgid, signal.SIGTERM)
                deadline = time.monotonic() + 1
                while time.monotonic() < deadline and pgid in _process_groups():
                    process.poll()
                    time.sleep(0.02)
                if pgid in _process_groups():
                    os.killpg(pgid, signal.SIGKILL)
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)
            record_path.unlink(missing_ok=True)
            socket_path.unlink(missing_ok=True)
            self._children.pop(process.pid, None)
            self._log(log_path, "start-failed " + release.name)
            raise

    def status(self, release: Path, timeout: int) -> bool:
        if not 0 < timeout <= 30:
            raise InstallerError("RUNTIME_TIMEOUT")
        record = self._record(release)
        return record is not None and self._group_exists(record)

    def health(self, release: Path, timeout: int) -> bool:
        if not self.status(release, timeout):
            return False
        _, socket_path, _ = self._paths(release)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                with socket.socket(socket.AF_UNIX) as client:
                    client.settimeout(max(0.01, deadline - time.monotonic()))
                    client.connect(str(socket_path))
                    client.sendall(b"GET /health/ready HTTP/1.1\r\nHost: factory.local\r\nConnection: close\r\n\r\n")
                    chunks = []
                    total = 0
                    while total < 65_536:
                        chunk = client.recv(min(4096, 65_536 - total))
                        if not chunk:
                            break
                        chunks.append(chunk)
                        total += len(chunk)
                    response = b"".join(chunks)
                return response.startswith(b"HTTP/1.1 200 ") and b'"status":"ok"' in response
            except OSError:
                time.sleep(0.02)
        return False

    def stop(self, release: Path, timeout: int) -> None:
        record_path, socket_path, _ = self._paths(release)
        record = self._record(release)
        if record is None:
            return
        if not self._group_exists(record):
            record_path.unlink(missing_ok=True)
            socket_path.unlink(missing_ok=True)
            return
        pinned = self._open_group(record)
        try:
            self._signal_pinned(pinned, signal.SIGTERM)
            child = self._children.get(record["pid"])
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline and record["pgid"] in _process_groups():
                try:
                    if child is not None:
                        child.poll()
                    else:
                        os.waitpid(record["pid"], os.WNOHANG)
                except ChildProcessError:
                    pass
                time.sleep(0.02)
            # A TERM handler may fork another same-group process after the first
            # snapshot. Re-enumerate and pin to a bounded fixed point; keeping the
            # validated leader pidfd open prevents its PID/PGID identity being reused.
            kill_deadline = time.monotonic() + 1
            while record["pgid"] in _process_groups() and time.monotonic() < kill_deadline:
                self._extend_pinned_group(record, pinned)
                self._signal_pinned(pinned, signal.SIGKILL)
                if child is not None:
                    child.poll()
                time.sleep(0.02)
            if record["pgid"] in _process_groups():
                raise InstallerError("RUNTIME_STOP_FAILED")
            if child is not None:
                child.poll()
        finally:
            for descriptor in pinned.values():
                os.close(descriptor)
        record_path.unlink(missing_ok=True)
        socket_path.unlink(missing_ok=True)
        self._children.pop(record["pid"], None)
        self._log(self._paths(release)[2], "stopped " + release.name)

    def logs(self, release: Path, lines: int, maximum_bytes: int, timeout: int) -> str:
        del timeout
        if not 1 <= lines <= 1000 or not 1 <= maximum_bytes <= 65_536:
            raise InstallerError("INVALID_LOG_LIMIT")
        _, _, log_path = self._paths(release)
        if not log_path.exists():
            return ""
        content = self._log(log_path)[-maximum_bytes:]
        return "\n".join(content.decode("utf-8", "replace").splitlines()[-lines:])
