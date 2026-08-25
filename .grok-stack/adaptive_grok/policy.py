from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from . import _policy_legacy as _legacy
from ._policy_legacy import *  # noqa: F401,F403
from .shell_targets import control_plane_shell_mutation

_LEGACY_SHELL_GUARD = threading.Lock()
WORKFLOW_DISPATCH_POLICY = 'workflow-dispatch is forbidden'


def evaluate_pre_tool(root: Path, event: dict[str, Any]) -> tuple[bool, str | None]:
    tool = str(event.get('tool_name', ''))
    tool_input = event.get('tool_input') or {}
    if tool != 'Bash':
        return _legacy.evaluate_pre_tool(root, event)

    config = _legacy.load_json(root / '.grok-stack/config/policy.json', {}) or {}
    if not isinstance(config, dict):
        config = {}
    control_plane = _legacy._configured_patterns(
        config,
        'control_plane_paths',
        _legacy.DEFAULT_CONTROL_PLANE,
    )
    command = str(tool_input.get('command', '')) if isinstance(tool_input, dict) else str(tool_input)
    protected_targets, opaque = control_plane_shell_mutation(root, command, control_plane)
    if protected_targets:
        targets = ', '.join(protected_targets)
        return False, (
            f'Blocked control-plane shell mutation targeting {targets}; use a structured write '
            '(Edit/Write/apply_patch) with an exact protected-path grant for each target.'
        )
    if opaque:
        return False, (
            'Blocked opaque control-plane shell mutation; split the command or use Edit/Write/apply_patch '
            'so targets are explicit repository-relative paths. Do not create a protected-path grant until '
            'the exact targets are known.'
        )

    # The legacy evaluator still owns destructive, production, external-write, route and MCP policy.
    # Disable only its substring-based control-plane guard while it evaluates this one invocation.
    with _LEGACY_SHELL_GUARD:
        original = _legacy._is_control_plane_shell_mutation
        _legacy._is_control_plane_shell_mutation = lambda _command, _patterns: False
        try:
            return _legacy.evaluate_pre_tool(root, event)
        finally:
            _legacy._is_control_plane_shell_mutation = original


def __getattr__(name: str) -> Any:
    return getattr(_legacy, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_legacy)))
