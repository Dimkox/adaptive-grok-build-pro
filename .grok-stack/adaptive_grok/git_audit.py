"""Read-only audit of the local Git delivery surface (issue #54).

A working clone of this repository registers 190+ linked worktrees and 200+ local branches.
Some worktrees carry hundreds of uncommitted files, dozens of branches point their configured
upstream at a protected base branch (`git push` from such a branch targets `main` the moment
`push.default=upstream` is set, and `git pull` silently merges `main` into the feature branch),
stashes are labelled only by a branch that may no longer exist, and the branch registry keeps
entries for worktree directories that were deleted. None of that was visible on any health
screen before it cost work.

This module only reads. It never pushes, prunes, re-upstreams, stashes, drops or deletes; the
remediation it returns is a list of commands a human reviews and runs, mirroring how
``adaptive_grok.deploy`` prints the publish commands instead of executing them.

Two rules bound every number printed here, because a delivery screen that reads clean when it
did not look is worse than no screen at all:

1. A Git read that fails (nonzero exit, timeout, or the aggregate wall-clock budget) is never
   folded into an empty collection. It is recorded as a degraded read, and every row it touches
   becomes ``info`` naming the command and the exit code.
2. A check that was skipped is never used as evidence of the positive. ``unpushed_state`` must be
   ``checked`` before anything is presented as delivered, so a repository with no remote cannot
   be advised to point its branch at ``origin/main``.
"""

from __future__ import annotations

import math
import os
import re
import shlex
import time
from pathlib import Path
from typing import Any

from .util import command_exists, run

PROTECTED_BASE_BRANCHES = ('main', 'master')
MAX_WORKTREE_SCANS = 250
MAX_HISTORY_COMMITS = 100_000
DETAIL_LIMIT = 8
GIT_TIMEOUT_SECONDS = 30
#: Whole-audit deadline. 250 worktree scans at 30 s each would be ~125 min, which is longer than
#: the test harness that imports this module; the deadline is what makes the per-command timeout
#: an upper bound instead of a multiplier.
AUDIT_BUDGET_SECONDS = 20.0
#: Synthetic exit code: ``util.run`` reports 124 for a command that outran its timeout.
TIMEOUT_EXIT_CODE = 124
#: How many next steps the screen lists before pointing at the JSON instead.
MAX_REMEDIATIONS = 14

READ_ONLY_NOTICE = (
    'read-only audit: this tool never runs anything - it does not push, prune, re-upstream, '
    'stash, drop or delete. Each remediation line is a command for a human to review and run, '
    'and a direct push to a protected or shared branch stays prohibited'
)

DELIVERY_CAVEAT = (
    'every pull request in this repository is squash-merged, so a fully delivered branch can '
    'still look unpushed; confirm the pull-request state before treating a branch as lost work'
)

_BRANCH_KEY = re.compile(r'^branch\.(?P<branch>.*)\.(?P<field>remote|merge)$')
_STASH_LABEL = re.compile(r'^(?:WIP on|On)\s+(?P<branch>.+?):\s*(?P<subject>.*)$')

# Git gives these ambient variables precedence over repository discovery, config, refs, objects or
# the index selected by ``cwd``. The audit is explicitly about ``root``; inheriting any of them
# lets the caller silently redirect a read to different state while the report still says checked.
_GIT_STATE_ENV = {
    'GIT_ALTERNATE_OBJECT_DIRECTORIES',
    'GIT_CEILING_DIRECTORIES',
    'GIT_COMMON_DIR',
    'GIT_CONFIG',
    'GIT_CONFIG_COUNT',
    'GIT_CONFIG_GLOBAL',
    'GIT_CONFIG_NOSYSTEM',
    'GIT_CONFIG_PARAMETERS',
    'GIT_CONFIG_SYSTEM',
    'GIT_DIR',
    'GIT_DISCOVERY_ACROSS_FILESYSTEM',
    'GIT_GRAFT_FILE',
    'GIT_INDEX_FILE',
    'GIT_IMPLICIT_WORK_TREE',
    'GIT_INTERNAL_SUPER_PREFIX',
    'GIT_NAMESPACE',
    'GIT_NO_REPLACE_OBJECTS',
    'GIT_OBJECT_DIRECTORY',
    'GIT_OBJECT_DIRECTORY_RELATIVE',
    'GIT_PREFIX',
    'GIT_QUARANTINE_PATH',
    'GIT_REPLACE_REF_BASE',
    'GIT_SHALLOW_FILE',
    'GIT_SUPER_PREFIX',
    'GIT_WORK_TREE',
}


def _git_state_env() -> tuple[str, ...]:
    """Every ambient key that can select or reinterpret repository state.

    Git's environment surface is open-ended across versions (including numbered config keys and
    internal super-prefix/object-directory controls), so remove every inherited ``GIT_*`` key and
    then let :func:`_git` add back only ``GIT_OPTIONAL_LOCKS=0``.
    """
    dynamic = {
        key
        for key in os.environ
        if key.startswith('GIT_')
    }
    return tuple(sorted(_GIT_STATE_ENV | dynamic))


