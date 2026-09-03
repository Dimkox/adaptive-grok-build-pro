from __future__ import annotations

import json
import os
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HOOK_DIR = Path(__file__).resolve().parent
REPO_CANDIDATE = HOOK_DIR.parents[1]
STACK = REPO_CANDIDATE / '.grok-stack'
if str(STACK) not in sys.path:
    sys.path.insert(0, str(STACK))

from adaptive_grok._policy_legacy import (
    _contains_embedded_sensitive_command,
    _unwrap_execution_wrappers,
)
from adaptive_grok.util import find_root

TOOL_ALIASES = {
    'run_terminal_command': 'Bash',
    'read_file': 'Read',
    'open_file': 'Read',
    'search_replace': 'Edit',
    'write': 'Write',
    'Write': 'Write',
    'Edit': 'Edit',
    'spawn_subagent': 'Agent',
    'task': 'Agent',
    'Task': 'Agent',
}


def read_payload() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def emit(data: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(data, ensure_ascii=False))
    if not data:
        return
    sys.stdout.write('\n')


def first(*values: Any) -> Any:
    for value in values:
        if value not in (None, ''):
            return value
    return None


def root_from(payload: dict[str, Any]) -> Path:
    cwd = first(payload.get('cwd'), payload.get('workspaceRoot'), payload.get('workspace_root'))
    return find_root(cwd)


_SESSION_ROOT_ALIASES = ('cwd', 'workspaceRoot', 'workspace_root')
_COMMAND_ROOT_ALIASES = ('workdir', 'cwd', 'working_directory', 'workingDirectory')


@dataclass(frozen=True)
class RootContext:
    session_cwd: str | None
    session_root: Path | None
    command_workdirs: dict[str, str]
    effective_root: Path | None
    resolution_status: str

    @property
    def sensitive_safe(self) -> bool:
        return self.effective_root is not None and self.resolution_status in {'session-root', 'effective-root'}

    @property
    def has_ambiguous_command_evidence(self) -> bool:
        return any(value == '<ambiguous>' for value in self.command_workdirs.values())

    @property
    def ledger_root(self) -> Path | None:
        return self.effective_root or self.session_root


def _recognized_root(value: Path) -> Path | None:
    root = find_root(value.resolve())
    return root.resolve() if (root / '.grok-stack').is_dir() else None


def _literal_xargs_command(words: list[str]) -> list[str] | None:
    index = 1
    while index < len(words):
        token = words[index]
        if token == '--':
            return words[index + 1:]
        if token in {'-a', '--arg-file'}:
            if index + 1 >= len(words):
                return None
            index += 2
            continue
        if token.startswith('--arg-file='):
            index += 1
            continue
        if token.startswith('-'):
            return None
        return words[index:]
    return []


def _literal_git_subcommand(words: list[str]) -> str | None:
    index = 1
    while index < len(words):
        token = words[index]
        if token in {'-C', '-c', '--git-dir', '--work-tree'}:
            if index + 1 >= len(words):
                return None
            index += 2
            continue
        if token.startswith(('--git-dir=', '--work-tree=')):
            index += 1
            continue
        if token.startswith('-'):
            return None
        return token.lower()
    return None


def _contains_nested_command_shell(words: list[str]) -> bool:
    shells = {'bash', 'sh', 'zsh', 'dash', 'ksh'}
    for shell_index, token in enumerate(words):
        if Path(token).name.lower() not in shells:
            continue
        for option in words[shell_index + 1:-1]:
            if re.fullmatch(r'-[A-Za-z]*c[A-Za-z]*', option):
                return True
    return False


