from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import PurePosixPath
import re
import unicodedata
from typing import Any, Mapping

from .contracts import canonical_digest
from .models import FailureClass
from .protocol import (
    CanonicalEvent,
    MAX_DURABLE_PATH_BYTES,
    ProtocolError,
    contains_structural_secret,
    validate_note_type,
)


_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_MEDIA_TYPE = re.compile(r"^[a-z0-9.+-]+/[a-z0-9.+-]+$")
_PEM_BLOCK = re.compile(
    r"-----BEGIN ([A-Z0-9 ]*PRIVATE KEY)-----.*?-----END \1-----",
    re.DOTALL,
)
_PEM_MARKER = re.compile(r"-----(?:BEGIN|END) [A-Z0-9 ]*PRIVATE KEY-----")
_BEARER = re.compile(r"(?i)\bBearer[ \t]+[A-Za-z0-9._~+/=-]+")
_AUTHORIZATION = re.compile(
    r"(?im)(?<![A-Za-z0-9_-])(?:[A-Za-z0-9]+[_-])*Authorization"
    r"[ \t]*[=:][ \t]*[^\r\n]*"
)
_SECRET = re.compile(
    r"(?i)(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]+"
    r"|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
    r"|(?<![A-Za-z0-9_-])(?:[\"'])?(?:[a-z0-9]+[_-])*(?:api[_-]?key|"
    r"access[_-]?token|session[_-]?token|client[_-]?secret|refresh[_-]?token|"
    r"password|credential|secret[_-]?key|private[_-]?key|token|secret)"
    r"(?:[_-][a-z0-9]+)*(?:[\"'])?(?![A-Za-z0-9_-])"
    r"[ \t]*[:=][ \t]*(?:\"[^\"\r\n]+\"|'[^'\r\n]+'|[^\s,;}]+)"
)
_TERMINAL = frozenset({"run.completed", "run.failed", "run.needs_human"})
MAX_PROPOSAL_ENVELOPE_BYTES = 1_048_576


class BrokerError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


@dataclass(frozen=True)
class ProposalContext:
    task_id: str
    run_id: str
    owner: str
    fence: int
    packet_digest: str
    role: str
    repository_id: str
    workspace_handle: str
    allowed_paths: tuple[str, ...]
    allowed_artifact_classes: tuple[str, ...]
    max_note_bytes: int
    max_artifact_bytes: int
    max_output_bytes: int
    max_cost_usd_micros: int
    max_token_units: int
    declared_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class NoteProposal:
    task_id: str
    run_id: str
    packet_digest: str
    fence: int
    sequence: int
    author_role: str
    note_type: str
    body: str
    evidence: tuple[str, ...]
    idempotency_key: str


@dataclass(frozen=True)
class ArtifactProposal:
    task_id: str
    run_id: str
    packet_digest: str
    fence: int
    sequence: int
    author_role: str
    artifact_class: str
    path: str
    sha256: str
    size_bytes: int
    media_type: str
    artifact_attestation_digest: str
    idempotency_key: str


@dataclass(frozen=True)
class UsageProposal:
    task_id: str
    run_id: str
    packet_digest: str
    fence: int
    sequence: int
    author_role: str
    provider_call_id: str
    price_table_digest: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    cost_usd_micros: int
    output_bytes: int
    idempotency_key: str

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.reasoning_tokens


@dataclass(frozen=True)
class TerminalProposal:
    task_id: str
    run_id: str
    packet_digest: str
    fence: int
    sequence: int
    author_role: str
    terminal_type: str
    summary: str
    failure_class: str | None
    reason: str | None
    diagnostic: str | None
    idempotency_key: str


def _bounded_proposal(proposal):
    wire = json.dumps(
        asdict(proposal),
        ensure_ascii=False,
        sort_keys=True,
        separators=(", ", ": "),
    ).encode("utf-8")
    if len(wire) > MAX_PROPOSAL_ENVELOPE_BYTES:
        raise BrokerError("proposal_too_large")
    return proposal


def _redact(value: str, max_bytes: int) -> str:
    if not isinstance(value, str):
        raise BrokerError("invalid_text")
    try:
        raw = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise BrokerError("invalid_text") from exc
    if len(raw) > max_bytes:
        raise BrokerError("text_too_large")
    redacted = _PEM_BLOCK.sub("[REDACTED]", value)
    if _PEM_MARKER.search(redacted):
        raise BrokerError("secret_content")
    redacted = _AUTHORIZATION.sub("[REDACTED]", redacted)
    redacted = _BEARER.sub("[REDACTED]", redacted)
    redacted = _SECRET.sub("[REDACTED]", redacted)
    if len(redacted.encode("utf-8")) > max_bytes:
        raise BrokerError("text_too_large")
    return redacted


