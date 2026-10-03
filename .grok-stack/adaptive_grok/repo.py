from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .util import unique_ordered


# Shared inventory/read budgets. Depth counts directories below the root.
# Discard an overflowing directory in full: enumeration order must not choose
# which languages survive. One extra entry distinguishes exact-bound listings.
SOURCE_SCAN_MAX_FILES = 4000
SOURCE_SCAN_MAX_BYTES = 8 * 1024 * 1024
SOURCE_SCAN_MAX_DEPTH = 16
SOURCE_SCAN_MAX_DIRS = 1024
SOURCE_SCAN_MAX_ENTRIES = 20_000
SOURCE_SCAN_MAX_ENTRIES_PER_DIR = 4000
MANIFEST_MAX_BYTES = 64 * 1024
SOURCE_MAX_FILE_BYTES = 64 * 1024

SOURCE_LANGUAGE_EXTENSIONS = {
    '.swift': 'swift', '.py': 'python', '.pyi': 'python', '.php': 'php',
    '.go': 'go', '.rs': 'rust', '.kt': 'kotlin', '.kts': 'kotlin',
    '.java': 'java', '.js': 'javascript', '.jsx': 'javascript',
    '.mjs': 'javascript', '.cjs': 'javascript', '.ts': 'typescript',
    '.tsx': 'typescript', '.c': 'c', '.h': 'c', '.cc': 'cpp',
    '.cpp': 'cpp', '.cxx': 'cpp', '.hpp': 'cpp', '.hh': 'cpp',
    '.m': 'objective-c', '.mm': 'objective-c', '.cs': 'csharp', '.rb': 'ruby',
}
SCAN_SKIP_DIRS = frozenset({
    'node_modules', 'bower_components', 'vendor', 'pods', 'carthage',
    'sourcepackages', 'checkouts', 'submodules', 'third_party', 'thirdparty',
    'deps', 'dependencies', 'external', 'deriveddata', 'dist', 'build',
    'out', 'obj', 'target', 'generated', 'cmake-build-debug', '__pycache__',
    'site-packages', 'venv', 'virtualenv', 'env',
})
NON_SOURCE_EXTENSIONS = frozenset({
    '.md', '.markdown', '.rst', '.txt', '.adoc', '.png', '.jpg', '.jpeg',
    '.gif', '.webp', '.ico', '.pdf', '.zip', '.tar', '.gz', '.bz2', '.xz',
    '.7z', '.class', '.pyc', '.pyo', '.so', '.dll', '.dylib', '.a', '.o',
    '.obj', '.exe', '.lock', '.sum', '.mod',
})
MANIFEST_LANGUAGES = {
    'composer.json': ('php',), 'package.json': ('javascript', 'typescript'),
    'pyproject.toml': ('python',), 'requirements.txt': ('python',),
    'go.mod': ('go',), 'Cargo.toml': ('rust',), 'Package.swift': ('swift',),
    'openapi.yaml': (), 'openapi.yml': (), 'asyncapi.yaml': (), 'asyncapi.yml': (),
}
MANIFEST_CANONICAL = {name.casefold(): name for name in MANIFEST_LANGUAGES}


