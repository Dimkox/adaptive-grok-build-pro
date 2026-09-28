from __future__ import annotations

import importlib.util
import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .manifest import verify_manifest
from .repo import detect_repo
from .router import build_route
from .toolchain import check_toolchain
from .util import load_json


@dataclass
class DoctorItem:
    status: str
    name: str
    message: str


_SUITE_RUNTIME_DEPS = (
    ('factory', 'factory/pyproject.toml'),
    ('trust-ci', 'trust-ci/pyproject.toml'),
    ('delivery', 'delivery/pyproject.toml'),
)
_REQUIREMENT_NAME = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$')
_REQUIREMENT_OPERATORS = ('===', '==', '~=', '!=', '>=', '<=', '>', '<')


def _dependency_module(requirement: str) -> str | None:
    name = requirement.split(';', 1)[0].strip().split('[', 1)[0].strip()
    for operator in _REQUIREMENT_OPERATORS:
        if operator in name:
            name = name.split(operator, 1)[0].strip()
            break
    name = name.split()[0] if name else ''
    if not _REQUIREMENT_NAME.fullmatch(name):
        return None
    module = name.replace('-', '_')
    if not module.isidentifier():
        return None
    return module


def _module_importable(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def _runtime_modules(dependencies: object) -> list[str] | None:
    if not isinstance(dependencies, list):
        return None
    modules: list[str] = []
    seen: set[str] = set()
    for item in dependencies:
        if not isinstance(item, str):
            return None
        module = _dependency_module(item)
        if module is None:
            if item.strip():
                return None
            continue
        if module not in seen:
            seen.add(module)
            modules.append(module)
    return modules


def _suite_dependency_items(root: Path) -> list[DoctorItem]:
    """Report pyproject runtime modules that this interpreter cannot import.

    The probe never installs or executes a dependency. A suite with no
    pyproject.toml is omitted instead of failed.
    """
    items: list[DoctorItem] = []
    for name, rel in _SUITE_RUNTIME_DEPS:
        path = root / rel
        if not path.is_file():
            continue
        try:
            document = tomllib.loads(path.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            items.append(DoctorItem('fail', f'test-deps:{name}', str(exc)))
            continue
        project = document.get('project') if isinstance(document, dict) else None
        if not isinstance(project, dict) or 'dependencies' not in project:
            items.append(DoctorItem('pass', f'test-deps:{name}', 'no runtime dependencies'))
            continue
        modules = _runtime_modules(project.get('dependencies'))
        if modules is None:
            items.append(DoctorItem('fail', f'test-deps:{name}', f'invalid runtime dependencies in {rel}'))
            continue
        missing = [module for module in modules if not _module_importable(module)]
        if missing:
            items.append(DoctorItem('fail', f'test-deps:{name}', f'{", ".join(missing)} missing'))
        elif modules:
            items.append(DoctorItem('pass', f'test-deps:{name}', 'runtime dependencies importable'))
        else:
            items.append(DoctorItem('pass', f'test-deps:{name}', 'no runtime dependencies'))
    return items


def run_doctor(root: Path) -> list[DoctorItem]:
    items: list[DoctorItem] = []

    required = [
        'AGENTS.md', '.grok/config.toml', '.grok/hooks.json',
        '.agents/skills/adaptive-delivery/SKILL.md', '.grok-stack/config/routing.json',
    ]
    for rel in required:
        items.append(DoctorItem('pass' if (root / rel).exists() else 'fail', f'file:{rel}', 'present' if (root / rel).exists() else 'missing'))

    for rel in ('.grok/config.toml',):
        try:
            tomllib.loads((root / rel).read_text(encoding='utf-8'))
            items.append(DoctorItem('pass', f'toml:{rel}', 'valid TOML'))
        except Exception as exc:
            items.append(DoctorItem('fail', f'toml:{rel}', str(exc)))

    try:
        json.loads((root / '.grok/hooks.json').read_text(encoding='utf-8'))
        items.append(DoctorItem('pass', 'json:.grok/hooks.json', 'valid JSON'))
    except Exception as exc:
        items.append(DoctorItem('fail', 'json:.grok/hooks.json', str(exc)))

    managed = load_json(root / '.grok-stack/config/managed.json', {}) or {}
    managed_agents = managed.get('agents', [])
    managed_skills = managed.get('skills', [])

    for name in managed_agents:
        path = root / '.grok/agents' / f'{name}.toml'
        if not path.is_file():
            items.append(DoctorItem('fail', f'agent:{name}', 'managed agent is missing'))
            continue
        try:
            data = tomllib.loads(path.read_text(encoding='utf-8'))
            missing = [key for key in ('name', 'description', 'developer_instructions') if not data.get(key)]
            items.append(DoctorItem('fail' if missing else 'pass', f'agent:{path.name}', f'missing {missing}' if missing else data['name']))
        except Exception as exc:
            items.append(DoctorItem('fail', f'agent:{path.name}', str(exc)))

    for name in managed_skills:
        path = root / '.agents/skills' / name / 'SKILL.md'
        if not path.is_file():
            items.append(DoctorItem('fail', f'skill:{name}', 'managed skill is missing'))
            continue
        skill_text = path.read_text(encoding='utf-8')
        valid = skill_text.startswith('---\n') and '\nname:' in skill_text[:500] and '\ndescription:' in skill_text[:1000]
        items.append(DoctorItem('pass' if valid else 'fail', f'skill:{name}', 'valid frontmatter' if valid else 'invalid frontmatter'))

    unmanaged_agents = [path.name for path in (root / '.grok/agents').glob('*.toml') if path.stem not in managed_agents]
    unmanaged_skills = [path.parent.name for path in (root / '.agents/skills').glob('*/SKILL.md') if path.parent.name not in managed_skills]
    if unmanaged_agents:
        items.append(DoctorItem('info', 'unmanaged-agents', ', '.join(sorted(unmanaged_agents))))
    if unmanaged_skills:
        items.append(DoctorItem('info', 'unmanaged-skills', ', '.join(sorted(unmanaged_skills))))

    profile = detect_repo(root)
    items.append(DoctorItem('pass', 'repo-detection', f'{profile.kind}; domains={profile.domains}; signals={profile.signals[:5]}'))
    sample = build_route(root, 'Исправить ошибку в обработчике события Битрикс D7 и добавить PHPUnit тест', 'doctor')
    if sample.write_agent == 'bitrix_implementer' and 'bitrix_reviewer' in sample.review_agents:
        items.append(DoctorItem('pass', 'adaptive-routing', 'Bitrix route selects specialized agents'))
    else:
        items.append(DoctorItem('fail', 'adaptive-routing', str(sample.to_dict())))

    manifest_path = root / 'MANIFEST.sha256'
    if manifest_path.is_file():
        manifest_errors = verify_manifest(root)
        items.append(DoctorItem(
            'fail' if manifest_errors else 'pass',
            'manifest',
            '; '.join(manifest_errors[:10]) if manifest_errors else 'all packaged files match MANIFEST.sha256',
        ))
    else:
        items.append(DoctorItem('info', 'manifest', 'not generated yet; packaging creates it'))

    for tool in check_toolchain(root):
        items.append(DoctorItem(tool.status, f'tool:{tool.id}', tool.message))
    items.extend(_suite_dependency_items(root))
    return items