def _has_unsafe_dispatcher_composition(words: list[str]) -> bool:
    if not words:
        return False
    shells = {'bash', 'sh', 'zsh', 'dash', 'ksh'}
    sensitive = {'git', 'gh', 'docker', 'npm', 'curl', 'wget'}
    outer = Path(words[0]).name.lower()
    if outer == 'xargs':
        dispatched = _literal_xargs_command(words)
        if dispatched is None:
            return any(Path(token).name.lower() in sensitive | shells for token in words[1:])
        if not dispatched:
            return False
        dispatched, ambiguous_wrapper = _unwrap_execution_wrappers(dispatched)
        if ambiguous_wrapper:
            return True
        if not dispatched:
            return False
        executable = Path(dispatched[0]).name.lower()
        if executable in shells:
            return True
        if executable == 'git':
            return _literal_git_subcommand(dispatched) != 'status'
        if executable in sensitive:
            return True
        if executable in {'echo', 'printf'}:
            return False
        if executable in {'env', 'sudo', 'doas', 'chroot', 'xargs'}:
            if any(Path(token).name.lower() in sensitive for token in dispatched[1:]):
                return True
        return _contains_nested_command_shell(dispatched[1:])
    if outer in sensitive | shells | {'cd', 'pushd', 'echo', 'printf'}:
        return False
    return _contains_nested_command_shell(words[1:])


def _command_directory_aliases(command: str, *, depth: int = 0) -> dict[str, str]:
    aliases: dict[str, str] = {}
    try:
        words = shlex.split(command)
    except ValueError:
        return {'shell': '<ambiguous>'}
    expects_command = True
    for word in words:
        if word in {'&&', '||', ';', '|'}:
            expects_command = True
            continue
        if not expects_command:
            continue
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', word):
            continue
        if word.startswith(('$', '`')) or '$(' in word or '${' in word:
            return {'command.dynamic-position': '<ambiguous>'}
        expects_command = False
    if any(word in {'cd', 'pushd'} for word in words) and os.environ.get('CDPATH'):
        return {'command.cdpath-environment': '<ambiguous>'}
    if any(word.startswith('CDPATH=') and word != 'CDPATH=' for word in words):
        return {'command.cdpath-assignment': '<ambiguous>'}
    if re.search(r'(?:\|\||(?<!\|)\|(?!\|)|;|[()])', command):
        return {'command.control-flow': '<ambiguous>'}
    assignment_index = 0
    while words and re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', words[0]):
        name, value = words[0].split('=', 1)
        if name in {'GIT_DIR', 'GIT_WORK_TREE'}:
            aliases[f'command.env.{name}[{assignment_index}]'] = value
            assignment_index += 1
        words = words[1:]
    if words and Path(words[0]).name.lower() == 'env':
        aliases['command.env-wrapper'] = '<ambiguous>'
        return aliases
    if words and Path(words[0]).name.lower() in {'sudo', 'doas'}:
        if len(words) < 2 or words[1].startswith('-'):
            aliases['command.wrapper-options'] = '<ambiguous>'
            return aliases
        words = words[1:]
    words, ambiguous_wrapper = _unwrap_execution_wrappers(words)
    if ambiguous_wrapper:
        aliases['command.wrapper-options'] = '<ambiguous>'
        return aliases
    if _has_unsafe_dispatcher_composition(words):
        aliases['command.dispatcher-composition'] = '<ambiguous>'
        return aliases
    if _contains_embedded_sensitive_command(words) and (
        not words
        or Path(words[0]).name.lower()
        not in {'cd', 'pushd', 'git', 'gh', 'docker', 'npm', 'curl', 'wget'}
    ):
        aliases['command.displaced-sensitive-executable'] = '<ambiguous>'
        return aliases
    if any(word in {'eval', 'source', '.'} for word in words):
        aliases['command.dynamic-shell'] = '<ambiguous>'
        return aliases
    if words and words[0] == 'exec':
        aliases['command.exec-shell'] = '<ambiguous>'
        return aliases
    if depth < 3 and words:
        executable = Path(words[0]).name.lower()
        if executable in {'bash', 'sh', 'zsh', 'dash', 'ksh'}:
            if len(words) != 3 or words[1] not in {'-c', '-lc'}:
                aliases['command.shell-options'] = '<ambiguous>'
                return aliases
            aliases.update({
                f'shell.{key}': value
                for key, value in _command_directory_aliases(words[2], depth=depth + 1).items()
            })
            return aliases
    directory_index = git_index = git_invocations = 0
    for index, word in enumerate(words):
        assignment = re.match(r'^(GIT_DIR|GIT_WORK_TREE)=(.*)$', word)
        if assignment:
            aliases[f'command.env.{assignment.group(1)}[{assignment_index}]'] = assignment.group(2)
            assignment_index += 1
        if word in {'cd', 'pushd'}:
            cursor = index + 1
            if cursor < len(words) and words[cursor] == '--':
                cursor += 1
            elif cursor < len(words) and words[cursor].startswith('-'):
                aliases[f'command.{word}[{directory_index}]'] = '<ambiguous>'
                directory_index += 1
                continue
            if cursor >= len(words) or words[cursor] in {'&&', '||', ';', '|'}:
                aliases[f'command.{word}[{directory_index}]'] = '<ambiguous>'
            else:
                aliases[f'command.{word}[{directory_index}]'] = words[cursor]
            directory_index += 1
        if Path(word).name == 'git':
            git_invocations += 1
            cursor = index + 1
            while cursor < len(words):
                if words[cursor] == '-c':
                    if cursor + 1 >= len(words):
                        aliases[f'command.git-config[{git_index}]'] = '<ambiguous>'
                        break
                    if not re.fullmatch(r'protocol\.version=\d+', words[cursor + 1]):
                        aliases[f'command.git-config[{git_index}]'] = '<ambiguous>'
                        break
                    cursor += 2
                    continue
                if words[cursor] == '-C':
                    if cursor + 1 >= len(words):
                        aliases[f'command.git-C[{git_index}]'] = '<ambiguous>'
                        break
                    aliases[f'command.git-C[{git_index}]'] = words[cursor + 1]
                    git_index += 1
                    cursor += 2
                    continue
                if words[cursor] in {'--git-dir', '--work-tree'}:
                    if cursor + 1 >= len(words):
                        aliases[f'command.git-root[{git_index}]'] = '<ambiguous>'
                        break
                    aliases[f'command.git-root[{git_index}]'] = words[cursor + 1]
                    git_index += 1
                    cursor += 2
                    continue
                if words[cursor].startswith(('--git-dir=', '--work-tree=')):
                    aliases[f'command.git-root[{git_index}]'] = words[cursor].split('=', 1)[1]
                    git_index += 1
                    cursor += 1
                    continue
                break
    if git_invocations > 1 and any('.git-' in key for key in aliases):
        aliases['command.multiple-git-roots'] = '<ambiguous>'
    return aliases


