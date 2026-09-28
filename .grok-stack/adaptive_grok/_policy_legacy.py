from __future__ import annotations

import fnmatch
import os
import re
import shlex
import stat
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


# Git global options whose next word is the value, not the subcommand. On git 2.43
# `--namespace foo` and `--attr-source HEAD` are this shape; treating the option as one
# flag stops the scan on the value and hides a later `-C` or `push`. Stuck `=` forms are
# one word. `-C` reaches this classifier already lowercased to `-c`.
_GIT_GLOBAL_VALUE_OPTIONS = {'-c', '--git-dir', '--work-tree', '--namespace', '--attr-source'}
_GIT_GLOBAL_EQUALS_PREFIXES = ('--git-dir=', '--work-tree=', '--namespace=', '--attr-source=')
_GIT_SELECTOR_VALUE_OPTIONS = _GIT_GLOBAL_VALUE_OPTIONS | {'-C'}


def _production_action(argv: list[str]) -> str | None:
    if argv and argv[0] == 'git':
        index = 1
        while index < len(argv):
            if index + 1 < len(argv) and argv[index] in _GIT_GLOBAL_VALUE_OPTIONS:
                index += 2
                continue
            if argv[index].startswith(_GIT_GLOBAL_EQUALS_PREFIXES):
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
        if token == '--':  # nosec B105
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
        if token in _GIT_SELECTOR_VALUE_OPTIONS:
            if index + 1 >= len(argv):
                return len(argv)
            index += 2
            continue
        if token.startswith(_GIT_GLOBAL_EQUALS_PREFIXES):
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
    if remaining and Path(remaining[0]).name.lower() == 'sudo':
        index = 1
        if index < len(remaining) and remaining[index] == '-E':
            index += 1
        if index >= len(remaining) or remaining[index].startswith('-'):
            return remaining, False
        remaining = remaining[index:]
    elif remaining and Path(remaining[0]).name.lower() == 'doas':
        index = 1
        if index + 1 < len(remaining) and remaining[index] == '-u':
            index += 2
        if index >= len(remaining) or remaining[index].startswith('-'):
            return remaining, False
        remaining = remaining[index:]
    elif remaining and Path(remaining[0]).name.lower() == 'env':
        index = 1
        while index < len(remaining) and re.match(
            r'^[A-Za-z_][A-Za-z0-9_]*=', remaining[index]
        ):
            index += 1
        if index >= len(remaining) or remaining[index].startswith('-'):
            return remaining, False
        remaining = remaining[index:]
    remaining, ambiguous_wrapper = _unwrap_execution_wrappers(remaining)
    return remaining, not ambiguous_wrapper


def _literal_shell_payload(tokens: list[str]) -> str | None:
    if not tokens or Path(tokens[0]).name.lower() not in _SHELL_EXECUTABLES:
        return None
    if len(tokens) == 3 and tokens[1] in {'-c', '-lc'}:
        return tokens[2]
    if len(tokens) == 4 and tokens[1] == '--noprofile' and tokens[2] in {'-c', '-lc'}:
        return tokens[3]
    return None


def _exact_outer_shell_payload(raw_command: str) -> str | None:
    tokens = _command_tokens(raw_command)
    if tokens is None:
        return None
    bounded, proven = _bounded_command(tokens)
    if not proven:
        return None
    return _literal_shell_payload(bounded)


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
    shell_payload = _exact_outer_shell_payload(raw_command)
    if shell_payload is not None:
        return _analyze_authority_pieces(shell_payload, shell_depth=1)
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


# --- push repository binding (issue #58) -------------------------------------
# A delegated production grant is bound to the policy root's repository, HEAD and
# tree, but a `git push` resolves the repository it writes through the shell's
# working directory and git's own upward `.git` discovery. The two disagree whenever
# a command line carries a `cd`/`pushd`, an explicit `-C`/`--git-dir`/`--work-tree`,
# or a tool-level working directory that reaches another repository. Everything in
# this section is new; the only existing code it touches is one call site in
# evaluate_pre_tool().

