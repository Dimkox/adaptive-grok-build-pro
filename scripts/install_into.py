from __future__ import annotations

import argparse
import os
import stat
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.repo import detect_repo
from adaptive_grok.toolchain import pull_dependencies

MANAGED_DIRS = ('.grok', '.agents', '.grok-stack')
MANAGED_FILES = (
    'scripts/grok_architecture.py',
    'scripts/grok_route.py',
    'scripts/grok_change.py',
    'scripts/grok_spec.py',
    'scripts/grok_verify.py',
    'scripts/grok_review.py',
    'scripts/grok_approve.py',
    'scripts/grok_doctor.py',
    'scripts/grok_status.py',
    'scripts/grok_deploy.py',
    'session_start.py',
    'user_prompt_submit.py',
    'pre_tool_use.py',
    'post_tool_use.py',
    'pre_compact.py',
    'subagent_start.py',
    'subagent_stop.py',
    'stop_gate.py',
    'session_end.py',
    'ruff.toml',
    'bandit.yaml',
    '.coveragerc',
    'schemas/change-spec.schema.json',
    'schemas/change-spec-v1.schema.json',
    'schemas/architecture-system.schema.json',
    'schemas/architecture-rules.schema.json',
)
SKIP_PREFIXES = ('.grok-stack/runtime/',)
TARGET_OWNED_ARCHITECTURE = frozenset({
    'architecture/adoption.json',
    'architecture/rules.yaml',
    'architecture/system.yaml',
})
MANAGED_START = '<!-- ADAPTIVE-GROK-PRO:START -->'
MANAGED_END = '<!-- ADAPTIVE-GROK-PRO:END -->'
MAX_TARGET_FILE_BYTES = 16 * 1024 * 1024


class UnsafeInstallTarget(RuntimeError):
    pass


def _identity(value: os.stat_result) -> tuple[int, int, int]:
    return value.st_dev, value.st_ino, value.st_mode


