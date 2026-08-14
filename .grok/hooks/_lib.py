from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

HOOK_DIR = Path(__file__).resolve().parent
REPO_CANDIDATE = HOOK_DIR.parents[1]
STACK = REPO_CANDIDATE / '.grok-stack'
if str(STACK) not in sys.path:
    sys.path.insert(0, str(STACK))

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