@dataclass
class RepoProfile:
    kind: str
    languages: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    bitrix_modules: list[str] = field(default_factory=list)
    package_scripts: list[str] = field(default_factory=list)
    # `languages` keeps confirmed routing evidence; extensions/weak manifests
    # are additive disclosure rather than silent promotion to specialist routes.
    detected_languages: list[str] = field(default_factory=list)
    language_scan: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class _Inventory:
    def __init__(self) -> None:
        self.nodes: set[str] = set()
        self.directory_nodes: set[str] = set()
        self.readable: set[str] = set()
        self.manifests: dict[str, bytes] = {}
        self.manifest_names: dict[str, set[str]] = {}
        self.detected: set[str] = set()
        self.source_counts: dict[str, int] = {}
        self.readable_sources: dict[str, int] = {}
        self.unknown_extensions: dict[str, int] = {}
        self.reasons: set[str] = set()
        self.unreadable: set[str] = set()
        self.symlinks: set[str] = set()
        self.non_regular: set[str] = set()
        self.seen_files: set[str] = set()
        self.files = self.bytes = self.directories = self.entries = 0

    def read(self, parent: int, name: str, relative: str, info: os.stat_result, *, manifest: bool) -> bytes | None:
        limit = MANIFEST_MAX_BYTES if manifest else SOURCE_MAX_FILE_BYTES
        if info.st_size > limit:
            self.reasons.add(f'{"manifest" if manifest else "source"}-bytes:{limit}')
            return None
        if info.st_size > SOURCE_SCAN_MAX_BYTES - self.bytes:
            self.reasons.add(f'bytes:{SOURCE_SCAN_MAX_BYTES}')
            return None
        descriptor = None
        try:
            descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode) or _identity(before) != _identity(info):
                raise OSError('file changed before open')
            chunks: list[bytes] = []
            remaining = info.st_size
            while remaining:
                chunk = os.read(descriptor, min(remaining, 8192))
                if not chunk:
                    raise OSError('file shortened during read')
                self.bytes += len(chunk)
                remaining -= len(chunk)
                chunks.append(chunk)
            if _identity(os.fstat(descriptor)) != _identity(before):
                raise OSError('file changed during read')
            self.readable.add(relative)
            return b''.join(chunks)
        except OSError:
            self.unreadable.add(relative)
            return None
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def file(self, parent: int, name: str, relative: str, info: os.stat_result) -> bool:
        if relative in self.seen_files:
            return True
        if self.files >= SOURCE_SCAN_MAX_FILES:
            self.reasons.add(f'files:{SOURCE_SCAN_MAX_FILES}')
            return False
        self.seen_files.add(relative)
        self.nodes.add(relative)
        self.files += 1
        canonical = MANIFEST_CANONICAL.get(name.casefold()) if '/' not in relative else None
        extension = Path(name).suffix.lower()
        language = SOURCE_LANGUAGE_EXTENSIONS.get(extension)
        if canonical:
            self.manifest_names.setdefault(canonical, set()).add(name)
            self.detected.update(MANIFEST_LANGUAGES[canonical])
        elif language:
            self.detected.add(language)
            self.source_counts[language] = self.source_counts.get(language, 0) + 1
        elif extension and extension not in NON_SOURCE_EXTENSIONS:
            self.unknown_extensions[extension] = self.unknown_extensions.get(extension, 0) + 1
        contract = relative.startswith(('engineering/contracts/openapi/', 'engineering/contracts/asyncapi/')) and extension in {'.yaml', '.yml', '.json'}
        if canonical or language or contract:
            data = self.read(parent, name, relative, info, manifest=bool(canonical or contract))
            if data is not None and canonical and name == canonical:
                self.manifests[canonical] = data
            elif data and language and not canonical:
                # Discover example/test PHP anywhere, but retain the legacy
                # first-party locations required to promote PHP routing.
                php_location = '/' not in relative or relative.split('/', 1)[0] in {'src', 'app', 'local', 'public', 'www'}
                if language != 'php' or php_location:
                    self.readable_sources[language] = self.readable_sources.get(language, 0) + 1
        return True

    def walk(self, descriptor: int, relative: str = '', depth: int = 0) -> None:
        if self.directories >= SOURCE_SCAN_MAX_DIRS:
            self.reasons.add(f'directories:{SOURCE_SCAN_MAX_DIRS}')
            return
        self.directories += 1
        remaining = SOURCE_SCAN_MAX_ENTRIES - self.entries
        limit = min(remaining, SOURCE_SCAN_MAX_ENTRIES_PER_DIR)
        names: list[str] = []
        try:
            with os.scandir(descriptor) as iterator:
                for entry in iterator:
                    if len(names) >= limit:
                        reason = (f'entries:{SOURCE_SCAN_MAX_ENTRIES}' if remaining <= SOURCE_SCAN_MAX_ENTRIES_PER_DIR else f'entries-per-directory:{SOURCE_SCAN_MAX_ENTRIES_PER_DIR}')
                        self.reasons.add(reason)
                        self.entries += len(names)
                        return
                    names.append(entry.name)
        except OSError:
            self.unreadable.add(relative or '.')
            return
        self.entries += len(names)
        for name in sorted(names):
            if name.startswith('.'):
                continue
            path = f'{relative}/{name}' if relative else name
            try:
                info = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode):
                    self.symlinks.add(path)
                elif stat.S_ISDIR(info.st_mode):
                    if name.casefold() in SCAN_SKIP_DIRS:
                        continue
                    self.nodes.add(path)
                    self.directory_nodes.add(path)
                    if depth >= SOURCE_SCAN_MAX_DEPTH:
                        self.reasons.add(f'depth:{SOURCE_SCAN_MAX_DEPTH}')
                        continue
                    if self.directories >= SOURCE_SCAN_MAX_DIRS:
                        self.reasons.add(f'directories:{SOURCE_SCAN_MAX_DIRS}')
                        continue
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                    try:
                        if _identity(os.fstat(child)) != _identity(info):
                            raise OSError('directory changed before open')
                        self.walk(child, path, depth + 1)
                    finally:
                        os.close(child)
                elif stat.S_ISREG(info.st_mode):
                    if not self.file(descriptor, name, path, info):
                        return
                else:
                    self.non_regular.add(path)
            except OSError:
                self.unreadable.add(path)


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _scan(root: Path) -> _Inventory:
    inventory = _Inventory()
    descriptor = None
    try:
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        # Fixed root probes survive oversized listings but consume shared file
        # and read budgets. Listing and probes deduplicate each observed path.
        for name in MANIFEST_LANGUAGES:
            try:
                info = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            except FileNotFoundError:
                continue
            except OSError:
                inventory.unreadable.add(name)
                continue
            if stat.S_ISREG(info.st_mode):
                inventory.file(descriptor, name, name, info)
            elif stat.S_ISLNK(info.st_mode):
                inventory.symlinks.add(name)
            else:
                inventory.non_regular.add(name)
        inventory.walk(descriptor)
    except OSError:
        inventory.unreadable.add('.')
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return inventory