class _TargetTree:
    def __init__(self, root: Path) -> None:
        self.root = root.absolute()
        self.root.mkdir(parents=True, exist_ok=True)
        nofollow = getattr(os, 'O_NOFOLLOW', 0)
        directory = getattr(os, 'O_DIRECTORY', 0)
        if not nofollow or not directory:
            raise UnsafeInstallTarget('safe no-follow directory operations are unavailable')
        metadata = os.lstat(self.root)
        if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise UnsafeInstallTarget('installation target must be a real directory')
        self.fd = os.open(self.root, os.O_RDONLY | directory | nofollow)
        if _identity(os.fstat(self.fd)) != _identity(metadata):
            os.close(self.fd)
            raise UnsafeInstallTarget('installation target changed while opening')
        self.identity = _identity(metadata)

    def close(self) -> None:
        os.close(self.fd)

    def __enter__(self) -> '_TargetTree':
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    @staticmethod
    def _parts(relative: str) -> tuple[str, ...]:
        path = Path(relative)
        if path.is_absolute() or not path.parts or any(part in {'', '.', '..'} for part in path.parts):
            raise UnsafeInstallTarget(f'unsafe managed path: {relative}')
        return path.parts

    def _check_root(self) -> None:
        try:
            current = os.lstat(self.root)
        except OSError as exc:
            raise UnsafeInstallTarget(f'installation target is unavailable: {exc}') from exc
        if _identity(current) != self.identity or _identity(os.fstat(self.fd)) != self.identity:
            raise UnsafeInstallTarget('installation target changed during operation')

    def _open_dir(self, parts: tuple[str, ...], *, create: bool) -> int:
        self._check_root()
        descriptor = os.dup(self.fd)
        try:
            for component in parts:
                try:
                    metadata = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
                except FileNotFoundError:
                    if not create:
                        raise
                    os.mkdir(component, mode=0o755, dir_fd=descriptor)
                    metadata = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
                if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
                    raise UnsafeInstallTarget(
                        f'managed path ancestor is not a real directory: {component}'
                    )
                child = os.open(
                    component,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=descriptor,
                )
                if _identity(os.fstat(child)) != _identity(metadata):
                    os.close(child)
                    raise UnsafeInstallTarget('managed path ancestor changed while opening')
                os.close(descriptor)
                descriptor = child
            return descriptor
        except Exception:
            os.close(descriptor)
            raise

    def ensure_dir(self, relative: str, *, dry_run: bool = False) -> None:
        parts = self._parts(relative)
        if dry_run:
            try:
                descriptor = self._open_dir(parts, create=False)
            except FileNotFoundError:
                return
        else:
            descriptor = self._open_dir(parts, create=True)
        os.close(descriptor)

    def is_dir(self, relative: str) -> bool:
        try:
            descriptor = self._open_dir(self._parts(relative), create=False)
        except FileNotFoundError:
            return False
        os.close(descriptor)
        return True

    def _file(self, relative: str) -> tuple[int, str, os.stat_result | None]:
        parts = self._parts(relative)
        try:
            parent = self._open_dir(parts[:-1], create=False)
        except FileNotFoundError:
            return -1, parts[-1], None
        try:
            metadata = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            metadata = None
        if metadata is not None and not stat.S_ISREG(metadata.st_mode):
            os.close(parent)
            raise UnsafeInstallTarget(f'managed destination is not a regular file: {relative}')
        return parent, parts[-1], metadata

    def _read_details(self, relative: str) -> tuple[bytes, int] | None:
        parent, name, metadata = self._file(relative)
        if metadata is None:
            if parent >= 0:
                os.close(parent)
            return None
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
        os.close(parent)
        try:
            opened = os.fstat(descriptor)
            if _identity(opened) != _identity(metadata) or opened.st_size > MAX_TARGET_FILE_BYTES:
                raise UnsafeInstallTarget(f'managed destination changed or is oversized: {relative}')
            chunks: list[bytes] = []
            remaining = opened.st_size
            while remaining:
                chunk = os.read(descriptor, min(65_536, remaining))
                if not chunk:
                    raise UnsafeInstallTarget(f'managed destination was truncated: {relative}')
                chunks.append(chunk)
                remaining -= len(chunk)
            after = os.fstat(descriptor)
            if (
                _identity(after) != _identity(opened)
                or after.st_size != opened.st_size
                or after.st_mtime_ns != opened.st_mtime_ns
                or after.st_ctime_ns != opened.st_ctime_ns
            ):
                raise UnsafeInstallTarget(f'managed destination changed while reading: {relative}')
            return b''.join(chunks), stat.S_IMODE(opened.st_mode)
        finally:
            os.close(descriptor)

    def read(self, relative: str) -> bytes | None:
        details = self._read_details(relative)
        return None if details is None else details[0]

    def _stage(self, content: bytes, mode: int) -> str:
        for _ in range(32):
            name = f'.adaptive-install-{uuid.uuid4().hex}'
            try:
                descriptor = os.open(
                    name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    mode,
                    dir_fd=self.fd,
                )
            except FileExistsError:
                continue
            try:
                view = memoryview(content)
                while view:
                    written = os.write(descriptor, view)
                    view = view[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            return name
        raise UnsafeInstallTarget('cannot allocate a contained installer staging file')

    def write(self, relative: str, content: bytes, *, mode: int = 0o644) -> None:
        parts = self._parts(relative)
        initial_parent = self._open_dir(parts[:-1], create=True)
        initial_identity = _identity(os.fstat(initial_parent))
        original_details = self._read_details(relative)
        original = None if original_details is None else original_details[0]
        original_mode = mode if original_details is None else original_details[1]
        stage = self._stage(content, mode)
        published_parent = -1
        try:
            published_parent = self._open_dir(parts[:-1], create=False)
            if _identity(os.fstat(published_parent)) != initial_identity:
                raise UnsafeInstallTarget(f'managed destination parent changed: {relative}')
            os.replace(stage, parts[-1], src_dir_fd=self.fd, dst_dir_fd=published_parent)
            stage = ''
            try:
                current_parent = self._open_dir(parts[:-1], create=False)
            except FileNotFoundError as exc:
                current_parent = -1
                changed = True
                change_exc: Exception = exc
            else:
                changed = _identity(os.fstat(current_parent)) != initial_identity
                change_exc = UnsafeInstallTarget(f'managed destination parent relocated: {relative}')
                os.close(current_parent)
            if changed:
                if original is None:
                    os.unlink(parts[-1], dir_fd=published_parent)
                else:
                    rollback = self._stage(original, original_mode)
                    os.replace(
                        rollback,
                        parts[-1],
                        src_dir_fd=self.fd,
                        dst_dir_fd=published_parent,
                    )
                raise UnsafeInstallTarget(str(change_exc))
            os.fsync(published_parent)
        finally:
            os.close(initial_parent)
            if published_parent >= 0:
                os.close(published_parent)
            if stage:
                try:
                    os.unlink(stage, dir_fd=self.fd)
                except FileNotFoundError:
                    pass


def iter_source_files(source: Path) -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for dirname in MANAGED_DIRS:
        base = source / dirname
        if not base.is_dir():
            continue
        for path in base.rglob('*'):
            if not path.is_file():
                continue
            rel = path.relative_to(source).as_posix()
            if rel in TARGET_OWNED_ARCHITECTURE:
                continue
            if rel.endswith('/__pycache__') or '/__pycache__/' in rel or rel.endswith('.pyc'):
                continue
            if any(rel.startswith(prefix) and not rel.endswith('.gitkeep') for prefix in SKIP_PREFIXES):
                continue
            files.append((rel, path))
    files.extend(
        (rel, source / rel)
        for rel in MANAGED_FILES
        if rel not in TARGET_OWNED_ARCHITECTURE
    )
    return sorted(files)


def different(left: Path, tree: _TargetTree, relative: str) -> bool:
    right = tree.read(relative)
    return right is not None and left.read_bytes() != right


def managed_agents_text(source: Path) -> str:
    core = (source / 'AGENTS.md').read_text(encoding='utf-8').rstrip()
    return f'\n{MANAGED_START}\n{core}\n{MANAGED_END}\n'


def merge_agents(source: Path, target: Path, tree: _TargetTree, dry_run: bool) -> None:
    agent_file = target / 'AGENTS.md'
    existing_bytes = tree.read('AGENTS.md')
    existing = existing_bytes.decode('utf-8') if existing_bytes is not None else ''
    block = managed_agents_text(source)
    if MANAGED_START in existing and MANAGED_END in existing:
        before, rest = existing.split(MANAGED_START, 1)
        _, after = rest.split(MANAGED_END, 1)
        merged = before.rstrip() + block + after.lstrip()
    else:
        merged = existing.rstrip() + block
    print(f'UPDATE {agent_file}')
    if not dry_run:
        tree.write('AGENTS.md', merged.encode('utf-8'))


def install(
    source: Path,
    target: Path,
    *,
    force: bool,
    dry_run: bool,
    with_ci: bool = False,
    install_deps: bool = True,
    all_deps: bool = False,
    runner=None,
) -> None:
    if with_ci:
        raise SystemExit(
            'GitHub Actions is forbidden. Use local `make verify` / '
            '`python3 scripts/grok_verify.py --mode pr`.'
        )
    with _TargetTree(target) as tree:
        source_files = iter_source_files(source)
        conflicts = [rel for rel, src in source_files if different(src, tree, rel)]
        if conflicts and not force:
            formatted = '\n'.join(f'  - {item}' for item in conflicts[:50])
            extra = '' if len(conflicts) <= 50 else f'\n  ... and {len(conflicts) - 50} more'
            raise SystemExit(
                'Adaptive Grok managed files already exist with different content. '
                'Review them, back up the repository, then rerun with --force to overwrite only these files.\n'
                + formatted + extra
            )

        for rel, src in source_files:
            current = tree.read(rel)
            content = src.read_bytes()
            action = 'OVERWRITE' if current is not None and current != content else (
                'KEEP' if current is not None else 'COPY'
            )
            print(f'{action} {rel}')
            if dry_run or action == 'KEEP':
                continue
            tree.write(rel, content, mode=src.stat().st_mode & 0o777)

        merge_agents(source, target, tree, dry_run)

        profile = detect_repo(target)
        if profile.kind == 'bitrix' and tree.is_dir('local'):
            local_agents = target / 'local/AGENTS.md'
            bitrix_block = (source / 'docs/bitrix-local-AGENTS.md').read_bytes()
            existing = tree.read('local/AGENTS.md')
            if existing is None:
                print(f'CREATE {local_agents.relative_to(target)}')
                if not dry_run:
                    tree.write('local/AGENTS.md', bitrix_block)
            elif bitrix_block not in existing:
                print(f'NOTICE {local_agents.relative_to(target)} exists; Bitrix-local guidance was not overwritten.')

        for rel in (
            'engineering/changes',
            'engineering/adr',
            'engineering/runbooks',
            'engineering/reviews',
            'engineering/contracts/openapi',
            'engineering/contracts/asyncapi',
            'engineering/contracts/schemas',
        ):
            print(f'ENSURE {rel}')
            tree.ensure_dir(rel, dry_run=dry_run)

        pin_root = target if tree.read('.grok-stack/config/toolchain.json') is not None else source

    print(f'Detected target profile: {profile.kind}; domains={profile.domains}; modules={profile.bitrix_modules}')

    dep_results = pull_dependencies(
        pin_root,
        apply=install_deps,
        include_optional=all_deps,
        dry_run=dry_run,
        runner=runner,
    )
    for item in dep_results:
        action = item.get('action')
        tool_id = item.get('id')
        command = item.get('command') or ''
        if action == 'skip-optional':
            print(f'SKIP optional {tool_id}')
        elif action == 'skip-disabled':
            print(f'SKIP deps {tool_id}: {command}')
        elif action == 'would-install':
            print(f'WOULD INSTALL {tool_id}: {command}')
        elif action == 'manual-url':
            print(f'MANUAL {tool_id}: {command}')
        elif action == 'install':
            print(f'{"INSTALLED" if item.get("ok") else "INSTALL FAILED"} {tool_id}: {command}')
        else:
            print(f'DEPS {tool_id}: {action}')


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Install Adaptive Grok Build Pro into an existing repository without deleting unrelated agent configuration.'
    )
    parser.add_argument('target')
    parser.add_argument('--force', action='store_true', help='Overwrite conflicting Adaptive Grok managed files only.')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument(
        '--with-ci',
        action='store_true',
        help='Forbidden. Never GitHub Actions; use local python3 scripts/grok_verify.py --mode pr.',
    )
    parser.add_argument('--no-deps', action='store_true', help='Do not install missing required toolchain tools.')
    parser.add_argument('--all-deps', action='store_true', help='Also install optional profile tools (php, node, gh, …).')
    args = parser.parse_args()
    install(
        ROOT,
        Path(args.target).resolve(),
        force=args.force,
        dry_run=args.dry_run,
        with_ci=args.with_ci,
        install_deps=not args.no_deps,
        all_deps=args.all_deps,
    )


if __name__ == '__main__':
    main()
