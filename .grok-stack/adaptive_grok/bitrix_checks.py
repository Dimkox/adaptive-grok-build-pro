from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .util import read_text_limited


@dataclass
class Finding:
    severity: str
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


CORE_PREFIXES = ('bitrix/',)
DEBUG_PATTERNS = {
    'debug-output': re.compile(r'\b(?:var_dump|print_r)\s*\(|\bdd\s*\(|\bdie\s*\(', re.IGNORECASE),
    'dangerous-eval': re.compile(r'\b(?:eval|shell_exec|passthru|system)\s*\(', re.IGNORECASE),
}


def _module_roots(root: Path, changed: list[str]) -> list[Path]:
    roots: set[Path] = set()
    for rel in changed:
        parts = Path(rel).parts
        if len(parts) >= 3 and parts[0] == 'local' and parts[1] == 'modules':
            roots.add(root / 'local/modules' / parts[2])
    return sorted(roots)


def check_bitrix(root: Path, changed: list[str]) -> list[Finding]:
    findings: list[Finding] = []

    for rel in changed:
        normalized = rel.replace('\\', '/')
        if normalized.startswith(CORE_PREFIXES):
            findings.append(Finding(
                'error', 'core-modification', normalized,
                'Bitrix core path changed. Move customization to local/ or approve protected-path explicitly.',
            ))

    for rel in changed:
        if not rel.lower().endswith('.php'):
            continue
        path = root / rel
        text = read_text_limited(path)
        if not text:
            continue
        for code, pattern in DEBUG_PATTERNS.items():
            if pattern.search(text):
                severity = 'error' if code == 'dangerous-eval' else 'error'
                findings.append(Finding(severity, code, rel, f'Forbidden production pattern detected: {code}'))
        if re.search(r'\$_REQUEST\s*\[', text):
            findings.append(Finding('warning', 'raw-request', rel, 'Direct $_REQUEST access requires explicit filtering and type validation.'))
        if re.search(r'\bCModule::IncludeModule\s*\(', text, re.IGNORECASE):
            findings.append(Finding('warning', 'legacy-loader', rel, 'Prefer Bitrix\\Main\\Loader::includeModule for new code.'))
        if re.search(r'global\s+\$DB\b|\$DB->Query\s*\(', text):
            findings.append(Finding('warning', 'direct-db', rel, 'Direct legacy DB access needs justification; prefer D7 ORM/connection APIs.'))
        if '/templates/' in rel.replace('\\', '/') and re.search(r'\b(?:add|update|delete)\s*\(', text, re.IGNORECASE):
            findings.append(Finding('warning', 'template-business-logic', rel, 'Component templates should not own writes or domain logic.'))

    for module_root in _module_roots(root, changed):
        module_id = module_root.name
        rel_root = module_root.relative_to(root).as_posix()
        if not re.fullmatch(r'[a-z0-9_]+\.[a-z0-9_.]+', module_id):
            findings.append(Finding('error', 'module-id', rel_root, 'Module directory must use lowercase vendor.module identifier.'))
        required = ['install/index.php', 'include.php', 'lib']
        for item in required:
            if not (module_root / item).exists():
                findings.append(Finding('error', 'module-structure', rel_root, f'Missing required module path: {item}'))

        install_path = module_root / 'install/index.php'
        install_text = read_text_limited(install_path)
        if install_text:
            registers_module = bool(re.search(r'(?i)(?:\bRegisterModule|ModuleManager::registerModule)\s*\(', install_text))
            unregisters_module = bool(re.search(r'(?i)(?:\bUnRegisterModule|ModuleManager::unRegisterModule)\s*\(', install_text))
            if registers_module and not unregisters_module:
                findings.append(Finding('error', 'uninstall-symmetry', install_path.relative_to(root).as_posix(), 'Module registration exists without uninstall symmetry.'))
            registers_events = any(token in install_text for token in ('registerEventHandler', 'RegisterModuleDependences'))
            unregisters_events = any(token in install_text for token in ('unRegisterEventHandler', 'UnRegisterModuleDependences'))
            if registers_events and not unregisters_events:
                findings.append(Finding('error', 'event-unregister', install_path.relative_to(root).as_posix(), 'Event registration must have uninstall symmetry.'))
            if 'CAgent::AddAgent' in install_text and not any(token in install_text for token in ('RemoveModuleAgents', 'RemoveAgent')):
                findings.append(Finding('error', 'agent-uninstall', install_path.relative_to(root).as_posix(), 'Bitrix agents must be removed during uninstall.'))
            if not registers_module:
                findings.append(Finding('warning', 'module-registration', install_path.relative_to(root).as_posix(), 'No module registration call found in install class.'))

        include_text = read_text_limited(module_root / 'include.php')
        if include_text and 'Loader::register' not in include_text and 'autoload.php' not in include_text:
            findings.append(Finding('warning', 'autoload', f'{rel_root}/include.php', 'Module include.php does not visibly register namespace/classes; verify D7 autoload.'))

    return findings
