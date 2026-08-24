from __future__ import annotations

import fnmatch
import re
import shlex
from pathlib import Path

from ._policy_legacy import (
    _COMMAND_SPLIT,
    _GLOB_META,
    _SHELL_MUTATION_SIGNAL,
    _SHELL_REDIRECTION,
    _UNWRAP_SHELL,
    _WRAPPERS,
)
from .util import safe_relative_path

def _normalize_repo_path(value: str) -> str:
    normalized = value.replace('\\', '/')
    while normalized.startswith('./'):
        normalized = normalized[2:]
    return normalized


def _glob_match(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(_normalize_repo_path(path), _normalize_repo_path(pattern))


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(_glob_match(path, pattern) for pattern in patterns)


def _literal_pattern_prefix(pattern: str) -> str:
    normalized = _normalize_repo_path(pattern)
    match = _GLOB_META.search(normalized)
    return normalized[:match.start()] if match else normalized


def _shell_argv(chunk: str) -> list[str]:
    stripped = chunk.split('#', 1)[0].strip()
    try:
        tokens = shlex.split(stripped)
    except ValueError:
        tokens = stripped.split()
    while tokens and re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', tokens[0]):
        tokens = tokens[1:]
    while tokens and tokens[0].lower() in _WRAPPERS:
        tokens = tokens[1:]
    return tokens


def _option_values(
    argv: list[str],
    short: str,
    long: str,
    *,
    grouped_prefixes: set[str] | None = None,
) -> list[str]:
    values: list[str] = []
    index = 1
    short_name = short.removeprefix('-')
    while index < len(argv):
        token = argv[index]
        if token in {short, long}:
            if index + 1 < len(argv):
                values.append(argv[index + 1])
                index += 2
                continue
        if token.startswith(long + '='):
            values.append(token.split('=', 1)[1])
        elif token.startswith(short) and token != short and not token.startswith('--'):
            values.append(token[len(short):])
        elif grouped_prefixes and token.startswith('-') and not token.startswith('--'):
            cluster = token[1:]
            prefix = cluster[:-len(short_name)] if short_name and cluster.endswith(short_name) else ''
            if prefix and all(char in grouped_prefixes for char in prefix) and index + 1 < len(argv):
                values.append(argv[index + 1])
                index += 2
                continue
        index += 1
    return values


def _has_option(argv: list[str], names: set[str]) -> bool:
    for token in argv[1:]:
        for name in names:
            if token == name:
                return True
            if name.startswith('--') and token.startswith(name + '='):
                return True
            if name.startswith('-') and not name.startswith('--') and token.startswith(name) and token != '-':
                return True
    return False


def _operands(argv: list[str], value_options: set[str] | None = None) -> list[str]:
    result: list[str] = []
    options_with_values = value_options or set()
    after_separator = False
    index = 1
    while index < len(argv):
        token = argv[index]
        if token == '--':
            after_separator = True
            index += 1
            continue
        if not after_separator and token.startswith('-'):
            if token in options_with_values and index + 1 < len(argv):
                index += 2
                continue
            if any(token.startswith(option + '=') for option in options_with_values if option.startswith('--')):
                index += 1
                continue
            index += 1
            continue
        result.append(token)
        index += 1
    return result


def _command_name(argv: list[str]) -> str:
    if not argv:
        return ''
    command = argv[0].replace('\\', '/').rsplit('/', 1)[-1].lower()
    return command[:-4] if command.endswith('.exe') else command


def _directory_target(root: Path, raw: str, *, explicit: bool) -> bool:
    if explicit or raw.endswith(('/', '\\')):
        return True
    if any(marker in raw for marker in ('$(', '${', '$', '`', '*', '?', '[')):
        return False
    path = Path(raw)
    absolute = path if path.is_absolute() else root / path
    try:
        return absolute.resolve().is_dir()
    except OSError:
        return False


def _joined_target(directory: str, source: str) -> str | None:
    normalized_source = source.replace('\\', '/').rstrip('/')
    basename = normalized_source.rsplit('/', 1)[-1]
    if not basename or basename in {'.', '..'} or any(marker in basename for marker in ('$', '`', '*', '?', '[')):
        return None
    normalized_directory = directory.replace('\\', '/').rstrip('/')
    if normalized_directory in {'', '.'}:
        return basename
    return f'{normalized_directory}/{basename}'


def _copy_like_targets(root: Path, command: str, argv: list[str]) -> list[str]:
    value_options = {'-t', '--target-directory', '-S', '--suffix'}
    if command == 'install':
        value_options.update({'-m', '--mode', '-o', '--owner', '-g', '--group'})
    configured = _option_values(argv, '-t', '--target-directory')
    operands = _operands(argv, value_options)
    if configured:
        destinations = configured
        sources = operands
        explicit_directory = True
    elif operands:
        destinations = operands[-1:]
        sources = operands[:-1]
        explicit_directory = False
    else:
        return []

    targets = list(destinations)
    for destination in destinations:
        if not _directory_target(root, destination, explicit=explicit_directory):
            continue
        for source in sources:
            joined = _joined_target(destination, source)
            if joined:
                targets.append(joined)
    return list(dict.fromkeys(targets))


def _script_file_targets(
    argv: list[str],
    *,
    script_options: set[str],
    value_options: set[str],
) -> list[str]:
    operands = _operands(argv, value_options)
    if _has_option(argv, script_options):
        return operands
    return operands[1:] if len(operands) > 1 else []


def _argv_mutation_targets(root: Path, argv: list[str]) -> list[str] | None:
    command = _command_name(argv)
    if not command:
        return None
    if command == 'curl':
        targets = _option_values(
            argv,
            '-o',
            '--output',
            grouped_prefixes=set('sSfLkIiVv'),
        )
        return targets if targets else None
    if command == 'wget':
        targets = _option_values(
            argv,
            '-O',
            '--output-document',
            grouped_prefixes=set('qNc'),
        )
        return targets if targets else None
    if command == 'dd':
        targets = [token.split('=', 1)[1] for token in argv[1:] if token.startswith('of=')]
        return targets if targets else None
    if command == 'tee':
        return _operands(argv)
    if command == 'touch':
        return _operands(argv, {'-d', '--date', '-r', '--reference', '-t', '--time'})
    if command == 'mkdir':
        return _operands(argv, {'-m', '--mode', '-Z', '--context'})
    if command in {'rmdir', 'rm'}:
        return _operands(argv)
    if command == 'truncate':
        return _operands(argv, {'-s', '--size', '-r', '--reference'})
    if command in {'chmod', 'chown', 'chgrp'}:
        operands = _operands(argv, {'--reference', '--from'})
        if _has_option(argv, {'--reference'}):
            return operands
        return operands[1:] if len(operands) > 1 else []
    if command in {'cp', 'mv', 'ln', 'install'}:
        return _copy_like_targets(root, command, argv)
    if command == 'rsync':
        operands = _operands(argv)
        return operands[-1:] if operands else []
    if command == 'sed' and any(token == '-i' or token.startswith('-i') for token in argv[1:]):
        return _script_file_targets(
            argv,
            script_options={'-e', '--expression', '-f', '--file'},
            value_options={'-e', '--expression', '-f', '--file'},
        )
    if command == 'perl' and any(token.startswith('-') and 'i' in token[1:] for token in argv[1:]):
        return _script_file_targets(
            argv,
            script_options={'-e', '-E'},
            value_options={'-e', '-E', '-M', '-m'},
        )
    if command == 'ruff' and '--fix' in argv:
        operands = _operands(argv)
        if operands and operands[0] in {'check', 'format'}:
            operands = operands[1:]
        return operands
    return None


def _shell_mutation_targets(root: Path, command: str) -> tuple[list[str], bool, bool]:
    targets: list[str] = []
    mutation = False
    unresolved = False
    for chunk in _command_chunks(command):
        inner = _unwrap_shell(chunk)
        for piece in _command_chunks(inner):
            redirections = [
                match.group('target').strip('"\'')
                for match in _SHELL_REDIRECTION.finditer(piece)
            ]
            if redirections:
                mutation = True
                targets.extend(redirections)
            signal = _SHELL_MUTATION_SIGNAL.search(piece) is not None
            argv_targets = _argv_mutation_targets(root, _shell_argv(piece))
            if argv_targets is not None:
                mutation = True
                targets.extend(argv_targets)
            elif signal:
                mutation = True
                unresolved = True
    return list(dict.fromkeys(targets)), mutation, unresolved


def _control_plane_target(path: str, patterns: list[str]) -> bool:
    if _matches_any(path, patterns):
        return True
    normalized = _normalize_repo_path(path).rstrip('/')
    for pattern in patterns:
        candidate = _normalize_repo_path(pattern)
        if candidate.endswith('/**') and normalized == candidate[:-3].rstrip('/'):
            return True
    return False


def _dynamic_target_mentions_control_plane(raw: str, patterns: list[str]) -> bool:
    normalized = raw.replace('\\', '/')
    if not normalized.startswith(('/', '$', '`')) and _control_plane_target(normalized, patterns):
        return True
    expansion = re.compile(
        r'(?:\$[A-Za-z_][A-Za-z0-9_]*|\$\{[^}]+\}|\$\([^)]*\)|`[^`]*`)/(?P<suffix>[^\s]+)'
    )
    for match in expansion.finditer(normalized):
        suffix = match.group('suffix').strip('"\'')
        if _control_plane_target(suffix, patterns):
            return True
    return False


def _opaque_control_plane_reference(root: Path, command: str, patterns: list[str]) -> bool:
    normalized = command.replace('\\', '/')
    absolute_root = root.resolve().as_posix().rstrip('/')
    for pattern in patterns:
        prefix = _literal_pattern_prefix(pattern)
        if not prefix:
            continue
        exact_pattern = _GLOB_META.search(_normalize_repo_path(pattern)) is None
        suffix = r'(?=$|[\s\'"),;:&|])' if exact_pattern else ''
        relative = re.compile(
            r'(?:^|[\s\'"=(:,>])(?:\./)?' + re.escape(prefix) + suffix,
            re.IGNORECASE,
        )
        absolute = re.compile(
            re.escape(absolute_root + '/' + prefix) + suffix,
            re.IGNORECASE,
        )
        if relative.search(normalized) or absolute.search(normalized):
            return True
    return False


def _control_plane_shell_mutation(
    root: Path,
    command: str,
    patterns: list[str],
) -> tuple[list[str], bool]:
    raw_targets, mutation, unresolved = _shell_mutation_targets(root, command)
    protected_targets: list[str] = []
    dynamic_protected = False
    for raw in raw_targets:
        if not raw:
            continue
        if any(marker in raw for marker in ('$(', '${', '$', '`', '*', '?', '[')):
            dynamic_protected = dynamic_protected or _dynamic_target_mentions_control_plane(raw, patterns)
            continue
        rel = safe_relative_path(root, raw)
        if rel is not None and _control_plane_target(rel, patterns):
            protected_targets.append(rel)
    if protected_targets:
        return list(dict.fromkeys(protected_targets)), False
    if dynamic_protected:
        return [], True
    return [], mutation and unresolved and _opaque_control_plane_reference(root, command, patterns)



def _command_chunks(command: str) -> list[str]:
    return [part for part in _COMMAND_SPLIT.split(command) if part.strip()]


def _leading_argv(chunk: str) -> list[str]:
    return [token.lower() for token in _shell_argv(chunk)]


def _unwrap_shell(chunk: str) -> str:
    match = _UNWRAP_SHELL.match(chunk)
    if not match:
        return chunk
    rest = match.group('rest')
    if len(rest) >= 2 and rest[0] == rest[-1] and rest[0] in {'"', "'"}:
        return rest[1:-1]
    return rest




control_plane_shell_mutation = _control_plane_shell_mutation