# The gate that decides whether a command line is worth walking at all is `_mentions_push()`
# below: a `\bgit\b[^\n]*\bpush\b` regex looks shorter but backtracks quadratically on a long
# line, and the hook runs this on every Bash call.
_COMMAND_GROUP_SEPARATORS = {'&&', '||', ';', '|', '&'}
_SHELL_PUNCTUATION = ';&|(){}'
_CD_EXECUTABLES = {'cd', 'pushd'}
_DRY_RUN_PUSH_OPTIONS = {'-n', '--dry-run', '--noop'}
_GIT_DIR_OPTIONS = {'--git-dir'}
_WORK_TREE_OPTIONS = {'--work-tree'}
_GIT_ENV_NAMES = {'GIT_DIR', 'GIT_WORK_TREE'}
_PUSH_WRAPPER_PREFIXES = {'env', 'sudo', 'doas'}
#: Wrapper options that carry a separate operand, so the loop must drop the operand too.
#: Skipping only `-u` leaves `LC_ALL` as the executable and hides the `git` behind it.
_PUSH_WRAPPER_VALUE_OPTIONS = {'-u', '--unset', '-S', '--split-string', '--default-path'}
#: Wrapper options that move the working directory, so the walk has to follow the move.
_PUSH_WRAPPER_CHDIR_OPTIONS = {'-C', '--chdir'}
#: Executables that run their own operands, so a `git push` sitting after them is real.
_PUSH_DISPATCHER_EXECUTABLES = {
    'env', 'xargs', 'parallel', 'sudo', 'doas', 'nohup', 'setsid', 'nice', 'ionice',
    'stdbuf', 'taskset', 'time', 'timeout', 'watch', 'command', 'exec', 'eval',
}
#: Shell builtins that put a variable into the environment of every later command on the line.
_PUSH_ENV_BUILTINS = {'export', 'declare', 'typeset', 'readonly', 'local', 'unset'}
#: A shell grouping character, or a word the shell has not finished building, in the executable
#: position: `(cd x && git push)`, `{ cd x; git push; }` and `$SCRIPT` all hide what gets run,
#: so nothing the walk concludes about the rest of the line can be trusted.
_PUSH_OBSTRUCTED_EXECUTABLE = re.compile(r'[(){};|&$*?\\`]')
#: Shell punctuation a tokenizer leaves glued to a word inside a group or brace construct.
_PUSH_WORD_GLUE = '(){};,&|'
#: How many literal shell-payload levels one line may nest before it stops being readable.
_PUSH_SHELL_DEPTH = 3
#: Push options that take a separate operand, so their value is never the destination.
_PUSH_VALUE_OPTIONS = {'--receive-pack', '--exec', '-o', '--push-option'}
_PUSH_DESTINATION_OPTIONS = {'--repo'}
_PUSH_FLAG_OPTIONS = {
    '--all', '--branches', '--tags', '--follow-tags', '--atomic', '--thin', '--no-thin',
    '--porcelain', '--progress', '--no-progress', '--set-upstream', '--no-verify', '--signed',
    '--no-signed', '--ipv4', '--ipv6', '-n', '--dry-run', '--noop', '-u', '-v', '--verbose',
    '-q', '--quiet', '-4', '-6',
}
_DESTRUCTIVE_PUSH_OPTIONS = {
    '--force', '--mirror', '--delete', '--prune', '--force-if-includes', '-f', '-d',
}
_SAFE_PUSH_CONFIG = re.compile(r'^protocol\.version=\d+$', re.IGNORECASE)
#: Longest command line the walk will tokenize, chosen from the measured cost below (~0.15 s).
_PUSH_SCAN_LIMIT = 65_536
#: The repository-local config is untrusted mutable input outside the Git tree/grant binding.
#: It needs its own cap because the command scan bound says nothing about this filesystem read.
_GIT_CONFIG_LIMIT = 131_072
_GIT_POINTER_LIMIT = 4_096
#: The one list of tool parameters that name the directory a command runs in. The installed
#: hook re-roots with it and the push guard reads the declared base with it, so a parameter
#: added here closes the same hole on both surfaces instead of drifting into two lists.
COMMAND_ROOT_ALIASES = ('workdir', 'cwd', 'working_directory', 'workingDirectory', 'directory')
_LITERAL_PATH_MARKERS = ('$', '`', '*', '?', '[', '{', '(', ')', '\n', '\\')


@dataclass(frozen=True)
class PushInvocation:
    """Where one literal `git push` on a command line will resolve its repository."""

    directory: Path | None
    git_directory: Path | None
    work_tree: Path | None
    unresolved: bool
    dry_run: bool
    #: Operands following the `push` word, kept so the destination can be read too. A push
    #: the parser could not attribute at all carries no operands and is already unresolved.
    args: tuple[str, ...] = ()


def _literal_path(base: Path, raw: str | None) -> Path | None:
    """Resolve one literal path operand against *base*; None when it is not literal."""
    if not raw or raw in {'-', '--'} or any(marker in raw for marker in _LITERAL_PATH_MARKERS):
        return None
    candidate = Path(raw)
    if raw.startswith('~'):
        try:
            candidate = candidate.expanduser()
        except (OSError, RuntimeError, ValueError):
            return None
        if str(candidate).startswith('~'):
            # An unresolvable `~user` is not a literal path: git would pass the word through
            # unchanged, so the guard cannot name the repository it reaches.
            return None
    if not candidate.is_absolute():
        candidate = base / candidate
    try:
        return candidate.resolve()
    except OSError:
        return None


def _nearest_repository(directory: Path) -> Path | None:
    """git's own repository discovery: the nearest enclosing directory that holds .git."""
    try:
        for candidate in (directory, *directory.parents):
            if (candidate / '.git').exists():
                return candidate
    except OSError:
        return None
    return None


