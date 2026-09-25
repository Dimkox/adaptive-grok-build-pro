"""Mechanical existence checks for identifier tokens cited as proof.

Receipts, tree fingerprints, spec digests and attestation ids are the load-bearing evidence
tokens of this stack, and every downstream staleness or merge gate trusts them blindly. A
report can therefore cite a *plausible* hex that exists in no receipt and still read as
verified. The set of real identifiers is enumerable from machine state, so existence is a
mechanical question and never a judgment call: this module answers it.

It checks identifier existence only. It cannot tell whether a real fingerprint was bound to
the claim the report attaches it to, and it does not claim to.

Two boundaries make the answer trustworthy rather than merely convenient:

* Nothing is accepted silently. A hex run that the checker declines to judge (all-decimal
  noise, a degenerate repeat, or a run longer than the identifier ceiling such as a sha512)
  is counted and reported, so a clean result is never confused with an unjudged one.
* A document that could not be read is an error, not a pass. The caller reports it as such.
"""
from __future__ import annotations

import bisect
import json
import os
import re
import stat
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

MIN_TOKEN_LENGTH = 8
MAX_TOKEN_LENGTH = 64
MAX_CORPUS_FILE_BYTES = 4 * 1024 * 1024
# Bound the whole scan, not just each file: a repository with a pathological number of
# machine-state files must cost a bounded amount rather than reading indefinitely.
MAX_CORPUS_TOTAL_BYTES = 64 * 1024 * 1024
MAX_CORPUS_FILES = 20_000
# Git resolution is one batched query, not one spawn per token, but the number of candidates it
# is asked about is still capped; a capped or short-answered query is reported rather than read
# as "absent".
MAX_GIT_PROBES = 1_000

# Maximal hex runs of any length. Matching unbounded runs (rather than {8,64}) is what makes a
# too-long run, such as a sha512, visible as declined instead of invisible to the extractor.
_HEX_RUN = re.compile(r'(?<![0-9A-Fa-f])[0-9A-Fa-f]+(?![0-9A-Fa-f])')

# Machine state that legitimately carries identifiers, plus the released artifact digests and
# generated architecture digests. Report prose is deliberately excluded: a fabricated token
# must not become authoritative because an earlier report repeated it.
CORPUS_GLOBS = (
    '.grok-stack/runtime/**/*.json',
    'engineering/changes/*/change-spec.yaml',
    'engineering/changes/*/state.json',
    'engineering/changes/*/route.json',
    'engineering/changes/*/human-gates.json',
    'engineering/contracts/**/*',
    'architecture/generated/**',
    'packages/*.sha256',
    'delivery/**/*.json',
)

# Hand-editable package and runtime documents carry prose as well as machine values, so a hex
# written into a title or a reason line would otherwise become authoritative tree-wide. In a
# structured file only a value sitting under an identifier-bearing key counts as an identifier.
IDENTIFIER_KEY_SEGMENTS = frozenset(
    {
        'id',
        'sha',
        'sha1',
        'sha256',
        'sha512',
        'hash',
        'digest',
        'fingerprint',
        'commit',
        'head',
        'base',
        'target',
        'oid',
        'rev',
        'revision',
        'receipt',
        'attestation',
        'signature',
        'certificate',
        'token',
        'epoch',
        'policy',
        'version',
    }
)
_DECLINE_REASONS = frozenset({'decimal-only', 'degenerate', 'over-max'})
_LINE_KEY = re.compile(r'["\']?(?P<key>[A-Za-z0-9_.:-]{1,128})["\']?\s*:')


@dataclass(frozen=True)
class Citation:
    token: str
    document: str
    line: int

    def to_dict(self) -> dict[str, object]:
        return {'token': self.token, 'document': self.document, 'line': self.line}


@dataclass
class CorpusScan:
    """The enumerable set of real identifiers, plus how much of the corpus was not judged."""

    identifiers: set[str] = field(default_factory=set)
    files_read: int = 0
    files_skipped: int = 0
    total_bytes: int = 0
    truncated: bool = False


def _key_is_identifier_bearing(key_path: Iterable[str]) -> bool:
    for component in key_path:
        for segment in re.split(r'[^A-Za-z0-9]+', component):
            lowered = segment.lower()
            if not lowered:
                continue
            if lowered in IDENTIFIER_KEY_SEGMENTS or lowered.rstrip('s') in IDENTIFIER_KEY_SEGMENTS:
                return True
    return False


def decline_reason(token: str) -> str | None:
    """Name why a hex run is not an identifier, or None when it is one."""
    if len(token) < MIN_TOKEN_LENGTH:
        return 'short'
    if len(token) > MAX_TOKEN_LENGTH:
        return 'over-max'
    if not any(character in 'abcdef' for character in token.lower()):
        return 'decimal-only'
    if len(set(token.lower())) < 3:
        return 'degenerate'
    return None


def is_declined_identifier_like(token: str) -> bool:
    """True when a run is long enough to look like an id but is deliberately not judged."""
    return decline_reason(token) in _DECLINE_REASONS


def is_identifier_like(token: str) -> bool:
    """Exclude decimal noise (dates, counters, port digits) from the identifier question."""
    return decline_reason(token) is None


