"""Mechanical existence checks for identifier tokens cited as proof.

Receipts, tree fingerprints, spec digests and attestation ids are the load-bearing evidence
tokens of this stack, and every downstream staleness or merge gate trusts them blindly. A
report can therefore cite a *plausible* hex that exists in no receipt and still read as
verified. The set of real identifiers is enumerable from machine state, so existence is a
mechanical question and never a judgment call: this module answers it.

It checks identifier existence only. It cannot tell whether a real fingerprint was bound to
the claim the report attaches it to, and it does not claim to.
"""
from __future__ import annotations

import bisect
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

MIN_TOKEN_LENGTH = 8
MAX_TOKEN_LENGTH = 64
MAX_CORPUS_FILE_BYTES = 4 * 1024 * 1024

# Maximal hex runs only, so a truncated citation is compared against a whole identifier
# rather than against an arbitrary slice of one.
_HEX_RUN = re.compile(r'(?<![0-9A-Fa-f])([0-9A-Fa-f]{8,64})(?![0-9A-Fa-f])')

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


@dataclass(frozen=True)
class Citation:
    token: str
    document: str
    line: int

    def to_dict(self) -> dict[str, object]:
        return {'token': self.token, 'document': self.document, 'line': self.line}


def is_identifier_like(token: str) -> bool:
    """Exclude decimal noise (dates, counters, port digits) from the identifier question."""
    if not MIN_TOKEN_LENGTH <= len(token) <= MAX_TOKEN_LENGTH:
        return False
    lowered = token.lower()
    if not any(character in 'abcdef' for character in lowered):
        return False
    if len(set(lowered)) < 3:
        return False
    return True


def extract_citations(text: str, document: str) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[tuple[str, int]] = set()
    for number, line in enumerate(text.splitlines(), start=1):
        for match in _HEX_RUN.finditer(line):
            token = match.group(1)
            if not is_identifier_like(token):
                continue
            key = (token.lower(), number)
            if key in seen:
                continue
            seen.add(key)
            citations.append(Citation(token=token, document=document, line=number))
    return citations


def _iter_corpus_paths(root: Path) -> Iterable[Path]:
    for pattern in CORPUS_GLOBS:
        directory, _, filename = pattern.partition('/')
        if not (root / directory).exists():
            continue
        for path in sorted(root.glob(pattern)):
            yield path


def corpus_identifiers(root: Path) -> tuple[set[str], int]:
    """Return every identifier-shaped token held in machine state, and how many files spoke."""
    identifiers: set[str] = set()
    files_read = 0
    for path in _iter_corpus_paths(root):
        try:
            if path.is_symlink() or not path.is_file():
                continue
            if path.stat().st_size > MAX_CORPUS_FILE_BYTES:
                continue
            raw = path.read_bytes()
        except OSError:
            continue
        files_read += 1
        text = raw.decode('utf-8', errors='replace')
        for match in _HEX_RUN.finditer(text):
            token = match.group(1)
            if is_identifier_like(token):
                identifiers.add(token.lower())
    return identifiers, files_read


def _resolves_as_git_object(root: Path, token: str) -> bool:
    """A cited commit/tree/blob id is real even though no receipt repeats it."""
    if len(token) < 7 or not re.fullmatch(r'[0-9a-fA-F]{7,40}', token):
        return False
    if os.environ.get('GROK_CITATIONS_SKIP_GIT') == '1':
        return False
    try:
        completed = subprocess.run(
            ['git', 'cat-file', '-e', token],
            cwd=root,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def _matches_corpus(token: str, sorted_identifiers: list[str]) -> str | None:
    """Accept an exact identifier or a faithful prefix/suffix truncation of one."""
    lowered = token.lower()
    index = bisect.bisect_left(sorted_identifiers, lowered)
    if index < len(sorted_identifiers) and sorted_identifiers[index] == lowered:
        return 'exact'
    if index < len(sorted_identifiers) and sorted_identifiers[index].startswith(lowered):
        return 'prefix'
    if index > 0:
        candidate = sorted_identifiers[index - 1]
        if lowered.startswith(candidate) and len(candidate) >= MIN_TOKEN_LENGTH:
            return 'extended-citation'
    return None


def find_unresolved(root: Path, citations: Iterable[Citation]) -> list[dict[str, object]]:
    """Report cited tokens that exist in no machine-state identifier and in no Git object."""
    collected = [item for item in citations if isinstance(item, Citation)]
    if not collected:
        return []
    identifiers, _files_read = corpus_identifiers(root)
    ordered = sorted(identifiers)
    unresolved: list[dict[str, object]] = []
    resolved_cache: dict[str, str | None] = {}
    for citation in collected:
        token = citation.token.lower()
        if token not in resolved_cache:
            resolved_cache[token] = _matches_corpus(token, ordered)
        if resolved_cache[token] is not None:
            continue
        if _resolves_as_git_object(root, citation.token):
            continue
        unresolved.append({**citation.to_dict(), 'resolved_by': None})
    return unresolved


def audit_documents(root: Path, documents: list[tuple[str, str]]) -> dict[str, object]:
    """Audit ``document`` -> text pairs and summarize the mechanical verdict."""
    citations = [citation for name, text in documents for citation in extract_citations(text, name)]
    unresolved = find_unresolved(root, citations)
    distinct = {item.token.lower() for item in citations}
    missing = {str(item['token']).lower() for item in unresolved}
    identifiers, corpus_files = corpus_identifiers(root)
    return {
        'schema_version': 1,
        'documents': [name for name, _ in documents],
        'citation_count': len(citations),
        'distinct_tokens': len(distinct),
        'unresolved_count': len(missing),
        'unresolved': unresolved,
        'corpus_files': corpus_files,
        'corpus_identifiers': len(identifiers),
        'status': 'pass' if not missing else 'fail',
    }