def _literal_shell_tokens(text: str) -> list[str] | None:
    """Tokenize literal shell text with control punctuation preserved as separate words."""
    normalized: list[str] = []
    quote = ''
    index = 0
    while index < len(text):
        char = text[index]
        if quote:
            normalized.append(char)
            if char == '\\' and quote == '"' and index + 1 < len(text):
                normalized.append(text[index + 1])
                index += 2
                continue
            if char == quote:
                quote = ''
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == '\n':
            # Spaced so the separator survives as its own token: gluing `&&` straight onto the
            # last word fuses two command groups and silently deletes the `cd` between them.
            normalized.append(' ; ')
            index += 1
            continue
        normalized.append(char)
        index += 1
    if quote:
        return None
    try:
        lexer = shlex.shlex(
            ''.join(normalized),
            posix=True,
            punctuation_chars=_SHELL_PUNCTUATION,
        )
        lexer.whitespace_split = True
        lexer.commenters = ''
        return list(lexer)
    except ValueError:
        return None


def _literal_command_groups(text: str) -> list[list[str]] | None:
    """Split a command line into quote-aware groups; None when the syntax is not literal."""
    tokens = _literal_shell_tokens(text)
    if tokens is None:
        return None
    groups: list[list[str]] = [[]]
    for token in tokens:
        if token in _COMMAND_GROUP_SEPARATORS:
            groups.append([])
            continue
        groups[-1].append(token)
    return [group for group in groups if group]


def _split_git_env_prefix(
    tokens: list[str],
    cwd: Path,
) -> tuple[Path | None, Path | None, bool, list[str], Path]:
    """Peel a wrapper/assignment prefix, returning the git environment and directory it sets.

    The last item is the directory the peeled command runs in: `env -C <dir>` moves it exactly
    like a `cd` does, and dropping the operand without applying the move would hand the walk a
    push that looks like it stayed where the grant is bound.
    """
    git_dir: Path | None = None
    work_tree: Path | None = None
    unresolved = False
    dropped = False
    moved = cwd
    rest = list(tokens)
    while rest:
        head = rest[0]
        assignment = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', head)
        if assignment:
            name = assignment.group(1)
            if name.startswith('GIT_CONFIG_'):
                unresolved = True
            if name in _GIT_ENV_NAMES:
                resolved = _literal_path(moved, assignment.group(2))
                unresolved = unresolved or resolved is None
                if name == 'GIT_DIR':
                    git_dir = resolved
                else:
                    work_tree = resolved
            rest = rest[1:]
            dropped = True
            continue
        if Path(head).name.lower() in _PUSH_WRAPPER_PREFIXES:
            rest = rest[1:]
            dropped = True
            continue
        if dropped and head.startswith('-'):
            # An option belonging to the wrapper. Some of them carry a separate operand, and
            # dropping only the flag leaves that operand standing where the executable was.
            inline = head.split('=', 1)
            if len(inline) == 2 and inline[0] in _PUSH_WRAPPER_CHDIR_OPTIONS:
                resolved = _literal_path(moved, inline[1])
                unresolved = unresolved or resolved is None
                if resolved is not None:
                    moved = resolved
                rest = rest[1:]
                dropped = True
                continue
            if head in _PUSH_WRAPPER_VALUE_OPTIONS or head in _PUSH_WRAPPER_CHDIR_OPTIONS:
                if len(rest) < 2:
                    unresolved = True
                    rest = rest[1:]
                else:
                    if head in _PUSH_WRAPPER_CHDIR_OPTIONS:
                        resolved = _literal_path(moved, rest[1])
                        unresolved = unresolved or resolved is None
                        if resolved is not None:
                            moved = resolved
                    rest = rest[2:]
            else:
                rest = rest[1:]
            dropped = True
            continue
        break
    return git_dir, work_tree, unresolved, rest, moved


@dataclass
class _PushWalk:
    """What the shell carries from one command group to the next on the same line.

    A `cd`, an `env -C`, or an `export GIT_DIR` in one group is still in force for the groups
    after it, so the walk has to hold that state instead of restarting per group.
    """

    cwd: Path
    git_dir: Path | None = None
    work_tree: Path | None = None
    obstructed: bool = False

    def child(self) -> _PushWalk:
        """A nested shell inherits this state, and its own changes never come back out."""
        return _PushWalk(self.cwd, self.git_dir, self.work_tree)


def _absorb_env_builtin(walk: _PushWalk, tokens: list[str]) -> bool:
    """Apply `export`/`declare`/`unset` on the git environment the walk carries; False = unknown.

    Without this, `export GIT_DIR=<foreign>/.git && git push origin HEAD` runs in the granted
    directory, so every directory test passes, while git writes the ref into another repository.
    """
    proven = True
    clearing = Path(tokens[0]).name.lower() == 'unset'

    def current(name: str) -> Path | None:
        return walk.git_dir if name == 'GIT_DIR' else walk.work_tree

    def store(name: str, value: Path | None) -> None:
        if name == 'GIT_DIR':
            walk.git_dir = value
        else:
            walk.work_tree = value

    for token in tokens[1:]:
        if token.startswith('-'):
            continue
        assignment = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', token)
        name = assignment.group(1) if assignment else token
        if name.startswith('GIT_CONFIG_'):
            proven = False
            continue
        if name not in _GIT_ENV_NAMES:
            continue
        if assignment is None:
            if clearing:
                store(name, None)
                continue
            # `export GIT_DIR` republishes a value the line never states.
            if current(name) is None:
                proven = False
            continue
        resolved = _literal_path(walk.cwd, assignment.group(2))
        if resolved is None:
            proven = False
        store(name, resolved)
    return proven