def detect_repo(root: Path) -> RepoProfile:
    inventory = _scan(root)
    signals: list[str] = []
    languages: list[str] = []
    domains: list[str] = []
    bitrix_signals = [item for item in ('bitrix', 'local/modules', 'local/components', 'bitrix/.settings.php', 'bitrix/php_interface/dbconn.php', 'bitrix/modules/main/include/prolog_before.php') if item in inventory.nodes]
    if bitrix_signals:
        signals.extend(f'bitrix:{item}' for item in bitrix_signals)
        domains.extend(['bitrix', 'php'])
        languages.append('php')
    if 'composer.json' in inventory.manifests or inventory.readable_sources.get('php'):
        languages.append('php')
        domains.append('php')
        if 'composer.json' in inventory.manifests:
            signals.append('php:composer.json')
    package_scripts: list[str] = []
    if 'package.json' in inventory.manifests:
        languages.extend(['javascript', 'typescript'])
        domains.append('frontend')
        signals.append('node:package.json')
        try:
            document = json.loads(inventory.manifests['package.json'])
            scripts = document.get('scripts', {}) if isinstance(document, dict) else {}
            if isinstance(scripts, dict):
                package_scripts = sorted(scripts)
        except (ValueError, RecursionError):
            pass
    if {'pyproject.toml', 'requirements.txt'} & inventory.manifests.keys():
        languages.append('python')
        signals.append('python:project')
    if 'go.mod' in inventory.manifests:
        languages.append('go')
        signals.append('go:module')
    if 'Cargo.toml' in inventory.manifests:
        languages.append('rust')
        signals.append('rust:cargo')
    swift = inventory.manifests.get('Package.swift', b'')
    swift_package = bool(re.search(rb'\bimport\s+PackageDescription\b', swift) and re.search(rb'\bPackage\s*\(', swift))
    if swift_package or inventory.readable_sources.get('swift'):
        languages.append('swift')
        if swift_package:
            signals.append('swift:Package.swift')
        if inventory.readable_sources.get('swift'):
            signals.append(f"swift:sources={inventory.readable_sources['swift']}")
        signals.append('swift:profile=base-only')
    elif 'Package.swift' in inventory.manifest_names:
        signals.append('swift:unconfirmed-package')
    for name, variants in sorted(inventory.manifest_names.items()):
        signals.extend(f'manifest-case-variant:{variant}' for variant in sorted(variants - {name}))
        if len(variants) > 1:
            signals.append(f'manifest-case-conflict:{name}')
    contract_signals = [name for name in ('openapi.yaml', 'openapi.yml', 'asyncapi.yaml', 'asyncapi.yml') if name in inventory.manifests]
    for relative in ('engineering/contracts/openapi', 'engineering/contracts/asyncapi'):
        if any(path.startswith(relative + '/') and Path(path).suffix.lower() in {'.yaml', '.yml', '.json'} for path in inventory.readable):
            contract_signals.append(relative)
    if contract_signals:
        if any('openapi' in item for item in contract_signals):
            domains.append('api')
        if any('asyncapi' in item for item in contract_signals):
            domains.append('event')
        signals.extend(f'contract:{item}' for item in contract_signals)
    for domain, candidates in (
        ('data', ('migrations', 'database/migrations', 'db/migrations', 'clickhouse', 'elasticsearch', 'opensearch')),
        ('ai', ('prompts', 'evals', 'rag', 'vector', 'embeddings')),
    ):
        found = [name for name in candidates if name in inventory.nodes]
        if found:
            domains.append(domain)
            signals.extend(f'{domain}:{name}' for name in found)
    bitrix_modules = sorted({Path(path).name for path in inventory.directory_nodes if path.count('/') == 2 and path.startswith(('local/modules/', 'bitrix/modules/')) and '.' in Path(path).name and not Path(path).name.startswith('.')})
    if bitrix_modules:
        signals.append(f'bitrix:custom-modules={len(bitrix_modules)}')
    languages = unique_ordered(languages)
    domains = unique_ordered(domains)
    inventory.detected.update(languages)
    unconfirmed = inventory.detected - set(languages)
    if (unconfirmed or inventory.unknown_extensions) and not languages:
        signals.append('undetected-language')
    for language in sorted(unconfirmed):
        signals.append(f"undetected-language:{language}={inventory.source_counts.get(language, 0)}")
    signals.extend(f'undetected-source-extension:{extension}={count}' for extension, count in sorted(inventory.unknown_extensions.items()))
    signals.extend(f'language-scan:incomplete={reason}' for reason in sorted(inventory.reasons))
    if inventory.unreadable:
        signals.append(f'language-scan:unreadable={len(inventory.unreadable)}')
    if 'bitrix' in domains:
        kind = 'bitrix'
    elif len(languages) > 1:
        kind = 'polyglot'
    else:
        kind = languages[0] if languages else 'generic'
    return RepoProfile(
        kind=kind, languages=languages, domains=domains, signals=signals,
        bitrix_modules=bitrix_modules, package_scripts=package_scripts,
        detected_languages=sorted(inventory.detected),
        language_scan={
            'status': 'incomplete' if inventory.reasons or inventory.unreadable else 'complete',
            'truncated': bool(inventory.reasons),
            'unknown': bool(inventory.reasons or inventory.unreadable or unconfirmed or inventory.unknown_extensions or any(len(names) > 1 for names in inventory.manifest_names.values())),
            'incomplete_reasons': sorted(inventory.reasons),
            'files': inventory.files, 'bytes': inventory.bytes,
            'directories': inventory.directories, 'entries': inventory.entries,
            'unreadable': len(inventory.unreadable),
            'skipped_symlinks': len(inventory.symlinks),
            'non_regular': len(inventory.non_regular),
            'unknown_extensions': dict(sorted(inventory.unknown_extensions.items())),
        },
    )
