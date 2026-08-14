from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .util import read_text_limited, unique_ordered


@dataclass
class RepoProfile:
    kind: str
    languages: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    bitrix_modules: list[str] = field(default_factory=list)
    package_scripts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _has_any(root: Path, candidates: list[str]) -> list[str]:
    return [item for item in candidates if (root / item).exists()]


def _find_bitrix_modules(root: Path) -> list[str]:
    modules: list[str] = []
    for base in (root / 'local/modules', root / 'bitrix/modules'):
        if not base.is_dir():
            continue
        for child in base.iterdir():
            if child.is_dir() and '.' in child.name and not child.name.startswith('.'):
                modules.append(child.name)
    return sorted(set(modules))


def detect_repo(root: Path) -> RepoProfile:
    signals: list[str] = []
    languages: list[str] = []
    domains: list[str] = []

    bitrix_signals = _has_any(root, [
        'bitrix',
        'local/modules',
        'local/components',
        'bitrix/.settings.php',
        'bitrix/php_interface/dbconn.php',
        'bitrix/modules/main/include/prolog_before.php',
    ])
    if bitrix_signals:
        signals.extend(f'bitrix:{item}' for item in bitrix_signals)
        domains.extend(['bitrix', 'php'])
        languages.append('php')

    php_markers = [root / 'composer.json']
    php_markers.extend(root.glob('*.php'))
    for directory in ('src', 'app', 'local', 'public', 'www'):
        base = root / directory
        if base.is_dir():
            marker = next(base.rglob('*.php'), None)
            if marker is not None:
                php_markers.append(marker)
                break
    if any(path.exists() for path in php_markers):
        languages.append('php')
        domains.append('php')
        if (root / 'composer.json').is_file():
            signals.append('php:composer.json')

    package_scripts: list[str] = []
    package_json = root / 'package.json'
    if package_json.is_file():
        languages.extend(['javascript', 'typescript'])
        domains.append('frontend')
        signals.append('node:package.json')
        try:
            package_scripts = sorted(json.loads(package_json.read_text(encoding='utf-8')).get('scripts', {}).keys())
        except (json.JSONDecodeError, OSError, AttributeError):
            package_scripts = []

    if (root / 'pyproject.toml').is_file() or (root / 'requirements.txt').is_file():
        languages.append('python')
        signals.append('python:project')

    if (root / 'go.mod').is_file():
        languages.append('go')
        signals.append('go:module')

    if (root / 'Cargo.toml').is_file():
        languages.append('rust')
        signals.append('rust:cargo')

    contract_signals = _has_any(root, [
        'openapi.yaml', 'openapi.yml', 'asyncapi.yaml', 'asyncapi.yml',
    ])
    for rel in ('engineering/contracts/openapi', 'engineering/contracts/asyncapi'):
        base = root / rel
        if base.is_dir() and any(
            item.is_file() and item.name != '.gitkeep' and item.suffix.lower() in {'.yaml', '.yml', '.json'}
            for item in base.rglob('*')
        ):
            contract_signals.append(rel)
    if contract_signals:
        if any('openapi' in item for item in contract_signals):
            domains.append('api')
        if any('asyncapi' in item for item in contract_signals):
            domains.append('event')
        signals.extend(f'contract:{item}' for item in contract_signals)

    data_signals = _has_any(root, [
        'migrations', 'database/migrations', 'db/migrations', 'clickhouse', 'elasticsearch', 'opensearch',
    ])
    if data_signals:
        domains.append('data')
        signals.extend(f'data:{item}' for item in data_signals)

    ai_signals = _has_any(root, ['prompts', 'evals', 'rag', 'vector', 'embeddings'])
    if ai_signals:
        domains.append('ai')
        signals.extend(f'ai:{item}' for item in ai_signals)

    bitrix_modules = _find_bitrix_modules(root)
    if bitrix_modules:
        signals.append(f'bitrix:custom-modules={len(bitrix_modules)}')

    languages = unique_ordered(languages)
    domains = unique_ordered(domains)
    if 'bitrix' in domains:
        kind = 'bitrix'
    elif len(languages) > 1:
        kind = 'polyglot'
    elif languages:
        kind = languages[0]
    else:
        kind = 'generic'

    return RepoProfile(
        kind=kind,
        languages=languages,
        domains=domains,
        signals=signals,
        bitrix_modules=bitrix_modules,
        package_scripts=package_scripts,
    )