def root_context(payload: dict[str, Any], input_data: dict[str, Any], tool: str) -> RootContext:
    try:
        return _root_context(payload, input_data, tool)
    except (OSError, RuntimeError, ValueError):
        session_cwd = next(
            (str(payload[key]) for key in _SESSION_ROOT_ALIASES if payload.get(key) not in (None, '')),
            None,
        )
        return RootContext(session_cwd, None, {}, None, 'root-resolution-error')


def _root_context(payload: dict[str, Any], input_data: dict[str, Any], tool: str) -> RootContext:
    session_values = {
        key: str(payload[key]) for key in _SESSION_ROOT_ALIASES if payload.get(key) not in (None, '')
    }
    session_cwd = next(iter(session_values.values()), None)
    session_paths: list[Path] = []
    session_roots: set[Path] = set()
    recognized_session_values = 0
    for raw in session_values.values():
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        path = path.resolve()
        session_paths.append(path)
        recognized = _recognized_root(path)
        if recognized is not None:
            session_roots.add(recognized)
            recognized_session_values += 1
    if session_values and recognized_session_values != len(session_values):
        return RootContext(session_cwd, None, {}, None, 'unrecognized-session-root')
    if len(session_roots) > 1 or (session_values and len(session_roots) != 1):
        return RootContext(session_cwd, None, {}, None, 'ambiguous-session-root')
    session_root = next(iter(session_roots), None)

    command_values = {
        key: str(input_data[key]) for key in _COMMAND_ROOT_ALIASES if input_data.get(key) not in (None, '')
    }
    command = input_data.get('command')
    if tool == 'Bash' and isinstance(command, str):
        command_values.update(_command_directory_aliases(command))
    if not command_values:
        status = 'session-root' if session_root is not None else 'missing-root'
        return RootContext(session_cwd, session_root, {}, session_root, status)

    if '<ambiguous>' in command_values.values():
        return RootContext(session_cwd, session_root, command_values, None, 'ambiguous-command-root')
    base = session_paths[0] if session_paths else None
    shell_base = base
    git_base = base
    command_roots: set[Path] = set()
    declared_directories: set[Path] = set()
    for key, raw in command_values.items():
        if re.search(r'[$`*?\[\]{}()]', raw):
            return RootContext(session_cwd, session_root, command_values, None, 'ambiguous-command-root')
        try:
            path = Path(raw).expanduser()
        except (OSError, RuntimeError, ValueError):
            return RootContext(session_cwd, session_root, command_values, None, 'root-resolution-error')
        if not path.is_absolute():
            if '.git-C[' in key or '.git-root[' in key:
                resolution_base = git_base
            elif key.startswith(('command.', 'shell.')):
                resolution_base = shell_base
            else:
                resolution_base = base
            if resolution_base is None:
                return RootContext(session_cwd, session_root, command_values, None, 'unresolved-relative-root')
            path = resolution_base / path
        try:
            path = path.resolve()
        except (OSError, RuntimeError, ValueError):
            return RootContext(session_cwd, session_root, command_values, None, 'root-resolution-error')
        if '.cd[' in key or '.pushd[' in key:
            shell_base = path
            git_base = path
        elif '.git-C[' in key:
            git_base = path
        elif not key.startswith(('command.', 'shell.')):
            declared_directories.add(path)
            shell_base = path
            git_base = path
        recognized = _recognized_root(path)
        if recognized is None:
            return RootContext(session_cwd, session_root, command_values, None, 'unrecognized-command-root')
        command_roots.add(recognized)
    if len(declared_directories) > 1:
        return RootContext(session_cwd, session_root, command_values, None, 'ambiguous-command-root')
    if len(command_roots) != 1:
        return RootContext(session_cwd, session_root, command_values, None, 'ambiguous-command-root')
    effective_root = next(iter(command_roots))
    status = 'effective-root' if session_root in (None, effective_root) else 'cross-root'
    return RootContext(session_cwd, session_root, command_values, effective_root, status)