class _Budget:
    """Wall-clock bound plus the degraded-read log for one audit pass.

    Both halves exist for the same reason: a limited audit must never read as a clean one. The
    deadline caps how long a whole pass can take, and ``degraded`` carries what could not be
    observed inside that time so each caller can say so instead of reporting zero.
    """

    def __init__(self, seconds: float | None = AUDIT_BUDGET_SECONDS) -> None:
        self.seconds = seconds
        # `is not None`, not truthiness: a 0 budget is the test seam that proves an expired audit
        # still reports itself as limited, and `None` is the only value that means "unbounded".
        self.deadline = time.monotonic() + seconds if seconds is not None else None
        self.degraded: list[dict[str, Any]] = []
        self.refused = 0

    def expired(self) -> bool:
        return self.deadline is not None and time.monotonic() >= self.deadline

    def timeout(self) -> int:
        if self.deadline is None:
            return GIT_TIMEOUT_SECONDS
        return max(1, min(GIT_TIMEOUT_SECONDS, math.ceil(self.deadline - time.monotonic())))

    def record(self, section: str, command: str, code: int) -> None:
        """Note that one read could not be trusted, naming it and how it failed."""
        self.degraded.append(
            {
                'section': section,
                'command': command,
                'code': code,
                'cause': _exit_cause(code),
            }
        )

    def refuse(self, section: str, args: tuple[str, ...] | list[str]) -> None:
        """Record a read that the shared deadline prevented from starting."""
        self.refused += 1
        self.record(section, _command_text(args), TIMEOUT_EXIT_CODE)

    def causes(self, section: str) -> list[str]:
        return [
            f'{item["command"]} {item["cause"]}'
            for item in self.degraded
            if item['section'] == section
        ]

    def limited(self, section: str) -> bool:
        return bool(self.causes(section))


def _exit_cause(code: int) -> str:
    if code == TIMEOUT_EXIT_CODE:
        return 'timed out'
    return f'exited {code}'


def _git(
    root: Path,
    *args: str,
    budget: _Budget | None = None,
    section: str | None = None,
) -> tuple[int, str]:
    """Run one read-only Git command without letting it refresh the index.

    The budget shortens the command's timeout so no single read can outrun the audit deadline and
    refuses every read, including repository detection, after that one deadline expires. A nonzero
    exit is returned, not swallowed: the caller decides whether it means empty or means unknown,
    and when it means unknown it must call ``budget.record`` (pass ``section`` here to have the
    failure logged automatically).
    """
    if not command_exists('git'):
        return 127, ''
    if not root.is_dir():
        return 1, ''
    if budget is not None and budget.expired():
        budget.refuse(section or 'git', args)
        return TIMEOUT_EXIT_CODE, ''
    proc = run(
        ['git', *args],
        cwd=root,
        timeout=budget.timeout() if budget else GIT_TIMEOUT_SECONDS,
        env={'GIT_OPTIONAL_LOCKS': '0'},
        env_remove=_git_state_env(),
    )
    if proc.returncode and section and budget is not None:
        budget.record(section, _command_text(args), proc.returncode)
    return proc.returncode, proc.stdout


def _command_text(args: tuple[str, ...] | list[str]) -> str:
    """The identity of one Git read, short enough to print inside a health row.

    Format specifiers carry the payload, not the name of the read, so they are dropped; the row
    must tell an operator which command failed, not echo a `--format=` string back at them.
    """
    words = [str(arg) for arg in args if not str(arg).startswith('--format')]
    return 'git ' + ' '.join(words[:3])


def _lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if line.strip()]


def _unavailable_reason(root: Path, budget: _Budget | None = None) -> str | None:
    if not command_exists('git'):
        return 'git is not installed'
    if not root.is_dir():
        return f'{root} is not a directory'
    code, out = _git(
        root,
        'rev-parse',
        '--is-inside-work-tree',
        budget=budget,
        section='repository',
    )
    if code == TIMEOUT_EXIT_CODE:
        return f'audit budget of {_budget_text(budget)} exhausted during repository detection'
    if code or out.strip() != 'true':
        return 'not a git repository'
    return None