def _result_text(value: str, max_bytes: int) -> str:
    if (
        not isinstance(value, str)
        or unicodedata.normalize("NFC", value) != value
        or any(ord(char) < 32 for char in value)
    ):
        raise BrokerError("terminal_text")
    return _redact(value, max_bytes)


def _secret_free(value: str, maximum: int, code: str = "secret_identity") -> str:
    if contains_structural_secret(value) or _redact(value, maximum) != value:
        raise BrokerError(code)
    return value


def secret_free_identity(value: str, maximum: int = 128) -> str:
    return _secret_free(value, maximum)


def _safe_path(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise BrokerError(code)
    _secret_free(value, MAX_DURABLE_PATH_BYTES)
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or ".git" in path.parts or str(path) != value:
        raise BrokerError(code)
    return value


def _allowed_path(value: Any, context: ProposalContext, code: str) -> str:
    value = _safe_path(value, code)
    candidate = PurePosixPath(value)
    roots = tuple(PurePosixPath(_safe_path(root, "invalid_allowed_path")) for root in context.allowed_paths)
    if not any(candidate == root or root in candidate.parents for root in roots):
        raise BrokerError("path_forbidden")
    return value


def _key(event: CanonicalEvent, context: ProposalContext, body: Mapping[str, Any]) -> str:
    return canonical_digest(
        {
            "contract": "adaptive-factory.execution-proposal/v1",
            "task_id": context.task_id,
            "run_id": context.run_id,
            "packet_digest": context.packet_digest,
            "fence": context.fence,
            "author_role": context.role,
            "sequence": event.sequence,
            "event_type": event.event_type,
            "body": dict(body),
        }
    )


def proposal_idempotency_key(
    proposal: NoteProposal | ArtifactProposal | UsageProposal | TerminalProposal,
) -> str:
    if isinstance(proposal, NoteProposal):
        event_type = "note.proposed"
        body = {
            "note_type": proposal.note_type,
            "body": proposal.body,
            "evidence": proposal.evidence,
        }
    elif isinstance(proposal, ArtifactProposal):
        event_type = "artifact.proposed"
        body = {
            "artifact_class": proposal.artifact_class,
            "path": proposal.path,
            "sha256": proposal.sha256,
            "size_bytes": proposal.size_bytes,
            "media_type": proposal.media_type,
            "author_role": proposal.author_role,
            "artifact_attestation_digest": proposal.artifact_attestation_digest,
        }
    elif isinstance(proposal, UsageProposal):
        event_type = "usage.reported"
        body = {
            "provider_call_id": proposal.provider_call_id,
            "price_table_digest": proposal.price_table_digest,
            "input_tokens": proposal.input_tokens,
            "output_tokens": proposal.output_tokens,
            "reasoning_tokens": proposal.reasoning_tokens,
            "cost_usd_micros": proposal.cost_usd_micros,
            "output_bytes": proposal.output_bytes,
            "author_role": proposal.author_role,
        }
    elif isinstance(proposal, TerminalProposal):
        event_type = proposal.terminal_type
        body = {
            "terminal_type": proposal.terminal_type,
            "author_role": proposal.author_role,
            "summary": proposal.summary,
            "failure_class": proposal.failure_class,
            "reason": proposal.reason,
            "diagnostic": proposal.diagnostic,
        }
    else:
        raise BrokerError("unsupported_proposal")
    return canonical_digest({
        "contract": "adaptive-factory.execution-proposal/v1",
        "task_id": proposal.task_id,
        "run_id": proposal.run_id,
        "packet_digest": proposal.packet_digest,
        "fence": proposal.fence,
        "author_role": proposal.author_role,
        "sequence": proposal.sequence,
        "event_type": event_type,
        "body": body,
    })


class ProposalBroker:
    def __init__(self) -> None:
        self._terminal: set[tuple[str, str, str]] = set()

    def accept(
        self,
        event: CanonicalEvent,
        context: ProposalContext,
        *,
        owner: str,
        fence: int,
        artifact_attestation_digest: str | None = None,
    ) -> NoteProposal | ArtifactProposal | UsageProposal | TerminalProposal:
        if (event.task_id, event.run_id, event.packet_digest) != (
            context.task_id,
            context.run_id,
            context.packet_digest,
        ):
            raise BrokerError("identity_mismatch")
        if owner != context.owner:
            raise BrokerError("owner_mismatch")
        if fence != context.fence:
            raise BrokerError("stale_fence")
        capability = {
            "note.proposed": "notes",
            "artifact.proposed": "artifacts",
            "usage.reported": "usage",
            "run.completed": "structured_output",
            "run.failed": "structured_output",
            "run.needs_human": "structured_output",
        }.get(event.event_type)
        if capability is not None and capability not in context.declared_capabilities:
            raise BrokerError("undeclared_capability", capability)
        if event.event_type == "note.proposed":
            if artifact_attestation_digest is not None:
                raise BrokerError("unexpected_artifact_attestation")
            return self._note(event, context)
        if event.event_type == "artifact.proposed":
            return self._artifact(event, context, artifact_attestation_digest)
        if artifact_attestation_digest is not None:
            raise BrokerError("unexpected_artifact_attestation")
        if event.event_type == "usage.reported":
            return self._usage(event, context)
        if event.event_type in _TERMINAL:
            return self._terminal_proposal(event, context)
        raise BrokerError("unsupported_proposal", event.event_type)

    @staticmethod
    def _note(event: CanonicalEvent, context: ProposalContext) -> NoteProposal:
        payload = event.payload
        if set(payload) != {"note_type", "body", "evidence"}:
            raise BrokerError("note_fields")
        note_type, body, evidence = payload["note_type"], payload["body"], payload["evidence"]
        if context.role not in {"reader", "writer"} or not isinstance(note_type, str) or not note_type:
            raise BrokerError("note_role")
        try:
            validate_note_type(note_type)
        except ProtocolError as exc:
            raise BrokerError("forbidden_note_type") from exc
        _secret_free(note_type, 64)
        if not isinstance(body, str) or body.startswith("#!") or "\ngit push" in body:
            raise BrokerError("executable_note")
        try:
            redacted = _redact(body, context.max_note_bytes)
        except BrokerError as exc:
            if exc.code == "text_too_large":
                raise BrokerError("note_too_large") from exc
            raise
        if not isinstance(evidence, (list, tuple)) or len(evidence) > 64:
            raise BrokerError("evidence")
        safe_evidence = tuple(_allowed_path(item, context, "evidence") for item in evidence)
        values = {"note_type": note_type, "body": redacted, "evidence": safe_evidence}
        return _bounded_proposal(NoteProposal(
            context.task_id,
            context.run_id,
            context.packet_digest,
            context.fence,
            event.sequence,
            context.role,
            note_type,
            redacted,
            safe_evidence,
            _key(event, context, values),
        ))

    @staticmethod
    def _artifact(
        event: CanonicalEvent,
        context: ProposalContext,
        artifact_attestation_digest: str | None,
    ) -> ArtifactProposal:
        payload = event.payload
        if context.role != "writer":
            raise BrokerError("artifact_role")
        required = {"artifact_class", "path", "sha256", "size_bytes", "media_type"}
        if set(payload) != required:
            raise BrokerError("artifact_fields")
        artifact_class = payload["artifact_class"]
        if artifact_class not in context.allowed_artifact_classes:
            raise BrokerError("artifact_class")
        path = _allowed_path(payload["path"], context, "invalid_artifact_path")
        digest = payload["sha256"]
        if not isinstance(digest, str) or not _HEX64.fullmatch(digest):
            raise BrokerError("artifact_digest")
        size = payload["size_bytes"]
        if type(size) is not int or size < 0 or size > context.max_artifact_bytes:
            raise BrokerError("artifact_size")
        media_type = payload["media_type"]
        if not isinstance(media_type, str) or not _MEDIA_TYPE.fullmatch(media_type):
            raise BrokerError("artifact_media_type")
        if (
            not isinstance(artifact_attestation_digest, str)
            or not _HEX64.fullmatch(artifact_attestation_digest)
        ):
            raise BrokerError("artifact_attestation")
        values = {
            **dict(payload),
            "author_role": context.role,
            "artifact_attestation_digest": artifact_attestation_digest,
        }
        return _bounded_proposal(ArtifactProposal(
            context.task_id,
            context.run_id,
            context.packet_digest,
            context.fence,
            event.sequence,
            context.role,
            artifact_class,
            path,
            digest,
            size,
            media_type,
            artifact_attestation_digest,
            _key(event, context, values),
        ))

    @staticmethod
    def _usage(event: CanonicalEvent, context: ProposalContext) -> UsageProposal:
        payload = event.payload
        required = {
            "provider_call_id",
            "price_table_digest",
            "input_tokens",
            "output_tokens",
            "reasoning_tokens",
            "cost_usd_micros",
            "output_bytes",
        }
        if set(payload) != required:
            raise BrokerError("missing_usage")
        if not isinstance(payload["price_table_digest"], str) or not _HEX64.fullmatch(payload["price_table_digest"]):
            raise BrokerError("missing_usage")
        numbers = [payload[name] for name in ("input_tokens", "output_tokens", "reasoning_tokens", "cost_usd_micros", "output_bytes")]
        if any(type(value) is not int or value < 0 for value in numbers):
            raise BrokerError("invalid_usage")
        total = sum(numbers[:3])
        if total > context.max_token_units or numbers[3] > context.max_cost_usd_micros or numbers[4] > context.max_output_bytes:
            raise BrokerError("budget_exceeded")
        provider_call_id = payload["provider_call_id"]
        if not isinstance(provider_call_id, str) or not provider_call_id:
            raise BrokerError("missing_usage")
        _secret_free(provider_call_id, 128)
        values = {**dict(payload), "author_role": context.role}
        return _bounded_proposal(UsageProposal(
            context.task_id,
            context.run_id,
            context.packet_digest,
            context.fence,
            event.sequence,
            context.role,
            provider_call_id,
            payload["price_table_digest"],
            numbers[0],
            numbers[1],
            numbers[2],
            numbers[3],
            numbers[4],
            _key(event, context, values),
        ))

    def _terminal_proposal(self, event: CanonicalEvent, context: ProposalContext) -> TerminalProposal:
        identity = (context.task_id, context.run_id, context.packet_digest)
        if identity in self._terminal:
            raise BrokerError("duplicate_terminal")
        if event.event_type == "run.completed":
            if set(event.payload) != {"summary"}:
                raise BrokerError("terminal_fields")
            summary = event.payload["summary"]
            if not isinstance(summary, str) or not summary:
                raise BrokerError("terminal_fields")
            failure_class = reason = diagnostic = None
        elif event.event_type == "run.failed":
            if set(event.payload) != {"failure_class", "diagnostic"}:
                raise BrokerError("terminal_fields")
            failure_class = event.payload["failure_class"]
            diagnostic = event.payload["diagnostic"]
            if (
                not isinstance(failure_class, str)
                or not isinstance(diagnostic, str)
                or not diagnostic
            ):
                raise BrokerError("terminal_fields")
            try:
                failure_class = FailureClass(failure_class).value
            except ValueError as exc:
                raise BrokerError("failure_class") from exc
            reason = None
            summary = None
        else:
            if set(event.payload) != {"reason", "diagnostic"}:
                raise BrokerError("terminal_fields")
            reason = event.payload["reason"]
            diagnostic = event.payload["diagnostic"]
            if (
                not isinstance(reason, str)
                or not reason
                or not isinstance(diagnostic, str)
                or not diagnostic
            ):
                raise BrokerError("terminal_fields")
            failure_class = None
            summary = None
        try:
            if event.event_type == "run.completed":
                summary = _redact(summary, context.max_note_bytes)
            elif event.event_type == "run.failed":
                diagnostic = _result_text(
                    diagnostic, min(4_096, context.max_note_bytes)
                )
                summary = _redact(
                    f"{failure_class}: {diagnostic}", context.max_note_bytes
                )
            else:
                reason = _result_text(reason, min(4_096, context.max_note_bytes))
                diagnostic = _redact(diagnostic, context.max_note_bytes)
                summary = _redact(f"{reason}: {diagnostic}", context.max_note_bytes)
        except BrokerError as exc:
            if exc.code == "text_too_large":
                raise BrokerError("terminal_too_large") from exc
            raise
        values = {
            "terminal_type": event.event_type,
            "author_role": context.role,
            "summary": summary,
            "failure_class": failure_class,
            "reason": reason,
            "diagnostic": diagnostic,
        }
        proposal = TerminalProposal(
            context.task_id,
            context.run_id,
            context.packet_digest,
            context.fence,
            event.sequence,
            context.role,
            event.event_type,
            summary,
            failure_class,
            reason,
            diagnostic,
            _key(event, context, values),
        )
        self._terminal.add(identity)
        return _bounded_proposal(proposal)
