from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any, Iterable

from .state import active_write_agents, get_active_route, has_valid_approval
from .util import load_json, safe_relative_path

WRITE_ROLES = {
    'general_implementer', 'php_implementer', 'bitrix_implementer', 'frontend_implementer',
    'integration_implementer', 'data_implementer', 'ai_implementer',
}

DEFAULT_PROTECTED = [
    '.git/**', '.env', '.env.*', '**/.env', '**/.env.*', '**/*.pem', '**/*.key', '**/*.p12', '**/*.pfx',
    'bitrix/**',
]
DEFAULT_SECRET_READ = [
    '.env', '.env.*', '**/.env', '**/.env.*', '**/*.pem', '**/*.key', '**/*.p12', '**/*.pfx',
    '**/id_rsa', '**/id_ed25519', '**/credentials*', '**/secrets/**',
]
DESTRUCTIVE_COMMANDS = [
    r'\bgit\s+reset\s+--hard\b',
    r'\bgit\s+clean\s+[^\n]*(?:-f|-x)',
    r'\bgit\s+push\s+[^\n]*(?:--force|-f\b)',
    r'\bterraform\s+(?:destroy|apply)\b',
    r'\btofu\s+(?:destroy|apply)\b',
    r'\bkubectl\s+(?:delete|apply|exec|port-forward)\b',
    r'\bhelm\s+(?:install|upgrade|uninstall)\b',
    r'\bdrop\s+(?:database|schema|table)\b',
    r'\btruncate\s+table\b',
    r'\brm\s+-rf\s+(?:/|~|\$HOME)\b',
    r'\bchmod\s+-R\s+777\b',
]
PRODUCTION_COMMANDS = [
    r'\bprod(?:uction)?\b', r'\bdeploy\b', r'\brelease\b', r'\bpublish\b',
    r'\bgit\s+push\b', r'\bgh\s+pr\s+merge\b', r'\bdocker\s+push\b',
]
SIDE_EFFECT_TOOL = re.compile(
    r'(?:^|__)(?:create|update|delete|remove|send|write|publish|deploy|merge|close|execute|apply|archive|trash|move)(?:_|$)',
    re.IGNORECASE,
)


def _glob_match(path: str, pattern: str) -> bool:
    normalized = path.replace('\\', '/').lstrip('./')
    candidate = pattern.replace('\\', '/').lstrip('./')
    return fnmatch.fnmatchcase(normalized, candidate)


def _extract_paths(value: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in {'path', 'file', 'filename', 'file_path', 'filepath', 'directory', 'target'} and isinstance(item, str):
                paths.append(item)
            else:
                paths.extend(_extract_paths(item))
    elif isinstance(value, list):
        for item in value:
            paths.extend(_extract_paths(item))
    return paths


def _extract_patch_paths(command: str) -> list[str]:
    patterns = [
        r'^\*\*\* (?:Update|Add|Delete) File:\s*(.+?)\s*$',
        r'^\+\+\+\s+(?:b/)?(.+?)\s*$',
        r'^---\s+(?:a/)?(.+?)\s*$',
    ]
    result: list[str] = []
    for line in command.splitlines():
        for pattern in patterns:
            match = re.match(pattern, line)
            if match and match.group(1) != '/dev/null':
                result.append(match.group(1))
    return result


def _agent_type(tool_input: Any) -> str | None:
    if not isinstance(tool_input, dict):
        return None
    for key in ('agent_type', 'type', 'name', 'role'):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def evaluate_pre_tool(root: Path, event: dict[str, Any]) -> tuple[bool, str | None]:
    tool = str(event.get('tool_name', ''))
    tool_input = event.get('tool_input') or {}
    route = get_active_route(root)
    config = load_json(root / '.grok-stack/config/policy.json', {}) or {}
    protected = config.get('protected_paths', DEFAULT_PROTECTED)
    secret_read = config.get('secret_read_paths', DEFAULT_SECRET_READ)

    if tool == 'Bash':
        command = str(tool_input.get('command', '')) if isinstance(tool_input, dict) else str(tool_input)
        for pattern in config.get('destructive_command_patterns', DESTRUCTIVE_COMMANDS):
            if re.search(pattern, command, flags=re.IGNORECASE):
                return False, f'Blocked destructive command by repository policy: {pattern}'
        if any(re.search(pattern, command, flags=re.IGNORECASE) for pattern in PRODUCTION_COMMANDS):
            if not has_valid_approval(root, 'production'):
                return False, 'Production/publish side effect requires explicit approval: python scripts/grok_approve.py production --reason "..."'

    candidate_paths = _extract_paths(tool_input)
    if tool == 'apply_patch' and isinstance(tool_input, dict):
        candidate_paths.extend(_extract_patch_paths(str(tool_input.get('command', ''))))

    is_read = tool.lower() in {'read', 'read_file', 'open_file', 'fs_read'} or ('read' in tool.lower() and tool.startswith('mcp__'))
    is_write = tool in {'apply_patch', 'Edit', 'Write'} or any(word in tool.lower() for word in ('write_file', 'edit_file', 'delete_file'))

    normalized: list[str] = []
    for raw in candidate_paths:
        rel = safe_relative_path(root, raw)
        if rel is None:
            if is_write:
                return False, f'Write outside repository root is blocked: {raw}'
            continue
        normalized.append(rel)

    if is_read:
        for rel in normalized:
            if any(_glob_match(rel, pattern) for pattern in secret_read):
                return False, f'Reading secret material is blocked: {rel}'

    if is_write:
        for rel in normalized:
            if any(_glob_match(rel, pattern) for pattern in protected):
                if not has_valid_approval(root, 'protected-path'):
                    return False, f'Protected path edit blocked: {rel}. Prefer local/ for Bitrix customizations.'

    if tool == 'Agent' or tool.lower() in {'spawn_agent', 'agent'}:
        agent_type = _agent_type(tool_input)
        if route and agent_type:
            allowed = set(route.get('allowed_agents', []))
            if agent_type not in allowed:
                return False, f'Agent {agent_type} is outside active route {route.get("route_id")}; allowed: {sorted(allowed)}'
            if agent_type in WRITE_ROLES:
                expected = route.get('write_agent')
                if expected != agent_type:
                    return False, f'Route permits only write owner {expected}, not {agent_type}'
                active = active_write_agents(root, WRITE_ROLES)
                if active and agent_type not in active:
                    return False, f'Another write agent is already active: {active}'

    if tool.startswith('mcp__') and SIDE_EFFECT_TOOL.search(tool):
        if not has_valid_approval(root, 'external-write'):
            return False, f'MCP side-effect tool {tool} requires explicit external-write approval.'

    return True, None
