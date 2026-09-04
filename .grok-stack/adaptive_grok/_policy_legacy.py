from __future__ import annotations

import fnmatch
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .state import active_write_agents, get_active_route, has_valid_approval
from .util import load_json, safe_relative_path

WRITE_ROLES = {
    'general_implementer', 'php_implementer', 'bitrix_implementer', 'frontend_implementer',
    'integration_implementer', 'data_implementer', 'ai_implementer',
}

DEFAULT_CONTROL_PLANE = [
    '.agents/**', '.grok/**', '.grok-stack/**', '.github/**', 'trust-ci/**',
    '.gitignore', 'AGENTS.md', 'README.md', 'CHANGELOG.md', 'VERSION',
    'decisions.md', 'mistakes.md', 'Makefile', 'ruff.toml', 'bandit.yaml', '.coveragerc',
    'scripts/grok_*.py', 'scripts/install_into.py', 'scripts/package_stack.py',
    'user_prompt_submit.py', 'pre_tool_use.py', 'post_tool_use.py', 'pre_compact.py',
    'session_start.py', 'session_end.py', 'stop_gate.py', 'subagent_start.py', 'subagent_stop.py',
    'tests/_support.py', 'tests/test_*.py', 'engineering/runbooks/publish-v*.md',
]
DEFAULT_PROTECTED = [
    '.git/**', '.env', '.env.*', '**/.env', '**/.env.*', '**/*.pem', '**/*.key', '**/*.p12', '**/*.pfx',
    *DEFAULT_CONTROL_PLANE, 'bitrix/**',
]
DEFAULT_SECRET_READ = [
    '.env', '.env.*', '**/.env', '**/.env.*', '**/*.pem', '**/*.key', '**/*.p12', '**/*.pfx',
    '**/id_rsa', '**/id_ed25519', '**/credentials*', '**/secrets/**', 'trust-ci/env/*.env', 'trust-ci/runtime/**',
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
_COMMAND_SPLIT = re.compile(r'(?:&&|\|\||[;|\n])')
_WRAPPERS = {'sudo', 'doas', 'command', 'time', 'nohup', 'nice'}
_EXECUTION_WRAPPERS = {'command', 'nice', 'nohup', 'setsid', 'time', 'timeout'}
_UNWRAP_SHELL = re.compile(
    r'''^\s*(?:(?:sudo|doas)\s+)?(?:/(?:usr/)?bin/)?(?:bash|sh|zsh|dash|ksh)\s+-\S*c\S*\s+(?P<rest>.+?)\s*$''',
    re.IGNORECASE | re.VERBOSE | re.DOTALL,
)
_SHELL_REDIRECTION = re.compile(
    r'''(?:^|[\s;&|])(?:\d*>>?|&>>?)\s*(?P<target>"[^"]+"|'[^']+'|[^\s;&|]+)''',
    re.IGNORECASE | re.VERBOSE,
)
_SHELL_MUTATION_SIGNAL = re.compile(
    r'''
    (?:^|[;&|]\s*|\s)(?:rm|mv|cp|install|touch|truncate|mkdir|rmdir|ln|chmod|chown|chgrp|tee|patch|rsync)\b
    |\bsed\b[^\n]*\s-i(?:\b|[A-Za-z])
    |\bperl\b[^\n]*\s-[^\s\n]*i[^\s\n]*\b
    |\b(?:python(?:3(?:\.\d+)?)?|node|ruby|php)\b[^\n]*\s(?:-c|-e|-r)\b
    |\bgit\b[^\n]*\s(?:apply|checkout|restore|rm|mv|clean)\b
    |\bruff\b[^\n]*--fix\b
    |\bcurl\b[^\n]*\s(?:-o|--output)(?:\s|=)
    |\bwget\b[^\n]*\s(?:-O|--output-document)(?:\s|=)
    |\bdd\b[^\n]*\bof=
    |\b(?:tar|unzip)\b[^\n]*(?:\s-(?:x|[^\s\n]*x[^\s\n]*)|\bextract\b)
    ''',
    re.IGNORECASE | re.VERBOSE | re.DOTALL,
)
_GLOB_META = re.compile(r'[*?[]')
_HTTP_URL = re.compile(r'https?://[^\s"\']+', re.IGNORECASE)
SIDE_EFFECT_TOOL = re.compile(
    r'(?:^|__)(?:create|update|delete|remove|send|write|publish|deploy|merge|close|execute|apply|archive|trash|move)(?:_|$)',
    re.IGNORECASE,
)


def write_roles(root: Path) -> set[str]:
    data = load_json(root / '.grok-stack/config/routing.json', None)
    if isinstance(data, dict):
        roles = data.get('write_roles')
        if isinstance(roles, list):
            names = {str(item).strip() for item in roles if isinstance(item, str) and item.strip()}
            if names:
                return names
    return set(WRITE_ROLES)


def _configured_patterns(config: dict[str, Any], key: str, defaults: list[str]) -> list[str]:
    value = config.get(key)
    if isinstance(value, list):
        patterns = [str(item).strip() for item in value if isinstance(item, str) and item.strip()]
        if patterns:
            return patterns
    return list(defaults)


def _glob_match(path: str, pattern: str) -> bool:
    normalized = path.replace('\\', '/').lstrip('./')
    candidate = pattern.replace('\\', '/').lstrip('./')
    return fnmatch.fnmatchcase(normalized, candidate)


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(_glob_match(path, pattern) for pattern in patterns)


def _literal_pattern_prefix(pattern: str) -> str:
    normalized = pattern.replace('\\', '/').lstrip('./')
    match = _GLOB_META.search(normalized)
    if match:
        normalized = normalized[:match.start()]
    return normalized.rstrip('/')


def _mentions_control_plane(command: str, patterns: list[str]) -> bool:
    normalized = command.replace('\\', '/').casefold()
    return any(prefix and prefix.casefold() in normalized for prefix in map(_literal_pattern_prefix, patterns))


def _redirects_to_control_plane(command: str, patterns: list[str]) -> bool:
    for match in _SHELL_REDIRECTION.finditer(command):
        target = match.group('target').strip('"\'')
        if _mentions_control_plane(target, patterns):
            return True
    return False


def _is_control_plane_shell_mutation(command: str, patterns: list[str]) -> bool:
    if _redirects_to_control_plane(command, patterns):
        return True
    return _mentions_control_plane(command, patterns) and _SHELL_MUTATION_SIGNAL.search(command) is not None


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


def _command_chunks(command: str) -> list[str]:
    return [part for part in _COMMAND_SPLIT.split(command) if part.strip()]


def _unwrap_execution_wrappers(tokens: list[str]) -> tuple[list[str], bool]:
    """Return a command behind a small literal wrapper grammar, or flag unsafe syntax."""
    remaining = list(tokens)
    for _depth in range(8):
        if not remaining:
            return [], True
        wrapper = Path(remaining[0]).name.lower()
        if wrapper not in _EXECUTION_WRAPPERS:
            return remaining, False
        index = 1
        if wrapper == 'nice':
            while index < len(remaining):
                option = remaining[index]
                if option == '--':
                    index += 1
                    break
                if option in {'-n', '--adjustment'}:
                    if index + 1 >= len(remaining):
                        return [], True
                    index += 2
                    continue
                if option.startswith('--adjustment='):
                    index += 1
                    continue
                if option.startswith('-'):
                    return [], True
                break
        elif wrapper == 'time':
            while index < len(remaining) and remaining[index] == '-p':
                index += 1
            if index < len(remaining) and remaining[index] == '--':
                index += 1
            elif index < len(remaining) and remaining[index].startswith('-'):
                return [], True
        elif wrapper in {'command', 'nohup', 'setsid'}:
            if index < len(remaining) and remaining[index] == '--':
                index += 1
            elif index < len(remaining) and remaining[index].startswith('-'):
                return [], True
        elif wrapper == 'timeout':
            if index < len(remaining) and remaining[index] == '--':
                index += 1
            if index >= len(remaining) or remaining[index].startswith('-'):
                return [], True
            index += 1  # duration
        remaining = remaining[index:]
    return [], True


def _leading_argv(chunk: str) -> list[str]:
    stripped = chunk.split('#', 1)[0].strip()
    try:
        tokens = shlex.split(stripped)
    except ValueError:
        tokens = stripped.split()
    while tokens and re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', tokens[0]):
        tokens = tokens[1:]
    if tokens and Path(tokens[0]).name.lower() in {'sudo', 'doas', 'env'}:
        commands = {'git', 'gh', 'docker', 'npm', 'bash', 'sh', 'zsh', 'dash', 'ksh'}
        command_index = next(
            (index for index, token in enumerate(tokens[1:], 1) if Path(token).name.lower() in commands),
            None,
        )
        if command_index is not None:
            tokens = tokens[command_index:]
    tokens, ambiguous_wrapper = _unwrap_execution_wrappers(tokens)
    if ambiguous_wrapper:
        return []
    if tokens:
        tokens[0] = Path(tokens[0]).name
    return [token.lower() for token in tokens]


def _unwrap_shell(chunk: str) -> str:
    try:
        tokens = shlex.split(chunk)
    except ValueError:
        tokens = []
    shells = {'bash', 'sh', 'zsh', 'dash', 'ksh'}
    for index, token in enumerate(tokens):
        if Path(token).name.lower() not in shells:
            continue
        for option_index in range(index + 1, len(tokens) - 1):
            if re.fullmatch(r'-[A-Za-z]*c[A-Za-z]*', tokens[option_index]):
                return tokens[option_index + 1]
        break
    match = _UNWRAP_SHELL.match(chunk)
    if not match:
        return chunk
    rest = match.group('rest')
    if len(rest) >= 2 and rest[0] == rest[-1] and rest[0] in {'"', "'"}:
        return rest[1:-1]
    return rest


def _production_action(argv: list[str]) -> str | None:
    if argv and argv[0] == 'git':
        index = 1
        while index < len(argv):
            if index + 1 < len(argv) and argv[index] in {'-c', '--git-dir', '--work-tree'}:
                index += 2
                continue
            if argv[index].startswith(('--git-dir=', '--work-tree=')):
                index += 1
                continue
            break
        argv = ['git', *argv[index:]]
    if argv[:2] == ['git', 'push']:
        if '--tags' in argv or any(item.startswith('refs/tags/') for item in argv[2:]):
            return 'git-push-tag'
        candidates = [item for item in argv[2:] if not item.startswith('-')]
        if any(re.fullmatch(r'v?\d+\.\d+\.\d+(?:[-+].+)?', item) for item in candidates):
            return 'git-push-tag'
        return 'git-push-branch'
    if argv[:3] == ['gh', 'pr', 'merge']:
        return 'pull-request-merge'
    if argv[:3] == ['gh', 'workflow', 'run']:
        return 'workflow-dispatch'
    if argv[:2] == ['docker', 'push']:
        return 'docker-push'
    if argv[:2] == ['npm', 'publish']:
        return 'npm-publish'
    if argv[:3] == ['gh', 'release', 'create']:
        return 'github-release'
    return None


@dataclass(frozen=True)
class AuthorityAnalysis:
    actions: tuple[str, ...]
    ambiguous: bool
    context_proven: bool


_AUTHORITY_EXECUTABLES = {'git', 'gh', 'docker', 'npm'}
_AUTHORITY_META = re.compile(r'[$`*?\[\]{}()]')
_INERT_EXECUTABLES = {'echo', 'printf'}
_SHELL_EXECUTABLES = {'bash', 'sh', 'zsh', 'dash', 'ksh'}


def _authority_token_is_dynamic(token: str) -> bool:
    return _AUTHORITY_META.search(token) is not None


def _literal_xargs_target(tokens: list[str]) -> list[str] | None:
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == '--':
            return tokens[index + 1:]
        if token in {'-a', '--arg-file'}:
            if index + 1 >= len(tokens):
                return None
            index += 2
            continue
        if token.startswith('--arg-file='):
            index += 1
            continue
        if token.startswith('-'):
            return None
        return tokens[index:]
    return []


def _git_selector_index(argv: list[str]) -> int:
    index = 1
    while index < len(argv):
        token = argv[index]
        if token in {'-C', '-c', '--git-dir', '--work-tree'}:
            if index + 1 >= len(argv):
                return len(argv)
            index += 2
            continue
        if token.startswith(('--git-dir=', '--work-tree=')):
            index += 1
            continue
        break
    return index


def _candidate_authority(argv: list[str]) -> tuple[str | None, bool]:
    if not argv:
        return None, False
    executable = Path(argv[0]).name.lower()
    normalized = [executable, *[token.lower() for token in argv[1:]]]
    action = _production_action(normalized)
    if executable == 'git':
        selector_index = _git_selector_index(argv)
        if selector_index >= len(argv):
            return action, False
        if _authority_token_is_dynamic(argv[selector_index]):
            return action, True
        if argv[selector_index].lower() == 'push' and any(
            _authority_token_is_dynamic(token) for token in argv[selector_index + 1:]
        ):
            return action, True
    elif executable in {'docker', 'npm'}:
        if len(argv) > 1 and _authority_token_is_dynamic(argv[1]):
            return action, True
        if action and any(_authority_token_is_dynamic(token) for token in argv[2:]):
            return action, True
    elif executable == 'gh':
        if len(argv) > 1 and _authority_token_is_dynamic(argv[1]):
            return action, True
        if len(argv) > 2 and argv[1].lower() in {'pr', 'release', 'workflow'}:
            if _authority_token_is_dynamic(argv[2]):
                return action, True
            if action and any(_authority_token_is_dynamic(token) for token in argv[3:]):
                return action, True
    return action, False


def _command_tokens(chunk: str) -> list[str] | None:
    try:
        tokens = shlex.split(chunk)
    except ValueError:
        return None
    while tokens and re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', tokens[0]):
        tokens = tokens[1:]
    return tokens


def _bounded_command(tokens: list[str]) -> tuple[list[str], bool]:
    remaining = list(tokens)
    if remaining and Path(remaining[0]).name.lower() in {'sudo', 'doas'}:
        if len(remaining) < 2 or remaining[1].startswith('-'):
            return remaining, False
        remaining = remaining[1:]
    elif remaining and Path(remaining[0]).name.lower() == 'env':
        return remaining, False
    remaining, ambiguous_wrapper = _unwrap_execution_wrappers(remaining)
    return remaining, not ambiguous_wrapper


def _literal_shell_payload(tokens: list[str]) -> str | None:
    if len(tokens) != 3 or Path(tokens[0]).name.lower() not in _SHELL_EXECUTABLES:
        return None
    if tokens[1] not in {'-c', '-lc'}:
        return None
    return tokens[2]


def _analyze_authority_pieces(
    raw_command: str,
    *,
    shell_depth: int = 0,
) -> AuthorityAnalysis:
    actions: list[str] = []
    ambiguous = False
    context_proven = True

    def record(argv: list[str], *, proven: bool) -> None:
        nonlocal ambiguous, context_proven
        action, candidate_ambiguous = _candidate_authority(argv)
        if action and action not in actions:
            actions.append(action)
        if candidate_ambiguous:
            ambiguous = True
        if (action or candidate_ambiguous) and not proven:
            context_proven = False

    for chunk in _command_chunks(raw_command):
        raw_tokens = _command_tokens(chunk)
        if raw_tokens is None:
            if re.search(r'\b(?:git|gh|docker|npm)\b', chunk, re.IGNORECASE):
                ambiguous = True
                context_proven = False
            continue
        tokens, bounded = _bounded_command(raw_tokens)
        if not tokens:
            continue
        outer = Path(tokens[0]).name.lower()
        if outer in _INERT_EXECUTABLES:
            continue
        if outer == 'xargs':
            target = _literal_xargs_target(tokens)
            if target is None:
                if any(Path(token).name.lower() in _AUTHORITY_EXECUTABLES for token in tokens[1:]):
                    ambiguous = True
                    context_proven = False
                continue
            target, target_bounded = _bounded_command(target)
            if not target or Path(target[0]).name.lower() in _INERT_EXECUTABLES:
                continue
            if Path(target[0]).name.lower() in _AUTHORITY_EXECUTABLES:
                record(target, proven=False)
            elif any(Path(token).name.lower() in _AUTHORITY_EXECUTABLES for token in target):
                for index, token in enumerate(target):
                    if Path(token).name.lower() in _AUTHORITY_EXECUTABLES:
                        record(target[index:], proven=False)
            if not target_bounded:
                context_proven = False
            continue
        if outer in _SHELL_EXECUTABLES:
            payload = _literal_shell_payload(tokens)
            if payload is None or shell_depth > 0:
                continue
            inner = _analyze_authority_pieces(payload, shell_depth=shell_depth + 1)
            for action in inner.actions:
                if action not in actions:
                    actions.append(action)
            ambiguous = ambiguous or inner.ambiguous
            if (inner.actions or inner.ambiguous) and (not bounded or not inner.context_proven):
                context_proven = False
            continue
        if outer in _AUTHORITY_EXECUTABLES:
            record(tokens, proven=bounded)
            continue
        for index, token in enumerate(tokens[1:], 1):
            if Path(token).name.lower() in _AUTHORITY_EXECUTABLES:
                record(tokens[index:], proven=False)

    return AuthorityAnalysis(tuple(actions), ambiguous, context_proven)


def analyze_command_authority(raw_command: str) -> AuthorityAnalysis:
    """Conservatively classify production authority without evaluating shell syntax."""
    return _analyze_authority_pieces(raw_command)


def production_action(command: str) -> str | None:
    analysis = analyze_command_authority(command)
    if analysis.ambiguous or not analysis.context_proven:
        return None
    return analysis.actions[0] if analysis.actions else None


def is_production_invocation(command: str) -> bool:
    return production_action(command) is not None


def _http_write_resource(command: str) -> str | None:
    lowered = command.lower()
    mutation = False
    if re.search(r'\bcurl\b', lowered):
        mutation = bool(re.search(r'(?:-x|--request)\s*(?:post|put|patch|delete)\b|(?:-d|--data(?:-raw|-binary)?)(?:\s|=)', lowered))
    elif re.search(r'\bwget\b', lowered):
        mutation = bool(re.search(r'--method(?:\s|=)(?:post|put|patch|delete)\b|--post-data(?:\s|=)', lowered))
    elif re.search(r'\bgh\s+api\b', lowered):
        mutation = bool(re.search(r'(?:-x|--method)\s*(?:post|put|patch|delete)\b|(?:-f|--field|--raw-field)(?:\s|=)', lowered))
        if mutation:
            return 'github-api'
    if not mutation:
        return None
    match = _HTTP_URL.search(command)
    return match.group(0) if match else 'direct-http-write'


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
    if not isinstance(config, dict):
        config = {}
    control_plane = _configured_patterns(config, 'control_plane_paths', DEFAULT_CONTROL_PLANE)
    protected = _configured_patterns(config, 'protected_paths', DEFAULT_PROTECTED)
    secret_read = _configured_patterns(config, 'secret_read_paths', DEFAULT_SECRET_READ)

    if tool == 'Bash':
        command = str(tool_input.get('command', '')) if isinstance(tool_input, dict) else str(tool_input)
        if _is_control_plane_shell_mutation(command, control_plane):
            return False, 'Blocked control-plane shell mutation; use a structured write with an exact protected-path grant.'
        for pattern in _configured_patterns(config, 'destructive_command_patterns', DESTRUCTIVE_COMMANDS):
            if re.search(pattern, command, flags=re.IGNORECASE):
                return False, f'Blocked destructive command by repository policy: {pattern}'
        action = production_action(command)
        if action:
            if action == 'workflow-dispatch':
                return False, 'GitHub Actions workflow dispatch is forbidden for this repository.'
            if not has_valid_approval(root, 'production', action=action):
                return False, f'Production action {action} requires an exact delegated local grant bound to the current SHA.'
        http_resource = _http_write_resource(command)
        if http_resource and not has_valid_approval(root, 'external-write', action='external-write', resource=http_resource):
            return False, f'Direct external write requires an exact delegated grant for resource {http_resource}.'

    candidate_paths = _extract_paths(tool_input)
    if tool == 'apply_patch' and isinstance(tool_input, dict):
        candidate_paths.extend(_extract_patch_paths(str(tool_input.get('command', ''))))

    lowered_tool = tool.lower()
    is_read = lowered_tool in {'read', 'read_file', 'open_file', 'fs_read'} or ('read' in lowered_tool and tool.startswith('mcp__'))
    is_write = tool in {'apply_patch', 'Edit', 'Write'} or any(word in lowered_tool for word in ('write_file', 'edit_file', 'delete_file'))

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
            if _matches_any(rel, secret_read):
                return False, f'Reading secret material is blocked: {rel}'

    if is_write:
        for rel in normalized:
            if _matches_any(rel, protected):
                if not has_valid_approval(root, 'protected-path', action='protected-path-write', resource=rel):
                    return False, f'Protected path edit requires an exact delegated grant for {rel}.'

    if tool == 'Agent' or lowered_tool in {'spawn_agent', 'agent'}:
        agent_type = _agent_type(tool_input)
        if route and agent_type:
            allowed = set(route.get('allowed_agents', []))
            if agent_type not in allowed:
                return False, f'Agent {agent_type} is outside active route {route.get("route_id")}; allowed: {sorted(allowed)}'
            roles = write_roles(root)
            if agent_type in roles:
                expected = route.get('write_agent')
                if expected != agent_type:
                    return False, f'Route permits only write owner {expected}, not {agent_type}'
                active = active_write_agents(root, roles)
                if active and agent_type not in active:
                    return False, f'Another write agent is already active: {active}'

    if tool.startswith('mcp__') and SIDE_EFFECT_TOOL.search(tool):
        if not has_valid_approval(root, 'external-write', action='external-write', resource=tool):
            return False, f'MCP side-effect tool {tool} requires an exact delegated external-write grant.'

    return True, None