def _worktree_entries(
    root: Path,
    budget: _Budget | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Parse `git worktree list --porcelain`. The exit code travels with the entries."""
    code, output = _git(
        root, 'worktree', 'list', '--porcelain', budget=budget, section='worktrees'
    )
    if code:
        return [], code
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in output.splitlines():
        if line.startswith('worktree '):
            if current is not None:
                entries.append(current)
            current = {
                'path': line[len('worktree '):].strip(),
                'branch': None,
                'head': None,
                'detached': False,
                'prunable': None,
            }
            continue
        if current is None:
            continue
        key, _, value = line.partition(' ')
        value = value.strip()
        if key == 'HEAD':
            current['head'] = value
        elif key == 'branch':
            current['branch'] = value[len('refs/heads/'):] if value.startswith('refs/heads/') else value
        elif key == 'detached':
            current['detached'] = True
        elif key == 'prunable':
            current['prunable'] = value or 'prunable'
    if current is not None:
        entries.append(current)
    return entries, code


def _audit_worktrees(
    root: Path,
    entries: list[dict[str, Any]],
    limit: int,
    budget: _Budget | None = None,
    registry_code: int = 0,
) -> dict[str, Any]:
    dirty: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    unreadable: list[str] = []
    scanned = 0
    over_limit = 0
    out_of_time = 0
    for entry in entries:
        path = entry['path']
        if not path or not Path(path).is_dir():
            missing.append(
                {
                    'path': path,
                    'branch': entry['branch'],
                    'reason': entry['prunable'] or 'registered worktree directory is absent from disk',
                }
            )
            continue
        if scanned >= limit:
            over_limit += 1
            continue
        if budget is not None and budget.expired():
            # Not a broken worktree: the audit ran out of time on it. Counted, never called clean.
            budget.refused += 1
            out_of_time += 1
            continue
        code, output = _git(
            Path(path), 'status', '--porcelain=v1', '--untracked-files=all',
            '--ignore-submodules=none',
            budget=budget,
        )
        scanned += 1
        if code:
            unreadable.append(path)
            continue
        changed = len(_lines(output))
        if changed:
            dirty.append({'path': path, 'branch': entry['branch'], 'changed_files': changed})
    dirty.sort(key=lambda item: (-item['changed_files'], item['path']))
    registry_logged = bool(budget.limited('worktrees')) if budget else False
    causes: list[str] = []
    if over_limit:
        causes.append(f'scan limit of {limit} worktrees reached, {over_limit} not scanned')
    if out_of_time:
        causes.append(
            f'audit budget of {_budget_text(budget)} exhausted, {out_of_time} not scanned'
        )
    if unreadable:
        causes.append(f'git status failed in {len(unreadable)} registered worktree path(s)')
    if registry_code and not registry_logged:
        causes.append(
            f'git worktree list --porcelain {_exit_cause(registry_code)}, '
            'the registry could not be read'
        )
    causes.extend(budget.causes('worktrees') if budget else [])
    registry_known = registry_code == 0
    dirty_state = (
        'checked'
        if registry_known and not (over_limit or out_of_time or unreadable)
        else 'unknown'
    )
    return {
        'registry_state': 'checked' if registry_known else 'unknown',
        'registered': len(entries) if registry_known else None,
        'scanned': scanned,
        'truncated': over_limit > 0,
        'incomplete': bool(causes),
        'incomplete_causes': causes,
        'over_limit': over_limit,
        'out_of_time': out_of_time,
        'unreadable': unreadable[:DETAIL_LIMIT],
        'unreadable_count': len(unreadable) if registry_known else None,
        'detached': sum(1 for entry in entries if entry['detached']) if registry_known else None,
        'prunable': sum(1 for entry in entries if entry['prunable']) if registry_known else None,
        'dirty': dirty,
        'dirty_state': dirty_state,
        'missing': missing[:DETAIL_LIMIT],
        'missing_count': len(missing) if registry_known else None,
    }


def _budget_text(budget: _Budget | None) -> str:
    if budget is None or budget.seconds is None:
        return 'unbounded'
    return f'{budget.seconds:g}s'


def _configured_upstreams(
    root: Path,
    budget: _Budget | None = None,
) -> dict[str, dict[str, str]] | None:
    """Read `branch.<name>.remote`/`merge` straight from repository config.

    `for-each-ref %(upstream:short)` goes blank once the remote-tracking ref is pruned, which is
    exactly the orphaned state this audit has to surface, so config is the authoritative source.

    `--local` is load-bearing, not an optimisation: without it a `branch.*` entry in
    `~/.gitconfig` or `GIT_CONFIG_GLOBAL` on the scanning host would be reported as this
    repository's upstream state, inventing or hiding a protected-base hazard.
    """
    args = ('config', '--get-regexp', '--local', r'^branch\.')
    if budget is not None and budget.expired():
        budget.refuse('branches', args)
        return None
    code, output = _git(root, *args, budget=budget)
    if code not in (0, 1) and budget is not None:
        label = _command_text(('config', '--get-regexp', '--local', r'^branch\.'))
        budget.record('branches', label, code)
        return None
    upstreams: dict[str, dict[str, str]] = {}
    for line in output.splitlines():
        key, _, value = line.partition(' ')
        match = _BRANCH_KEY.match(key)
        if not match:
            continue
        upstreams.setdefault(match.group('branch'), {})[match.group('field')] = value.strip()
    return upstreams


def _upstream_parts(remote: str, merge: str) -> dict[str, str] | None:
    if not merge:
        return None
    short = merge[len('refs/heads/'):] if merge.startswith('refs/heads/') else merge
    if not short:
        return None
    display = short if remote in ('', '.') else f'{remote}/{short}'
    return {'branch': short, 'upstream': display, 'remote': remote}


def _audit_branches(
    root: Path,
    entries: list[dict[str, Any]],
    upstreams: dict[str, dict[str, str] | None] | None,
    budget: _Budget | None = None,
    *,
    worktree_registry_ok: bool = True,
) -> dict[str, Any]:
    code, remote_output = _git(
        root,
        'for-each-ref',
        'refs/remotes',
        '--format=%(refname:short)%09%(objectname)',
        budget=budget,
        section='branches',
    )
    remote_refs_ok = code == 0
    remote_tips: dict[str, str] = {}
    for line in _lines(remote_output) if remote_refs_ok else []:
        ref, _, sha = line.partition('\t')
        if ref and sha.strip():
            remote_tips[ref] = sha.strip()
    remote_refs = set(remote_tips)
    local_tips: dict[str, str] = {}
    code, tips_output = _git(
        root,
        'for-each-ref',
        'refs/heads',
        '--format=%(refname:short)%09%(objectname)',
        budget=budget,
        section='branches',
    )
    local_refs_ok = code == 0
    for line in _lines(tips_output) if code == 0 else []:
        branch, _, sha = line.partition('\t')
        if branch and sha.strip():
            local_tips[branch] = sha.strip()
    code, remote_names = _git(root, 'remote', budget=budget, section='branches')
    remotes = _lines(remote_names) if code == 0 else None
    known = remote_refs | set(local_tips)
    protected: list[dict[str, str]] = []
    gone: list[dict[str, str]] = []
    no_upstream: list[str] = []
    if upstreams is not None:
        for branch in sorted(local_tips):
            resolved = upstreams.get(branch)
            if resolved is None:
                no_upstream.append(branch)
                continue
            short = resolved['branch']
            display = resolved['upstream']
            if short in PROTECTED_BASE_BRANCHES and branch not in PROTECTED_BASE_BRANCHES:
                protected.append(
                    {'branch': branch, 'upstream': display, 'remote': resolved['remote']}
                )
            # Only call an upstream ref gone when the remote registry was actually readable; an
            # unreadable `for-each-ref` would otherwise report every configured upstream as missing.
            if remote_refs_ok and display not in known:
                gone.append(
                    {
                        'branch': branch,
                        'upstream': display,
                        'remote': resolved['remote'],
                        'state': 'gone',
                    }
                )
    proven_upstreams: list[dict[str, str]] = []
    if local_refs_ok and remote_refs_ok and remotes is not None and upstreams is not None:
        for branch in no_upstream:
            for remote in remotes:
                candidate = f'{remote}/{branch}'
                if remote_tips.get(candidate) == local_tips[branch]:
                    proven_upstreams.append({'branch': branch, 'upstream': candidate})
                    break
    unpushed, unpushed_detached, unpushed_state, skip_reason = _unpushed_tips(
        root,
        local_tips,
        remote_refs,
        entries,
        budget,
        local_refs_ok=local_refs_ok,
        remote_refs_ok=remote_refs_ok,
        worktree_registry_ok=worktree_registry_ok,
    )
    protected_state = 'checked' if local_refs_ok and upstreams is not None else 'unknown'
    gone_state = (
        'checked'
        if local_refs_ok and remote_refs_ok and upstreams is not None
        else 'unknown'
    )
    return {
        'local': len(local_tips) if local_refs_ok else None,
        'remotes': remotes,
        'remote_refs': len(remote_refs) if remote_refs_ok else None,
        'upstream_state': 'checked' if upstreams is not None else 'unknown',
        'upstream_protected_state': protected_state,
        'upstream_gone_state': gone_state,
        'no_upstream_state': protected_state,
        'upstream_protected': protected,
        'upstream_gone': gone,
        'no_upstream': no_upstream,
        'proven_upstreams': proven_upstreams,
        'unpushed_tips': unpushed,
        'unpushed_detached': unpushed_detached,
        'unpushed_state': unpushed_state,
        'unpushed_tips_state': 'checked' if unpushed_state == 'checked' else 'unknown',
        'unpushed_detached_state': 'checked' if unpushed_state == 'checked' else 'unknown',
        'unpushed_skip_reason': skip_reason,
        'delivery_caveat': DELIVERY_CAVEAT,
    }


def _detached_heads(entries: list[dict[str, Any]], branch_tips: set[str]) -> dict[str, dict[str, Any]]:
    """Worktree HEADs that no branch names, keyed by commit.

    `git worktree list --porcelain` already reports each worktree's HEAD, so a detached checkout
    carries a commit that `refs/heads` never mentions. Deduplicated by commit (several worktrees
    can sit on the same one) and skipping commits a branch already stands on, because those are
    reported under their branch name.
    """
    heads: dict[str, dict[str, Any]] = {}
    for entry in entries:
        sha = entry.get('head')
        if not sha or sha in branch_tips:
            continue
        record = heads.setdefault(sha, {'head': sha, 'paths': [], 'detached': True})
        record['paths'].append(entry['path'])
        record['detached'] = record['detached'] and bool(entry.get('detached'))
    return heads


def _unpushed_tips(
    root: Path,
    local_tips: dict[str, str],
    remote_refs: set[str],
    entries: list[dict[str, Any]],
    budget: _Budget | None = None,
    *,
    local_refs_ok: bool = True,
    remote_refs_ok: bool = True,
    worktree_registry_ok: bool = True,
) -> tuple[list[str], list[dict[str, Any]], str, str | None]:
    """Local work no remote can recover: branch tips, plus the detached worktree HEADs.

    The detached half matters as much as the branch half. A clean detached worktree holds its
    commit in HEAD only: no branch, no remote. Comparing `refs/heads` alone calls it safe.
    """
    detached = _detached_heads(entries, set(local_tips.values()))
    if not local_refs_ok:
        return [], [], 'skipped', 'local branch tips could not be enumerated'
    if not remote_refs_ok:
        return [], [], 'skipped', 'remote-tracking refs could not be enumerated'
    if not worktree_registry_ok:
        return [], [], 'skipped', (
            'worktree registry could not be enumerated, so detached worktree HEADs and the '
            'combined unpushed result are unknown'
        )
    if not remote_refs:
        return [], [], 'skipped', (
            'no remote-tracking branches exist, so nothing can be compared; unpushed branch tips '
            'and detached worktree HEADs are unknown, not absent'
        )
    code, reachable = _git(
        root,
        'rev-list',
        '--remotes',
        f'--max-count={MAX_HISTORY_COMMITS + 1}',
        budget=budget,
        section='branches',
    )
    if code:
        return [], [], 'skipped', 'remote history could not be enumerated'
    reachable_lines = _lines(reachable)
    if len(reachable_lines) > MAX_HISTORY_COMMITS:
        return [], [], 'skipped', f'remote history exceeds the bounded limit of {MAX_HISTORY_COMMITS} commits'
    on_remote = set(reachable_lines)
    unpushed = [branch for branch, sha in sorted(local_tips.items()) if sha not in on_remote]
    unpushed_detached = [
        record for sha, record in sorted(detached.items()) if sha not in on_remote
    ]
    return unpushed, unpushed_detached, 'checked', None


def _audit_stashes(root: Path, budget: _Budget | None = None) -> dict[str, Any]:
    code, output = _git(
        root, 'stash', 'list', '--format=%gd%x09%gs', budget=budget, section='stashes'
    )
    if code:
        return {
            'count': None,
            'entries': [],
            'unreadable': True,
            'unreadable_cause': _exit_cause(code),
        }
    entries: list[dict[str, Any]] = []
    for line in _lines(output):
        selector, _, subject = line.partition('\t')
        match = _STASH_LABEL.match(subject.strip())
        entries.append(
            {
                'selector': selector.strip(),
                'branch': match.group('branch') if match else '',
                'subject': match.group('subject') if match else subject.strip(),
            }
        )
    return {
        'count': len(entries),
        'entries': entries[:DETAIL_LIMIT],
        'unreadable': False,
        'unreadable_cause': None,
    }


def _repository_slug(url: str) -> str | None:
    """Extract `owner/repo` from an HTTP(S) or SSH remote URL.

    Local-path remotes (a bare repo in a temp directory, a sibling clone) have no owner/repo
    form, so they return `None` and the printed command keeps the explicit placeholder.

    Two colon forms are distinguished: in a URL with a scheme, `host:7999` is a port and must be
    dropped (`ssh://git@host:7999/owner/repo.git` is `owner/repo`); in the scheme-less scp form
    `git@host:owner/repo.git`, the colon separates the host from the path and what follows it is
    the path.
    """
    if not url or url.startswith(('/', '.', '~')) or ('://' not in url and ':' not in url):
        return None
    scheme, sep, rest = url.partition('://')
    if scheme == 'file':
        # A `file://` remote is a local path in URL clothing; it has no owner/repo either.
        return None
    # The scp form (`git@host:owner/repo.git`) carries no scheme, so the URL is all location.
    location = rest if sep else url
    host_part, slash, tail = location.partition('/')
    if not slash or not tail:
        return None
    if '@' in host_part:
        host_part = host_part.rsplit('@', 1)[-1]
    if ':' in host_part:
        host_part, _, port = host_part.rpartition(':')
        if not (sep and port.isdigit()):
            # scp-style `git@host:owner/repo.git`: the colon carries the path, not a port.
            tail = f'{port}/{tail}'
    parts = [part for part in tail.split('/') if part]
    if len(parts) < 2:
        return None
    name = parts[1][: -len('.git')] if parts[1].endswith('.git') else parts[1]
    return f'{parts[0]}/{name}' if name else None


def _remote_slug(
    root: Path,
    remotes: list[str] | None,
    budget: _Budget | None = None,
) -> str | None:
    if remotes is None:
        return None
    names = (['origin'] if 'origin' in remotes else []) + [
        name for name in remotes if name != 'origin'
    ]
    for name in names:
        args = ('remote', 'get-url', name)
        if budget is not None and budget.expired():
            budget.refuse('branches', args)
            return None
        code, output = _git(root, *args, budget=budget, section='branches')
        if code:
            continue
        slug = _repository_slug(output.strip())
        if slug:
            return slug
    return None


def human_commands(report: dict[str, Any]) -> list[str]:
    """Commands a human authorizes and runs. This function never runs them.

    A recommended command is an outcome this screen produces, so it carries the same hazard test
    as anything else it prints: nothing may claim a branch is delivered on the strength of a check
    that did not run. `unpushed_state == 'checked'` is the gate for every suggestion that reads
    "this one is already safe", because an empty unpushed list from a skipped check is the absence
    of evidence, not evidence of delivery.
    """
    branches = report['branches']
    worktrees = report['worktrees']
    remotes = branches['remotes'] or []
    slug = report['repository']['slug'] or '<owner>/<repo>'
    tips_checked = branches['unpushed_state'] == 'checked'
    quote = shlex.quote
    commands: list[str] = []
    # `[]` is the clean close. A skipped reachability check must not take it when nothing
    # else is hazardous: empty commands are what the screen reads as delivery established.
    if tips_checked and not any(
        (
            branches['upstream_protected'],
            branches['upstream_gone'],
            branches['no_upstream'],
            branches['unpushed_tips'],
            branches['unpushed_detached'],
            worktrees['dirty'],
            worktrees['missing'],
            worktrees['incomplete'],
            report['stashes']['count'],
            report['stashes']['unreadable'],
            report['degraded'],
        )
    ):
        return commands
    if not tips_checked:
        commands.append(
            f'# delivery is NOT established here: {branches["unpushed_skip_reason"] or "the tip check did not run"}'
        )
        commands.append('# confirm the remote state (git remote -v) before setting any upstream')
    if branches['unpushed_detached_state'] == 'unknown':
        commands.append(
            '# detached rescue advice unavailable: '
            f'{branches["unpushed_skip_reason"] or "detached-tip dependencies were not read"}'
        )
    if branches['remotes']:
        commands.append('git fetch --all --prune  # refreshes remote-tracking refs only')
    for entry in branches['upstream_protected'][:3]:
        commands.append(
            f'git branch --unset-upstream {quote(entry["branch"])}'
            f'  # upstream {entry["upstream"]} is a protected base'
        )
        remote = entry.get('remote')
        if remote and remote not in {'.'} and remote in remotes:
            commands.append(
                f'git push -u {quote(remote)} {quote(entry["branch"])}'
                '  # human-authorized push to its own ref, never to main'
            )
    if len(branches['upstream_protected']) > 3:
        commands.append(f'# +{len(branches["upstream_protected"]) - 3} more protected-upstream branches')
    for entry in branches['upstream_gone'][:3]:
        commands.append(
            f'git branch --unset-upstream {quote(entry["branch"])}'
            f'  # upstream {entry["upstream"]} is gone'
        )
    if tips_checked:
        for entry in branches['proven_upstreams'][:2]:
            upstream_option = quote('--set-upstream-to=' + entry['upstream'])
            commands.append(
                f'git branch {upstream_option}'
                f' {quote(entry["branch"])}'
                '  # exact remote ref exists at this branch tip; never a protected base'
            )
    elif branches['no_upstream']:
        commands.append(
            f'# {len(branches["no_upstream"])} branch(es) have no upstream and the tip check was skipped:'
            ' do not set one to a base branch, re-run once the tip check can compare'
        )
    if tips_checked and branches['unpushed_tips']:
        sample = branches['unpushed_tips'][0]
        commands.append(
            f'gh pr list --repo {quote(slug)} --state all --head {quote(sample)}'
            ' --json number,state,mergedAt'
            '  # was it delivered by squash merge?'
        )
        commands.append(
            f'git log --oneline --decorate --max-count=5 {quote(sample)} --'
            '  # then a human decides: push it, or record it as intentionally disposable'
        )
    for record in branches['unpushed_detached'][:2]:
        head = record['head'][:12]
        path = (record['paths'] or ['<unknown worktree>'])[0]
        commands.append(
            f'git -C {quote(path)} switch -c {quote(f"delivery-rescue/{head}")}'
            f'  # detached tip {head} is on no branch and no remote; name it before it ages out of the reflog'
        )
    if worktrees['dirty']:
        worst = worktrees['dirty'][0]
        commands.append(
            f'git -C {quote(worst["path"])} status --short'
            f'  # {worst["changed_files"]} uncommitted files'
        )
    if worktrees['missing']:
        commands.append('git worktree prune -n  # dry run: review the stale registrations before pruning')
    for entry in report['stashes']['entries'][:2]:
        label = entry['branch'] or 'unknown branch'
        commands.append(f'git stash show -p {quote(entry["selector"])}  # labelled {label}')
    for cause in worktrees['incomplete_causes'][:2]:
        commands.append(f'# the worktree scan was limited: {cause}')
    if len(commands) > MAX_REMEDIATIONS:
        hidden = len(commands) - (MAX_REMEDIATIONS - 1)
        return commands[: MAX_REMEDIATIONS - 1] + [
            f'# +{hidden} more next steps, untruncated in: python3 scripts/grok_doctor.py --git-audit-json'
        ]
    return commands


def _upstream_index(
    root: Path,
    budget: _Budget | None = None,
) -> dict[str, dict[str, str] | None] | None:
    """Resolve each configured upstream to `(base branch name, display ref)`.

    A branch with no `remote`/`merge` pair at all, or with an unparseable pair, maps to `None`.
    """
    configured = _configured_upstreams(root, budget)
    if configured is None:
        return None
    index: dict[str, dict[str, str] | None] = {}
    for branch, config in configured.items():
        index[branch] = _upstream_parts(config.get('remote', ''), config.get('merge', ''))
    return index


def audit_git_state(
    root: Path,
    *,
    worktree_scan_limit: int = MAX_WORKTREE_SCANS,
    budget_seconds: float | None = AUDIT_BUDGET_SECONDS,
) -> dict[str, Any]:
    """Audit one clone without changing it. Reads are bounded by a wall-clock budget.

    `budget_seconds` is a test seam as much as a safety bound: with a whole-repo scan budget of 0
    the audit must still report itself as limited rather than as clean.
    """
    root = Path(root)
    budget = _Budget(budget_seconds)
    reason = _unavailable_reason(root, budget)
    report: dict[str, Any] = {
        'read_only': True,
        'notice': READ_ONLY_NOTICE,
        'error': reason,
        'budget': {'seconds': budget_seconds, 'refused_reads': budget.refused},
        'degraded': budget.degraded,
        'git': {'repository': reason is None, 'unavailable_reason': reason},
        'repository': {'path': str(root), 'slug': None},
        'worktrees': {
            'registry_state': 'unknown', 'registered': None, 'scanned': 0,
            'truncated': False, 'incomplete': reason is not None,
            'incomplete_causes': [], 'over_limit': 0, 'out_of_time': 0,
            'unreadable': [], 'unreadable_count': None, 'detached': None, 'prunable': None,
            'dirty': [], 'dirty_state': 'unknown', 'missing': [], 'missing_count': None,
        },
        'branches': {
            'local': None, 'remotes': None, 'remote_refs': None, 'upstream_state': 'unknown',
            'upstream_protected_state': 'unknown', 'upstream_gone_state': 'unknown',
            'no_upstream_state': 'unknown',
            'upstream_protected': [], 'upstream_gone': [], 'no_upstream': [],
            'proven_upstreams': [],
            'unpushed_tips': [], 'unpushed_detached': [],
            'unpushed_state': 'skipped', 'unpushed_tips_state': 'unknown',
            'unpushed_detached_state': 'unknown', 'unpushed_skip_reason': reason,
            'delivery_caveat': DELIVERY_CAVEAT,
        },
        'stashes': {
            'count': None, 'entries': [], 'unreadable': reason is not None,
            'unreadable_cause': reason,
        },
        'human_commands': [],
    }
    if reason is not None:
        return report
    # Parsed once: the registry is both the worktree scan input and the only place a detached
    # worktree's HEAD is visible, so scanning it twice would cost a second full pass for nothing.
    entries, registry_code = _worktree_entries(root, budget)
    # The branches and stashes are read first on purpose. They cost a handful of commands; the
    # worktree scan costs one per registration and is the part the budget can cut off. Scanning
    # first would let a slow clone spend the whole budget before the headline hazard was read.
    report['branches'] = _audit_branches(
        root,
        entries,
        _upstream_index(root, budget),
        budget,
        worktree_registry_ok=registry_code == 0,
    )
    report['stashes'] = _audit_stashes(root, budget)
    report['worktrees'] = _audit_worktrees(
        root, entries, worktree_scan_limit, budget=budget, registry_code=registry_code
    )
    report['repository']['slug'] = _remote_slug(root, report['branches']['remotes'], budget)
    report['budget']['refused_reads'] = budget.refused
    report['human_commands'] = human_commands(report)
    return report


def _named_list(items: list[Any], limit: int = DETAIL_LIMIT) -> str:
    names = [item['branch'] if isinstance(item, dict) else str(item) for item in items]
    shown = ', '.join(names[:limit])
    return f'{shown} +{len(names) - limit} more' if len(names) > limit else shown


def _detached_list(records: list[dict[str, Any]], limit: int = DETAIL_LIMIT) -> str:
    """`<short sha> (<worktree path>)` for detached HEADs, which have no branch name."""
    names = [
        f"{record['head'][:12]} ({', '.join(record['paths'][:2])}"
        + (f" +{len(record['paths']) - 2} worktrees)" if len(record['paths']) > 2 else ')')
        for record in records
    ]
    shown = ', '.join(names[:limit])
    return f'{shown} +{len(names) - limit} more' if len(names) > limit else shown


def hazard_count(report: dict[str, Any]) -> int:
    branches = report['branches']
    worktrees = report['worktrees']
    # Empty tip lists from a skipped check are not a measured zero. Counting the skip
    # is what keeps the git-audit row and the screen closer from reading it as clean.
    unresolved_tip_check = branches.get('unpushed_state') != 'checked'
    return (
        len(branches['upstream_protected'])
        + len(branches['upstream_gone'])
        + len(branches['no_upstream'])
        + len(worktrees['dirty'])
        + (worktrees['missing_count'] or 0)
        + (report['stashes']['count'] or 0)
        + len(branches['unpushed_tips'])
        + len(branches['unpushed_detached'])
        + (1 if unresolved_tip_check else 0)
    )


def _limit_suffix(causes: list[str]) -> str:
    if not causes:
        return ''
    return '; not everything could be read: ' + '; '.join(causes)


def _section_causes(report: dict[str, Any], section: str) -> list[str]:
    """Why one section could not be fully read, naming each command and exit code."""
    return [
        f'{item["command"]} {_exit_cause(item["code"])}'
        for item in report['degraded']
        if item['section'] == section
    ]


def _derived_count(state: str, count: int, label: str) -> str:
    """Render a derived collection without turning unavailable inputs into a measured zero."""
    return f'{count} {label}' if state == 'checked' else f'unknown {label}'


def doctor_items(report: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Map the audit onto `(status, name, message)` health rows.

    Never `fail`: unpushed history is a risk to surface, not a repository-health failure that
    should block a verification gate. Equally, never `pass` for a section that could not be read:
    a degraded row is `info` and carries its own cause text, because each row is rendered on its
    own line and a green row that means "we did not look" is how this screen would lose work all
    over again.
    """
    if report['error']:
        return [('info', 'git-audit', f'{report["error"]}; delivery audit skipped')]
    branches = report['branches']
    worktrees = report['worktrees']
    stashes = report['stashes']
    budget = report.get('budget') or {}
    dirty = len(worktrees['dirty'])
    missing = worktrees['missing_count']
    unreadable = worktrees['unreadable_count']
    worktree_causes = list(worktrees['incomplete_causes'])
    detached_tips = len(branches['unpushed_detached'])
    tip_check_ran = branches['unpushed_state'] == 'checked'
    branch_causes = (
        [] if tip_check_ran else [f'tip check skipped: {branches["unpushed_skip_reason"]}']
    ) + _section_causes(report, 'branches')
    upstream_summary = ', '.join(
        (
            _derived_count(
                branches['upstream_protected_state'],
                len(branches['upstream_protected']),
                'protected-upstream',
            ),
            _derived_count(
                branches['upstream_gone_state'],
                len(branches['upstream_gone']),
                'gone-upstream',
            ),
            _derived_count(
                branches['no_upstream_state'],
                len(branches['no_upstream']),
                'without upstream',
            ),
        )
    )
    dirty_summary = _derived_count(
        worktrees['dirty_state'], dirty, 'with uncommitted changes'
    )
    unpushed_summary = _derived_count(
        branches['unpushed_tips_state'],
        len(branches['unpushed_tips']),
        'not reachable from any remote',
    )
    detached_summary = (
        f', {detached_tips} detached worktree tips not reachable either'
        if branches['unpushed_detached_state'] == 'checked' and detached_tips
        else (
            ', unknown detached worktree tips not reachable'
            if branches['unpushed_detached_state'] == 'unknown'
            else ''
        )
    )
    stash_causes = _section_causes(report, 'stashes')
    items: list[tuple[str, str, str]] = [
        (
            'info' if (dirty or missing or unreadable or worktree_causes) else 'pass',
            'git-worktrees',
            (
                f'{worktrees["registered"]} registered, {dirty_summary}, '
                f'{missing} pointing at a deleted directory, {unreadable} unreadable, '
                f'{worktrees["prunable"]} prunable, {worktrees["scanned"]} scanned'
                if worktrees['registry_state'] == 'checked'
                else (
                    f'unknown registered worktrees, {dirty_summary}, '
                    f'{worktrees["scanned"]} scanned'
                )
            )
            + _limit_suffix(worktree_causes),
        ),
        (
            'info'
            if (
                branches['upstream_protected']
                or branches['upstream_gone']
                or branches['no_upstream']
                or branches['unpushed_tips']
                or detached_tips
                or branch_causes
            )
            else 'pass',
            'git-branches',
            (
                f'{branches["local"]} local'
                if branches['local'] is not None
                else 'unknown local branches'
            )
            + '; '
            + (
                f'{branches["remote_refs"]} remote-tracking refs'
                if branches['remote_refs'] is not None
                else 'unknown remote-tracking refs'
            )
            + f'; {upstream_summary}, '
            f'{unpushed_summary}'
            + detached_summary
            + _limit_suffix(branch_causes),
        ),
        (
            'info' if (stashes['count'] or stashes['unreadable'] or stash_causes) else 'pass',
            'git-stashes',
            (
                f'{stashes["count"]} stash entries; labels: '
                f'{_named_list(stashes["entries"]) or "none"}'
                if stashes['count']
                else (
                    f'stash list could not be read ({stashes["unreadable_cause"]}), '
                    'so the count is unknown rather than zero'
                    if stashes['unreadable']
                    else 'no stash entries'
                )
            )
            + _limit_suffix(stash_causes),
        ),
    ]
    notice_status = (
        'info'
        if hazard_count(report) or report['degraded'] or worktrees['incomplete']
        else 'pass'
    )
    items.append(
        (
            notice_status,
            'git-audit',
            f'{READ_ONLY_NOTICE}; detail: python3 scripts/grok_doctor.py --git-audit',
        )
    )
    if report['degraded']:
        causes = [f'{item["command"]} {_exit_cause(item["code"])}' for item in report['degraded']]
        items.append(
            (
                'info',
                'git-audit-limited',
                f'{len(report["degraded"])} Git read(s) could not be trusted, so the rows above are '
                f'partial: {"; ".join(causes[:DETAIL_LIMIT])}'
                + (f'; +{len(causes) - DETAIL_LIMIT} more' if len(causes) > DETAIL_LIMIT else '')
                + f'; {budget.get("refused_reads", 0)} read(s) were not attempted'
                f' (budget {budget.get("seconds")}s)',
            )
        )
    return items


def format_audit(report: dict[str, Any]) -> str:
    """The one screen a human reads before losing work."""
    lines = ['GIT DELIVERY AUDIT (read-only)']
    if report['error']:
        lines.append(f'  unavailable: {report["error"]}')
        return '\n'.join(lines)
    branches = report['branches']
    worktrees = report['worktrees']
    lines.append(f'  repository: {report["repository"]["path"]}')
    lines.append(
        (
            f'  worktrees: {worktrees["registered"]} registered, {worktrees["scanned"]} scanned, '
            f'{worktrees["detached"]} detached, {worktrees["missing_count"]} absent from disk, '
            f'{worktrees["unreadable_count"]} unreadable, {worktrees["prunable"]} prunable'
            if worktrees['registry_state'] == 'checked'
            else f'  worktrees: unknown registered, {worktrees["scanned"]} scanned'
        )
    )
    for cause in worktrees['incomplete_causes']:
        lines.append(f'    scan incomplete: {cause}')
    if worktrees['dirty_state'] == 'unknown':
        lines.append(
            '    dirty worktrees: unknown total'
            + (f' ({len(worktrees["dirty"])} observed)' if worktrees['dirty'] else '')
        )
    for entry in worktrees['dirty'][:DETAIL_LIMIT]:
        lines.append(f'    dirty: {entry["changed_files"]:>4} files  {entry["branch"] or "(detached)"}  {entry["path"]}')
    if len(worktrees['dirty']) > DETAIL_LIMIT:
        lines.append(f'    dirty: +{len(worktrees["dirty"]) - DETAIL_LIMIT} more')
    for entry in worktrees['missing'][:DETAIL_LIMIT]:
        lines.append(f'    absent: {entry["branch"] or "(detached)"}  {entry["path"]}  ({entry["reason"]})')
    if worktrees['unreadable']:
        lines.append(f'    unreadable: {", ".join(worktrees["unreadable"])}')
    lines.append(
        '  branches: '
        + (f'{branches["local"]} local' if branches['local'] is not None else 'unknown local branches')
        + ', '
        + (
            f'{branches["remote_refs"]} remote-tracking refs'
            if branches['remote_refs'] is not None
            else 'unknown remote-tracking refs'
        )
        + ', '
        + (
            f'remotes: {", ".join(branches["remotes"]) or "none"}'
            if branches['remotes'] is not None
            else 'remotes: unknown'
        )
    )
    if branches['upstream_protected_state'] == 'unknown':
        lines.append('    protected upstreams: unknown (local refs or upstream config unavailable)')
    else:
        for entry in branches['upstream_protected'][:DETAIL_LIMIT]:
            lines.append(
                f'    upstream is a protected base: {entry["branch"]} -> {entry["upstream"]}'
            )
        if len(branches['upstream_protected']) > DETAIL_LIMIT:
            lines.append(
                '    upstream is a protected base: '
                f'+{len(branches["upstream_protected"]) - DETAIL_LIMIT} more'
            )
    if branches['upstream_gone_state'] == 'unknown':
        lines.append(
            '    gone upstreams: unknown (local refs, remote refs or upstream config unavailable)'
        )
    else:
        for entry in branches['upstream_gone'][:DETAIL_LIMIT]:
            lines.append(f'    upstream ref is gone: {entry["branch"]} -> {entry["upstream"]}')
    if branches['no_upstream_state'] == 'unknown':
        lines.append('    branches without upstream: unknown (local refs or upstream config unavailable)')
    elif branches['no_upstream']:
        lines.append(f'    no upstream configured: {_named_list(branches["no_upstream"])}')
    if branches['unpushed_state'] == 'skipped':
        lines.append(f'    unpushed-tip check skipped: {branches["unpushed_skip_reason"]}')
        if branches['unpushed_detached_state'] == 'unknown':
            lines.append(
                f'    detached-tip check skipped: {branches["unpushed_skip_reason"]}'
            )
    else:
        lines.append(f'    tips on no remote: {_named_list(branches["unpushed_tips"]) or "none"}')
        lines.append(
            f'    detached tips on no remote: {_detached_list(branches["unpushed_detached"]) or "none"}'
        )
        lines.append(f'    caveat: {branches["delivery_caveat"]}')
    stashes = report['stashes']
    lines.append(
        f'  stashes: {stashes["count"]} entries (shared by every worktree in this clone)'
        if stashes['count'] is not None
        else '  stashes: unknown (stash registry could not be read)'
    )
    if stashes['unreadable']:
        lines.append(f'    stash list could not be read: {stashes["unreadable_cause"]}')
    for entry in stashes['entries']:
        lines.append(f'    {entry["selector"]}: on {entry["branch"] or "?"}: {entry["subject"]}')
    for item in report['degraded']:
        lines.append(f'  limited: {item["command"]} {_exit_cause(item["code"])}')
    if report['human_commands']:
        lines.append('HUMAN-OWNED next steps (the doctor does not run any of these):')
        lines.extend(f'  {command}' for command in report['human_commands'])
    elif hazard_count(report) or report['degraded'] or worktrees['incomplete']:
        lines.append(
            'HUMAN-OWNED next steps: none suggested, but hazards were seen - '
            'the audit could not resolve a safe command for them'
        )
    else:
        lines.append('HUMAN-OWNED next steps: none - no delivery hazard found')
    lines.append(f'  notice: {report["notice"]}')
    return '\n'.join(lines)
