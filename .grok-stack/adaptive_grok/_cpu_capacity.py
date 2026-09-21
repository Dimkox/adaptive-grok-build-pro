"""Bounded Linux cgroup quota discovery for the optional test runner.

None means every visible applicable quota is unlimited or absent. Unknown
membership, unreadable/malformed controls, and exhausted bounds return one.
Only ancestors exposed by the process's matching mounts can be inspected.
"""
from __future__ import annotations

from pathlib import Path
import re


_PROC_LIMIT = 1024 * 1024
_CONTROL_LIMIT = 4096
_MAX_LINES = 4096
_MAX_DEPTH = 256
_MAX_MOUNTS = 64
_MAX_READS = 1024
_ESCAPES = {'040': ' ', '011': '\t', '012': '\n', '134': '\\'}


def _read_text(path: Path, limit: int) -> str:
    with path.open('rb') as source:
        value = source.read(limit + 1)
    if len(value) > limit:
        raise ValueError('capacity input exceeds its bound')
    return value.decode('utf-8')


def _components(path: str) -> tuple[str, ...]:
    if not path.startswith('/') or '\0' in path or len(path) > 4096:
        raise ValueError('capacity path is not a bounded absolute path')
    parts = tuple(path[1:].split('/')) if path != '/' else ()
    if len(parts) > _MAX_DEPTH or any(part in {'', '.', '..'} for part in parts):
        raise ValueError('capacity path is ambiguous or too deep')
    return parts


def _mount_path(value: str) -> tuple[str, ...]:
    if re.search(r'\\(?!040|011|012|134)', value):
        raise ValueError('unsupported mount path escape')
    return _components(re.sub(r'\\(040|011|012|134)', lambda match: _ESCAPES[match[1]], value))


def _lines(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines or len(lines) > _MAX_LINES:
        raise ValueError('capacity metadata is empty or too large')
    return lines


def _membership(text: str) -> tuple[str, tuple[str, ...]]:
    cpu: list[str] = []
    unified: list[str] = []
    for line in _lines(text):
        fields = line.split(':', 2)
        if len(fields) != 3 or not fields[0].isascii() or not fields[0].isdecimal():
            raise ValueError('malformed cgroup membership')
        hierarchy, controllers, path = fields
        if (hierarchy == '0') != (not controllers):
            raise ValueError('malformed cgroup hierarchy/controller pair')
        if 'cpu' in controllers.split(','):
            cpu.append(path)
        if hierarchy == '0' and not controllers:
            unified.append(path)
    # On hybrid hosts the CPU controller can belong to v1, independently of
    # the process's membership in the unified hierarchy.
    selected = cpu if cpu else unified
    if len(selected) != 1:
        raise ValueError('CPU cgroup membership is unresolved')
    return ('cgroup' if cpu else 'cgroup2'), _components(selected[0])


def _mounts(text: str, kind: str, membership: tuple[str, ...]) -> list[tuple[Path, tuple[str, ...]]]:
    result: list[tuple[Path, tuple[str, ...]]] = []
    devices: set[str] = set()
    locations: dict[tuple[str, ...], tuple[str, ...]] = {}
    for line in _lines(text):
        before, separator, after = line.partition(' - ')
        fields, filesystem = before.split(), after.split()
        if not separator or len(fields) < 6 or len(filesystem) != 3:
            raise ValueError('malformed mount metadata')
        if filesystem[0] != kind:
            continue
        if kind == 'cgroup' and 'cpu' not in filesystem[2].split(','):
            continue
        identifiers = [fields[0], fields[1], *fields[2].split(':')]
        if len(identifiers) != 4 or any(not item.isascii() or not item.isdecimal() for item in identifiers):
            raise ValueError('malformed cgroup mount identity')
        mount_root, mountpoint = _mount_path(fields[3]), _mount_path(fields[4])
        devices.add(fields[2])
        if len(devices) > 1 or (mountpoint in locations and locations[mountpoint] != mount_root):
            raise ValueError('CPU cgroup mounts are ambiguous')
        locations[mountpoint] = mount_root
        if membership[:len(mount_root)] != mount_root:
            continue
        result.append((Path('/').joinpath(*mountpoint), membership[len(mount_root):]))
        if len(result) > _MAX_MOUNTS:
            raise ValueError('too many CPU cgroup mounts')
    if not result:
        raise ValueError('CPU cgroup has no visible matching mount')
    return result


def _positive(value: str) -> int:
    if not value.isascii() or not value.isdecimal() or len(value) > 20:
        raise ValueError('invalid cgroup quota number')
    number = int(value)
    if number <= 0:
        raise ValueError('nonpositive cgroup quota number')
    return number


def _quota(quota: str, period: str, unlimited: str) -> int | None:
    interval = _positive(period)
    if quota == unlimited:
        return None
    # Flooring is an intentionally conservative worker policy, not a claim
    # that this bandwidth is reserved or that process/PID capacity is free.
    return max(1, _positive(quota) // interval)


def linux_quota_capacity() -> int | None:
    """Return the minimum visible quota, or one for unknown capacity."""
    try:
        membership_text = _read_text(Path('/proc/self/cgroup'), _PROC_LIMIT)
        mount_text = _read_text(Path('/proc/self/mountinfo'), _PROC_LIMIT)
        kind, membership = _membership(membership_text)
        mounts = _mounts(mount_text, kind, membership)
        capacities: list[int] = []
        visited: set[Path] = set()
        reads = 0
        for mountpoint, relative in mounts:
            # Inspect all matching mounts: a bind subtree must not conceal
            # a tighter parent exposed through another mount of this hierarchy.
            for depth in range(len(relative), -1, -1):
                group = mountpoint.joinpath(*relative[:depth])
                if group in visited:
                    continue
                visited.add(group)
                reads += 1 if kind == 'cgroup2' else 2
                if reads > _MAX_READS:
                    raise ValueError('CPU cgroup ancestor reads exceed their bound')
                if kind == 'cgroup2':
                    try:
                        fields = _read_text(group / 'cpu.max', _CONTROL_LIMIT).split()
                    except FileNotFoundError:
                        # v2 roots and groups with no enabled CPU controller
                        # legitimately lack cpu.max; still inspect parents.
                        continue
                    if len(fields) != 2:
                        raise ValueError('malformed v2 quota')
                    capacity = _quota(fields[0], fields[1], 'max')
                else:
                    quota = _read_text(group / 'cpu.cfs_quota_us', _CONTROL_LIMIT).strip()
                    period = _read_text(group / 'cpu.cfs_period_us', _CONTROL_LIMIT).strip()
                    capacity = _quota(quota, period, '-1')
                if capacity is not None:
                    capacities.append(capacity)
        return min(capacities) if capacities else None
    except (OSError, UnicodeError, ValueError):
        return 1