def extract_citations(text: str, document: str) -> list[Citation]:
    """Every identifier-shaped hex run cited in ``document``, taken a whole run at a time."""
    citations, _declined = scan_document(text, document)
    return citations


def scan_document(text: str, document: str) -> tuple[list[Citation], dict[str, int]]:
    """Return the judged citations and a per-reason count of the runs that were declined."""
    citations: list[Citation] = []
    declined: dict[str, int] = {}
    seen: set[tuple[str, int]] = set()
    for number, line in enumerate(text.splitlines(), start=1):
        for match in _HEX_RUN.finditer(line):
            token = match.group(0)
            reason = decline_reason(token)
            if reason is not None:
                if reason in _DECLINE_REASONS:
                    declined[reason] = declined.get(reason, 0) + 1
                continue
            key = (token.lower(), number)
            if key in seen:
                continue
            seen.add(key)
            citations.append(Citation(token=token, document=document, line=number))
    return citations, declined


def _root_bound(root: Path) -> Path:
    try:
        return root.resolve(strict=True)
    except OSError:
        return root.resolve(strict=False)


def _escapes_root(path: Path, canonical_root: Path) -> bool:
    """True when following ``path`` can read content that is not inside the repository."""
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return True
    return canonical_root not in resolved.parents and resolved != canonical_root


def _iter_corpus_paths(root: Path) -> Iterable[Path]:
    canonical_root = _root_bound(root)
    for pattern in CORPUS_GLOBS:
        directory, _, _filename = pattern.partition('/')
        if not (root / directory).exists():
            continue
        for path in sorted(root.glob(pattern)):
            # A symlinked directory in a glob is followed by Path.glob, so containment is
            # checked on the resolved target rather than on the link text.
            if _escapes_root(path, canonical_root):
                continue
            yield path


def _structured_identifiers(raw: bytes, identifiers: set[str]) -> bool:
    """Collect identifier-keyed values from a JSON document. True when it parsed."""
    try:
        data = json.loads(raw.decode('utf-8', errors='replace'))
    except (UnicodeDecodeError, ValueError):
        return False
    collected: set[str] = set()
    pending: list[tuple[Any, tuple[str, ...]]] = [(data, ())]
    while pending:
        node, key_path = pending.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                pending.append((value, key_path + (str(key),)))
        elif isinstance(node, list):
            for value in node:
                pending.append((value, key_path))
        elif isinstance(node, str):
            if not _key_is_identifier_bearing(key_path):
                continue
            for match in _HEX_RUN.finditer(node):
                token = match.group(0)
                if is_identifier_like(token):
                    collected.add(token.lower())
    identifiers |= collected
    return True


def _line_keyed_identifiers(text: str, identifiers: set[str]) -> None:
    """YAML side of the same rule: a value counts only when its own line names an id-bearing key."""
    collected: set[str] = set()
    for line in text.splitlines():
        match = _LINE_KEY.search(line)
        if match is None or not _key_is_identifier_bearing((match.group('key'),)):
            continue
        for found in _HEX_RUN.finditer(line):
            token = found.group(0)
            if is_identifier_like(token):
                collected.add(token.lower())
    identifiers |= collected


def corpus_identifiers(root: Path) -> CorpusScan:
    """Return every identifier-shaped token held in machine state, and what was not read."""
    scan = CorpusScan()
    identifiers = scan.identifiers
    for path in _iter_corpus_paths(root):
        if scan.files_read >= MAX_CORPUS_FILES or scan.total_bytes >= MAX_CORPUS_TOTAL_BYTES:
            scan.truncated = True
            break
        try:
            stat_result = path.lstat()
            if stat.S_ISLNK(stat_result.st_mode) or not stat.S_ISREG(stat_result.st_mode):
                scan.files_skipped += 1
                continue
            if stat_result.st_size > MAX_CORPUS_FILE_BYTES:
                scan.files_skipped += 1
                continue
            raw = path.read_bytes()
        except OSError:
            scan.files_skipped += 1
            continue
        suffix = path.suffix.lower()
        collected: set[str] = set()
        if suffix == '.json':
            # Malformed machine state is not authoritative: an unparseable file contributes
            # nothing rather than falling back to whatever prose it happens to contain.
            if not _structured_identifiers(raw, collected):
                scan.files_skipped += 1
                continue
        elif suffix in ('.yaml', '.yml'):
            _line_keyed_identifiers(raw.decode('utf-8', errors='replace'), collected)
        else:
            text = raw.decode('utf-8', errors='replace')
            for match in _HEX_RUN.finditer(text):
                token = match.group(0)
                if is_identifier_like(token):
                    collected.add(token.lower())
        scan.total_bytes += len(raw)
        scan.files_read += 1
        identifiers |= collected
    return scan


def _git_candidate(token: str) -> bool:
    return 7 <= len(token) <= 40 and re.fullmatch(r'[0-9a-fA-F]{7,40}', token) is not None