def _collect_push_invocations(
    groups: list[list[str]],
    walk: _PushWalk,
    depth: int,
    found: list[PushInvocation],
) -> bool:
    """Append every push reachable from *groups*; return False when the walk is not literal."""
    proven = True
    for group in groups:
        prefix_git_dir, prefix_work_tree, env_unresolved, remainder, moved = (
            _split_git_env_prefix(group, walk.cwd)
        )
        walk.cwd = moved
        if not remainder:
            # An assignment-only group: the shell keeps GIT_DIR/GIT_WORK_TREE for later groups.
            proven = proven and not env_unresolved
            if prefix_git_dir is not None:
                walk.git_dir = prefix_git_dir
            if prefix_work_tree is not None:
                walk.work_tree = prefix_work_tree
            continue
        bounded, bounded_proven = _bounded_command(remainder)
        proven = proven and bounded_proven
        if not bounded:
            # A wrapper the classifier refused to unwrap: what it runs is unknown to the walk.
            walk.obstructed = True
            if _dispatched_push(group, require_dispatcher=False):
                found.append(_unattributable_push())
            continue
        executable = Path(bounded[0]).name.lower()
        if _PUSH_OBSTRUCTED_EXECUTABLE.search(bounded[0]) is not None:
            # `(cd x && git push)` and `{ cd x; git push; }` hand the walk a word that is not
            # a program. Whatever the groups inside them do, this line cannot be traced.
            walk.obstructed = True
            if _dispatched_push(group, require_dispatcher=False):
                found.append(_unattributable_push())
            continue
        if executable in _SHELL_EXECUTABLES:
            if depth >= _PUSH_SHELL_DEPTH:
                walk.obstructed = True
                continue
            payload = _literal_shell_payload(bounded)
            if payload is None:
                # A shell whose script is not a literal word could hold any command, so the
                # absence of a visible push in it is not evidence that none runs.
                walk.obstructed = True
                continue
            inner = _literal_command_groups(payload)
            if inner is None:
                proven = False
                continue
            nested = walk.child()
            proven = _collect_push_invocations(inner, nested, depth + 1, found) and proven
            walk.obstructed = walk.obstructed or nested.obstructed
            continue
        if executable in _PUSH_ENV_BUILTINS:
            proven = _absorb_env_builtin(walk, bounded) and proven
            continue
        if executable in _CD_EXECUTABLES:
            operand = 2 if len(bounded) > 1 and bounded[1] == '--' else 1
            if operand >= len(bounded) or operand + 1 < len(bounded):
                proven = False
                continue
            moved = _literal_path(walk.cwd, bounded[operand])
            if moved is None:
                proven = False
                continue
            walk.cwd = moved
            continue
        if executable != 'git':
            if _dispatched_push(group):
                found.append(_unattributable_push())
            continue
        directory = walk.cwd
        git_directory = prefix_git_dir if prefix_git_dir is not None else walk.git_dir
        work_tree = prefix_work_tree if prefix_work_tree is not None else walk.work_tree
        unresolved = env_unresolved
        # An option value that is not one literal word may still expand to several words, so
        # `git -C $(echo /a /b) push` shifts the whole rest of the line out of place.
        shifted = env_unresolved
        index = 1
        while index < len(bounded):
            option = bounded[index]
            if option == '-C' or option in _GIT_DIR_OPTIONS or option in _WORK_TREE_OPTIONS:
                value = bounded[index + 1] if index + 1 < len(bounded) else None
                resolved = _literal_path(directory, value)
                if resolved is None:
                    unresolved = True
                    shifted = True
                elif option == '-C':
                    directory = resolved
                elif option in _GIT_DIR_OPTIONS:
                    git_directory = resolved
                else:
                    work_tree = resolved
                index += 2
                continue
            if option.startswith('--git-dir='):
                resolved = _literal_path(directory, option.split('=', 1)[1])
                git_directory = resolved
                unresolved = unresolved or resolved is None
                shifted = shifted or resolved is None
                index += 1
                continue
            if option.startswith('--work-tree='):
                resolved = _literal_path(directory, option.split('=', 1)[1])
                work_tree = resolved
                unresolved = unresolved or resolved is None
                shifted = shifted or resolved is None
                index += 1
                continue
            if option == '-c' or option.startswith('-c'):
                value = bounded[index + 1] if option == '-c' and index + 1 < len(bounded) else option[2:]
                if not value or _SAFE_PUSH_CONFIG.fullmatch(value) is None:
                    unresolved = True
                if option == '-c' and index + 1 >= len(bounded):
                    shifted = True
                index += 2 if option == '-c' else 1
                continue
            if option == '--config-env' or option.startswith('--config-env='):
                unresolved = True
                if option == '--config-env' and index + 1 >= len(bounded):
                    shifted = True
                index += 2 if option == '--config-env' else 1
                continue
            if option in {'--namespace', '--attr-source'}:
                # The value is not a repository selector. Consume it so a later `-C`/`push`
                # stays visible; a missing value shifts the rest of the line.
                if index + 1 >= len(bounded):
                    unresolved = True
                    shifted = True
                    index += 1
                else:
                    index += 2
                continue
            if option.startswith('-'):
                index += 1
                continue
            break
        if index >= len(bounded) or bounded[index].lower() != 'push':
            if shifted and any(token.lower() == 'push' for token in bounded[index:]):
                found.append(_unattributable_push())
            continue
        operands = bounded[index + 1:]
        flags = [token.lower() for token in operands]
        found.append(PushInvocation(
            directory=directory,
            git_directory=git_directory,
            work_tree=work_tree,
            unresolved=unresolved,
            dry_run=any(flag in _DRY_RUN_PUSH_OPTIONS for flag in flags),
            args=tuple(operands),
        ))
    return proven