def session_id(payload: dict[str, Any]) -> str:
    return str(first(payload.get('session_id'), payload.get('sessionId'), 'manual'))


def prompt_text(payload: dict[str, Any]) -> str:
    return str(first(payload.get('prompt'), payload.get('userPrompt'), payload.get('user_prompt'), '') or '')


def tool_name(payload: dict[str, Any]) -> str:
    raw = str(first(payload.get('tool_name'), payload.get('toolName'), '') or '')
    return TOOL_ALIASES.get(raw, raw)


def tool_input(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get('tool_input')
    if value is None:
        value = payload.get('toolInput')
    if not isinstance(value, dict):
        return {}
    mapped = dict(value)
    if 'subagent_type' in mapped and 'agent_type' not in mapped:
        mapped['agent_type'] = mapped['subagent_type']
    if 'agentType' in mapped and 'agent_type' not in mapped:
        mapped['agent_type'] = mapped['agentType']
    return mapped


def agent_id(payload: dict[str, Any]) -> str:
    return str(first(
        payload.get('agent_id'),
        payload.get('agentId'),
        payload.get('subagent_id'),
        payload.get('subagentId'),
        'unknown',
    ))


def agent_type(payload: dict[str, Any]) -> str:
    nested = tool_input(payload)
    return str(first(
        payload.get('agent_type'),
        payload.get('agentType'),
        payload.get('subagent_type'),
        payload.get('subagentType'),
        nested.get('agent_type'),
        nested.get('subagent_type'),
        'unknown',
    ))


def stop_hook_active(payload: dict[str, Any]) -> bool:
    return bool(first(payload.get('stop_hook_active'), payload.get('stopHookActive'), False))


_CHILD_KEYS = (
    'agent_id', 'agentId', 'subagent_id', 'subagentId',
    'agent_type', 'agentType', 'subagent_type', 'subagentType',
)
_CHILD_BRIEF = re.compile(r'^\s*You are \w+', re.IGNORECASE)


def is_child_payload(payload: dict[str, Any]) -> bool:
    if any(payload.get(key) not in (None, '') for key in _CHILD_KEYS):
        return True
    return bool(_CHILD_BRIEF.match(prompt_text(payload)))