def _resolves_as_git_objects(root: Path, tokens: list[str]) -> tuple[set[str], bool]:
    """Resolve cited commit ids with one bounded batch query instead of one spawn per token.

    Returns the tokens Git reports as existing, and whether any candidate went unprobed.
    ``GROK_CITATIONS_SKIP_GIT=1`` disables the query entirely; it is host configuration and can
    only make the check stricter, never more permissive.
    """
    candidates = [token for token in tokens if _git_candidate(token)]
    if not candidates:
        return set(), False
    if os.environ.get('GROK_CITATIONS_SKIP_GIT') == '1':
        return set(), True
    capped = len(candidates) > MAX_GIT_PROBES
    batch = candidates[:MAX_GIT_PROBES]
    try:
        completed = subprocess.run(
            ['git', 'cat-file', '--batch-check'],
            cwd=root,
            input='\n'.join(batch) + '\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return set(), True
    lines = completed.stdout.splitlines()
    if len(lines) != len(batch):
        # batch-check answers every input with exactly one line; a short answer means some
        # candidate was not judged, which is reported rather than read as absent.
        capped = True
    resolved: set[str] = set()
    for token, line in zip(batch, lines):
        name, _, rest = line.partition(' ')
        lowered = name.lower()
        answered = rest.rstrip().endswith('missing') or rest.rstrip().endswith('ambiguous')
        if answered:
            continue
        # A hit prints the resolved object id (so an abbreviation answers with the full oid);
        # a miss echoes the requested name and prints "missing".
        if lowered == token.lower() or re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', lowered):
            resolved.add(token.lower())
    return resolved, capped


def _matches_corpus(token: str, sorted_identifiers: list[str]) -> str | None:
    """Accept an exact identifier or a faithful truncation of one, and nothing longer.

    A citation that is *longer* than every real identifier it starts with is not a truncation of
    anything: it is a genuine prefix with an invented tail, which is precisely the shape issue
    206 was filed about, so no acceptance rule here covers it.
    """
    lowered = token.lower()
    index = bisect.bisect_left(sorted_identifiers, lowered)
    if index < len(sorted_identifiers) and sorted_identifiers[index] == lowered:
        return 'exact'
    if index < len(sorted_identifiers) and sorted_identifiers[index].startswith(lowered):
        return 'prefix'
    return None


def find_unresolved(root: Path, citations: Iterable[Citation]) -> list[dict[str, object]]:
    """Report cited tokens that exist in no machine-state identifier and in no Git object."""
    unresolved, _scan, _git_capped = resolve_citations(root, citations, corpus=None)
    return unresolved


def resolve_citations(
    root: Path,
    citations: Iterable[Citation],
    *,
    corpus: CorpusScan | None,
) -> tuple[list[dict[str, object]], CorpusScan, bool]:
    """One corpus walk and one Git batch query for a whole set of citations."""
    collected = [item for item in citations if isinstance(item, Citation)]
    scan = corpus if corpus is not None else corpus_identifiers(root)
    if not collected:
        return [], scan, False
    ordered = sorted(scan.identifiers)
    verdicts = {token: _matches_corpus(token, ordered) for token in {item.token.lower() for item in collected}}
    pending = sorted(token for token, verdict in verdicts.items() if verdict is None)
    git_resolved, git_capped = _resolves_as_git_objects(root, pending)
    unresolved: list[dict[str, object]] = []
    for citation in collected:
        if verdicts[citation.token.lower()] is not None:
            continue
        if citation.token.lower() in git_resolved:
            continue
        unresolved.append({**citation.to_dict(), 'resolved_by': None})
    return unresolved, scan, git_capped


def audit_documents(
    root: Path,
    documents: list[tuple[str, str]],
    *,
    unreadable: list[str] | None = None,
) -> dict[str, object]:
    """Audit ``document`` -> text pairs and summarize the mechanical verdict.

    A document that was named but never read makes the whole audit ``error``: reporting a pass
    about content that was never looked at is the failure this tool exists to prevent.
    """
    citations: list[Citation] = []
    declined: dict[str, int] = {}
    for name, text in documents:
        found, reasons = scan_document(text, name)
        citations.extend(found)
        for reason, count in reasons.items():
            declined[reason] = declined.get(reason, 0) + count
    unreadable = list(unreadable or [])
    unresolved, scan, git_capped = resolve_citations(root, citations, corpus=None)
    distinct = {item.token.lower() for item in citations}
    missing = {str(item['token']).lower() for item in unresolved}
    if unreadable:
        status = 'error'
    elif missing:
        status = 'fail'
    else:
        status = 'pass'
    return {
        'schema_version': 1,
        'documents': [name for name, _ in documents],
        'citation_count': len(citations),
        'distinct_tokens': len(distinct),
        'unresolved_count': len(unresolved),
        'unresolved_distinct_tokens': len(missing),
        'unresolved': unresolved,
        'declined_runs': sum(declined.values()),
        'declined_by_reason': dict(sorted(declined.items())),
        'corpus_files': scan.files_read,
        'corpus_files_skipped': scan.files_skipped,
        'corpus_identifiers': len(scan.identifiers),
        'corpus_truncated': scan.truncated,
        'git_probes_capped': git_capped,
        'unreadable_documents': unreadable,
        'status': status,
    }