def _unattributable_push() -> PushInvocation:
    """A push the line plainly runs but whose repository the walk cannot name."""
    return PushInvocation(
        directory=None,
        git_directory=None,
        work_tree=None,
        unresolved=True,
        dry_run=False,
    )


def _dispatched_push(group: list[str], *, require_dispatcher: bool = True) -> bool:
    """True when a group plainly runs `git ... push` that the walk did not attribute.

    `xargs -I{} git -C <path> push {} feature` leaves the parser standing on a word that is not
    `git`, so the push inside the operand list is never tied to any directory, while xargs would
    exec it all the same. For a group the walk could not classify at all (`{ cd x; git push; }`)
    the same reading applies without the dispatcher test: the construct is not a program name.
    """
    if not group:
        return False
    words = [token.strip(_PUSH_WORD_GLUE).lower() for token in group]
    if require_dispatcher and Path(words[0]).name not in _PUSH_DISPATCHER_EXECUTABLES:
        return False
    names = [Path(word).name for word in words[1:]]
    if 'git' not in names:
        return False
    head = names.index('git')
    return any(word == 'push' for word in names[head + 1:])


def _read_bounded_regular_text(path: Path, limit: int) -> str | None:
    """Read one stable regular file without following a leaf symlink or exceeding *limit*."""
    try:
        expected = path.lstat()
    except OSError:
        return None
    if not stat.S_ISREG(expected.st_mode) or expected.st_size > limit:
        return None
    flags = (
        os.O_RDONLY
        | getattr(os, 'O_CLOEXEC', 0)
        | getattr(os, 'O_NOFOLLOW', 0)
        | getattr(os, 'O_NONBLOCK', 0)
    )
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return None
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size > limit
            or (expected.st_dev, expected.st_ino) != (before.st_dev, before.st_ino)
        ):
            return None
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b''.join(chunks)
        after = os.fstat(descriptor)
        stable = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) == (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if not stable or len(data) > limit or len(data) != after.st_size:
            return None
        return data.decode('utf-8', errors='replace')
    except OSError:
        return None
    finally:
        os.close(descriptor)


def _configured_remotes(repository: Path) -> dict[str, _ConfiguredRemote] | None:
    """remote name -> fetch url and pushurl values; None when the config cannot be read."""
    marker = repository / '.git'
    try:
        marker_mode = marker.lstat().st_mode
        if stat.S_ISDIR(marker_mode):
            config = marker / 'config'
        elif stat.S_ISREG(marker_mode):
            marker_text = _read_bounded_regular_text(marker, _GIT_POINTER_LIMIT)
            if marker_text is None:
                return None
            match = re.match(r'^gitdir:\s*(.+)$', marker_text.strip())
            if match is None:
                return None
            git_directory = Path(match.group(1))
            if not git_directory.is_absolute():
                git_directory = repository / git_directory
            git_directory = git_directory.resolve()
            common = git_directory / 'commondir'
            if common.exists():
                common_text = _read_bounded_regular_text(common, _GIT_POINTER_LIMIT)
                if common_text is None:
                    return None
                relative = Path(common_text.strip())
                git_directory = (
                    relative if relative.is_absolute() else git_directory / relative
                ).resolve()
            config = git_directory / 'config'
        else:
            return None
        config_text = _read_bounded_regular_text(config, _GIT_CONFIG_LIMIT)
        if config_text is None:
            return None
        lines = config_text.splitlines()
    except OSError:
        return None
    found: dict[str, dict[str, Any]] = {}
    current: str | None = None
    for line in lines:
        section = re.match(r'^\s*\[\s*remote\s+"((?:[^"\\]|\\.)*)"\s*\]\s*(?:[#;].*)?$', line)
        if section:
            current = section.group(1).replace('\\"', '"').replace('\\\\', '\\')
            continue
        if line.lstrip().startswith('['):
            current = None
            continue
        if current is None:
            continue
        push_entry = re.match(r'^\s*pushurl\s*=\s*(.*?)\s*(?:[#;].*)?$', line)
        if push_entry:
            bucket = found.setdefault(current, {'url': None, 'pushurls': []})
            value = push_entry.group(1).strip().rstrip('/')
            if value:
                bucket['pushurls'].append(value)
            continue
        entry = re.match(r'^\s*url\s*=\s*(.*?)\s*(?:[#;].*)?$', line)
        if entry:
            bucket = found.setdefault(current, {'url': None, 'pushurls': []})
            bucket['url'] = entry.group(1).strip().rstrip('/')
    return {
        name: _ConfiguredRemote(url=item['url'], pushurls=tuple(item['pushurls']))
        for name, item in found.items()
    }


@dataclass(frozen=True)
class _ConfiguredRemote:
    """Fetch url and pushurl overrides from one `[remote]` section.

    With no pushurl, git pushes to the fetch url. Any pushurl replaces that url for the push.
    """

    url: str | None = None
    pushurls: tuple[str, ...] = ()


@dataclass(frozen=True)
class _ParsedPushArguments:
    destination: str | None
    refspecs: tuple[str, ...]
    unresolved: bool
    destructive: bool


def _parse_push_arguments(push: PushInvocation) -> _ParsedPushArguments:
    """Parse supported `git push` options without letting values shift the destination."""
    index = 0
    destination_override: str | None = None
    positionals: list[str] = []
    unresolved = False
    destructive = False
    options = True
    while index < len(push.args):
        token = push.args[index]
        lowered = token.lower()
        if options and token == '--':  # nosec B105
            options = False
            index += 1
            continue
        if options and token in _PUSH_DESTINATION_OPTIONS | _PUSH_VALUE_OPTIONS:
            if index + 1 >= len(push.args):
                unresolved = True
                index += 1
                continue
            if token in _PUSH_DESTINATION_OPTIONS:
                value = push.args[index + 1]
                unresolved = unresolved or (
                    destination_override is not None and destination_override != value
                )
                destination_override = value
            index += 2
            continue
        if options and any(token.startswith(f'{option}=') for option in _PUSH_DESTINATION_OPTIONS):
            value = token.split('=', 1)[1]
            unresolved = unresolved or not value or (
                destination_override is not None and destination_override != value
            )
            destination_override = value or destination_override
            index += 1
            continue
        if options and any(token.startswith(f'{option}=') for option in _PUSH_VALUE_OPTIONS):
            unresolved = unresolved or not token.split('=', 1)[1]
            index += 1
            continue
        if options and (
            lowered in _DESTRUCTIVE_PUSH_OPTIONS
            or lowered.startswith('--force-with-lease=')
        ):
            destructive = True
            index += 1
            continue
        if options and lowered == '--force-with-lease':
            destructive = True
            index += 1
            continue
        if options and (lowered.startswith('--signed=') or lowered.startswith('--recurse-submodules=')):
            index += 1
            continue
        if options and lowered in _PUSH_FLAG_OPTIONS:
            index += 1
            continue
        if options and token.startswith('-o') and token != '-o':  # nosec B105
            index += 1
            continue
        if options and token.startswith('-') and not token.startswith('--'):
            flags = token[1:]
            if flags and set(flags) <= set('nuvq46fd'):
                destructive = destructive or 'f' in flags or 'd' in flags
                index += 1
                continue
            unresolved = True
            index += 1
            continue
        if options and token.startswith('--'):
            unresolved = True
            index += 1
            continue
        positionals.append(token)
        index += 1
    if destination_override is None:
        destination = positionals[0] if positionals else None
        refspecs = tuple(positionals[1:])
    else:
        destination = destination_override
        refspecs = tuple(positionals)
    destructive = destructive or any(refspec.startswith('+') for refspec in refspecs)
    return _ParsedPushArguments(destination, refspecs, unresolved, destructive)


def _push_destructive_reason(bound: Path, push: PushInvocation) -> str | None:
    parsed = _parse_push_arguments(push)
    if not parsed.destructive:
        return None
    return (
        'Blocked destructive git push by repository policy: force, lease, deletion, mirror, '
        'prune, and +refspec forms are not authorized by a repository-bound push grant. Use a '
        'non-force refspec only; independently observed remote-tip ancestry remains a separate '
        f'delivery prerequisite for {bound}.'
    )


def _push_destination_reason(bound: Path, push: PushInvocation) -> str | None:
    """Refuse a push whose destination is not a remote of the repository the grant names.

    Binding the *local* repository is only half of the question: `git push <url> <ref>` writes
    somewhere else entirely while reading its objects from the granted checkout, so an injected
    second operand spends the grant on a repository nobody approved. A destination is admissible
    only when the bound repository itself names it - a configured remote whose pushurl is
    absent or equal to its fetch url, that fetch url, or the repository's own path.
    """
    parsed = _parse_push_arguments(push)
    if parsed.unresolved:
        return _push_unresolved_reason(bound)
    destination = parsed.destination
    if destination is None:
        # No operand at all: git resolves the destination from the bound repository's config.
        return None
    explicit = f'git -C {bound} push <remote> <commit-ish>:<ref>'
    remotes = _configured_remotes(bound)
    if remotes is not None and destination in remotes:
        remote = remotes[destination]
        if not remote.pushurls or (
            remote.url is not None and all(item == remote.url for item in remote.pushurls)
        ):
            return None
        joined = ', '.join(remote.pushurls)
        return (
            'Blocked git push: it names destination '
            f'{destination}, whose pushurl ({joined}) is not the configured url of that '
            f'remote in {bound}. The grant covers the configured url only. Push to one of its '
            f'remotes by name: {explicit}.'
        )
    configured_urls = {remote.url for remote in (remotes or {}).values() if remote.url}
    if destination.rstrip('/') in configured_urls:
        return None
    if any(marker in destination for marker in _LITERAL_PATH_MARKERS):
        return (
            'Blocked git push: its destination is written with syntax that cannot be read as one '
            f'literal repository, so it cannot be matched against the remotes of {bound}. Push to '
            f'a remote by name instead: {explicit}.'
        )
    spelled = _literal_path(bound, destination)
    if spelled is not None and spelled == bound.resolve():
        return None
    if remotes is None:
        stated = f'its remote configuration could not be read from {bound}'
    else:
        named = ', '.join(sorted(remotes)) or 'no configured remote'
        stated = f'its configured remotes are: {named}'
    return (
        f'Blocked git push: it names destination {destination}, which is not a remote of the '
        f'repository the delegated grant is bound to ({bound}; {stated}). '
        f'The grant covers ref writes in that repository only. Push to one of its remotes by '
        f'name: git -C {bound} push <remote> <commit-ish>:<ref>.'
    )


def _resolve_directory(directory: Path) -> Path:
    """Canonical spelling of a directory the walk starts from; unchanged when unreadable."""
    try:
        return directory.resolve()
    except OSError:
        return directory


def _push_base_directory(root: Path, tool_input: Any) -> tuple[Path, bool]:
    """The directory the harness will run the command in, when it declares one."""
    if not isinstance(tool_input, dict):
        return _resolve_directory(root), True
    declared = [
        str(tool_input[key])
        for key in COMMAND_ROOT_ALIASES
        if tool_input.get(key) not in (None, '')
    ]
    if not declared:
        return _resolve_directory(root), True
    # Compare resolved paths: a harness that states the same directory twice with different
    # spelling (`/a/b` and `/a/b/`) declares one base, not a conflict, and a conflict here is
    # what denies every legitimate push instead of only the ambiguous ones.
    resolved: set[Path] = set()
    for value in declared:
        base = _literal_path(root, value)
        if base is None:
            return root, False
        resolved.add(base)
    if len(resolved) > 1:
        return root, False
    return next(iter(resolved)), True


def _inherited_git_env(base: Path) -> tuple[Path | None, Path | None, bool]:
    """GIT_DIR/GIT_WORK_TREE the harness already hands every command it starts.

    git obeys those over any working directory, so a session that inherited one from outside the
    granted repository would push elsewhere with nothing on the command line to read.
    """
    git_dir: Path | None = None
    work_tree: Path | None = None
    unresolved = False
    try:
        unresolved = any(name.startswith('GIT_CONFIG_') and value for name, value in os.environ.items())
    except OSError:
        unresolved = True
    for name in ('GIT_DIR', 'GIT_WORK_TREE'):
        try:
            raw = os.environ.get(name)
        except OSError:
            continue
        if not raw:
            continue
        resolved = _literal_path(base, raw)
        if resolved is None:
            unresolved = True
        elif name == 'GIT_DIR':
            git_dir = resolved
        else:
            work_tree = resolved
    return git_dir, work_tree, unresolved


def _push_repository_target(push: PushInvocation) -> Path | None:
    if push.git_directory is not None:
        return push.git_directory.parent if push.git_directory.name == '.git' else push.git_directory
    if push.work_tree is not None:
        return _nearest_repository(push.work_tree)
    return _nearest_repository(push.directory) if push.directory is not None else None


def _push_binding_reason(bound: Path, push: PushInvocation) -> str | None:
    explicit = f'git -C {bound} push <remote> <commit-ish>:<ref>'
    if push.unresolved:
        return (
            'Blocked git push: the repository it writes cannot be read from the command line, '
            'so the delegated grant bound to that repository cannot be checked. Run the push as '
            f'its own command with a literal directory: {explicit}.'
        )
    target = _push_repository_target(push)
    if target is not None and target == bound:
        return None
    found = 'no git repository' if target is None else str(target)
    return (
        f'Blocked git push: it resolves in {found}, while the delegated push grant is bound to '
        f'{bound} (its HEAD and tree). A cd, -C/--git-dir/--work-tree or a working-directory '
        f'parameter must not move the write elsewhere. Push that repository from its own session, '
        f'or pin this one explicitly: {explicit}.'
    )


def _push_unresolved_reason(bound: Path) -> str:
    return (
        'Blocked git push: the command line composes a push with syntax whose working directory '
        'cannot be resolved literally, so the repository it writes cannot be checked against the '
        'grant bound to '
        f'{bound}. Issue the push on its own, pinned to that repository: '
        f'git -C {bound} push <remote> <commit-ish>:<ref>.'
    )


def _mentions_push(text: str) -> bool:
    """Linear gate on the only command lines this guard can ever be about.

    The previous `\\bgit\\b[^\\n]*\\bpush\\b` scan backtracks over the rest of the line for every
    `git` it finds: measured here at 0.017 s for a 10 KB command, 0.278 s for 40 KB and 5.46 s for
    200 KB (the code review reached 62 s on a heavier shape) - a hook timeout on an ordinary long
    command, paid on every Bash call. Two substring tests per line are linear, and the parser below
    still decides, so widening the gate can only cost time on a line that turns out to hold no
    push; it can never grant one.
    """
    lowered = text.lower()
    return any('git' in line and 'push' in line for line in lowered.splitlines())


def push_repository_mismatch(root: Path, command: str, tool_input: Any) -> str | None:
    """Refuse a `git push` that a grant bound to *root* cannot authorize. Fail closed."""
    if not _mentions_push(command):
        return None
    bound = _nearest_repository(root)
    if bound is None:
        # Not a git working tree: no delegated push grant can be valid here, and the
        # existing production-action check already refuses the command.
        return None
    try:
        # Targets below come back from `Path.resolve()`; comparing them against a root that the
        # harness spelled with a symlink or a `.` segment would deny every legitimate push.
        bound = bound.resolve()
    except OSError:
        return _push_unresolved_reason(bound)
    if len(command) > _PUSH_SCAN_LIMIT:
        # The tokenizer is the cost here, not the gate: measured 1.25 s for a 200 KB line and
        # 35 s for a 1 MB line, which is a hook timeout on an ordinary long command. A push that
        # needs this much command line is not something the walk can name a repository in, so it
        # is refused the same way any other unresolvable composition is.
        return _push_unresolved_reason(bound)
    base, base_proven = _push_base_directory(root, tool_input)
    groups = _literal_command_groups(command)
    if groups is None:
        # The text mentions a push and the line is not parseable: refuse before anything runs.
        return _push_unresolved_reason(bound)
    inherited_dir, inherited_tree, inherited_unresolved = _inherited_git_env(base)
    walk = _PushWalk(cwd=base, git_dir=inherited_dir, work_tree=inherited_tree)
    pushes: list[PushInvocation] = []
    walk_proven = _collect_push_invocations(groups, walk, 0, pushes)
    proven = (
        walk_proven
        and base_proven
        and not inherited_unresolved
        and not walk.obstructed
    )
    writes = [push for push in pushes if not push.dry_run]
    if not writes:
        # A --dry-run push performs no write; it is the check that exposes a wrong directory.
        # An obstructed line is different: something on it runs a push the walk cannot see.
        return _push_unresolved_reason(bound) if walk.obstructed else None
    if not proven:
        return _push_unresolved_reason(bound)
    for push in writes:
        reason = (
            _push_binding_reason(bound, push)
            or _push_destructive_reason(bound, push)
            or _push_destination_reason(bound, push)
        )
        if reason:
            return reason
    return None


def _agent_type(tool_input: Any) -> str | None:
    if not isinstance(tool_input, dict):
        return None
    for key in ('agent_type', 'type', 'name', 'role'):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def evaluate_pre_tool(
    root: Path,
    event: dict[str, Any],
    *,
    _skip_substring_control_plane_guard: bool = False,
) -> tuple[bool, str | None]:
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
        mismatch = push_repository_mismatch(root, command, tool_input)
        if mismatch:
            return False, mismatch
        if (
            not _skip_substring_control_plane_guard
            and _is_control_plane_shell_mutation(command, control_plane)
        ):
            return False, 'Blocked control-plane shell mutation; use a structured write with an exact protected-path grant.'
        for pattern in _configured_patterns(config, 'destructive_command_patterns', DESTRUCTIVE_COMMANDS):
            if re.search(pattern, command, flags=re.IGNORECASE):
                return False, f'Blocked destructive command by repository policy: {pattern}'
        action = production_action(command)
        if action:
            if action == 'workflow-dispatch':
                return False, 'GitHub Actions workflow dispatch is forbidden for this repository.'
            from .human_gates import gate_block_reason

            gate_reason = gate_block_reason(root, 'production', action)
            if gate_reason:
                return False, gate_reason
            if not has_valid_approval(root, 'production', action=action):
                return False, f'Production action {action} requires an exact delegated local grant bound to the current SHA.'
        http_resource = _http_write_resource(command)
        if http_resource:
            from .human_gates import gate_block_reason

            gate_reason = gate_block_reason(root, 'external-write', 'external-write', http_resource)
            if gate_reason:
                return False, gate_reason
            if not has_valid_approval(root, 'external-write', action='external-write', resource=http_resource):
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
        from .human_gates import gate_block_reason

        gate_reason = gate_block_reason(root, 'external-write', 'external-write', tool)
        if gate_reason:
            return False, gate_reason
        if not has_valid_approval(root, 'external-write', action='external-write', resource=tool):
            return False, f'MCP side-effect tool {tool} requires an exact delegated external-write grant.'

    return True, None
