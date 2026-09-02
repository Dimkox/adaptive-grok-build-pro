from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re
from typing import Any, Mapping

from .contracts import canonical_digest
from .models import FailureClass
from .protocol import CanonicalEvent


_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_MEDIA_TYPE = re.compile(r"^[a-z0-9.+-]+/[a-z0-9.+-]+$")
_SECRET = re.compile(r"(?i)(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]+|-----BEGIN [A-Z ]*PRIVATE KEY-----")
_TERMINAL = frozenset({"run.completed", "run.failed", "run.needs_human"})


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
    artifact_class: str
    path: str
    sha256: str
    size_bytes: int
    media_type: str
    idempotency_key: str


@dataclass(frozen=True)
class UsageProposal:
    task_id: str
    run_id: str
    packet_digest: str
    fence: int
    sequence: int
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
    terminal_type: str
    summary: str
    failure_class: str | None
    reason: str | None
    diagnostic: str | None
    idempotency_key: str


def _redact(value: str) -> str:
    return _SECRET.sub("[REDACTED]", value)


def _safe_path(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise BrokerError(code)
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or ".git" in path.parts or str(path) != value:
        raise BrokerError(code)
    return value


def _key(event: CanonicalEvent, context: ProposalContext, body: Mapping[str, Any]) -> str:
    return canonical_digest(
        {
            "contract": "adaptive-factory.execution-proposal/v1",
            "task_id": context.task_id,
            "run_id": context.run_id,
            "packet_digest": context.packet_digest,
            "fence": context.fence,
            "sequence": event.sequence,
            "event_type": event.event_type,
            "body": dict(body),
        }
    )


class ProposalBroker:
    def __init__(self) -> None:
        self._terminal: set[tuple[str, str, str]] = set()

    def accept(
        self, event: CanonicalEvent, context: ProposalContext, *, owner: str, fence: int
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
            return self._note(event, context)
        if event.event_type == "artifact.proposed":
            return self._artifact(event, context)
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
        if not isinstance(body, str) or body.startswith("#!") or "\ngit push" in body:
            raise BrokerError("executable_note")
        redacted = _redact(body)
        if len(redacted.encode("utf-8")) > context.max_note_bytes:
            raise BrokerError("note_too_large")
        if not isinstance(evidence, (list, tuple)) or len(evidence) > 64:
            raise BrokerError("evidence")
        safe_evidence = tuple(_safe_path(item, "evidence") for item in evidence)
        values = {"note_type": note_type, "body": redacted, "evidence": safe_evidence}
        return NoteProposal(
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
        )

    @staticmethod
    def _artifact(event: CanonicalEvent, context: ProposalContext) -> ArtifactProposal:
        payload = event.payload
        required = {"artifact_class", "path", "sha256", "size_bytes", "media_type"}
        if set(payload) != required:
            raise BrokerError("artifact_fields")
        artifact_class = payload["artifact_class"]
        if artifact_class not in context.allowed_artifact_classes:
            raise BrokerError("artifact_class")
        path = _safe_path(payload["path"], "invalid_artifact_path")
        digest = payload["sha256"]
        if not isinstance(digest, str) or not _HEX64.fullmatch(digest):
            raise BrokerError("artifact_digest")
        size = payload["size_bytes"]
        if type(size) is not int or size < 0 or size > context.max_artifact_bytes:
            raise BrokerError("artifact_size")
        media_type = payload["media_type"]
        if not isinstance(media_type, str) or not _MEDIA_TYPE.fullmatch(media_type):
            raise BrokerError("artifact_media_type")
        values = dict(payload)
        return ArtifactProposal(
            context.task_id,
            context.run_id,
            context.packet_digest,
            context.fence,
            event.sequence,
            artifact_class,
            path,
            digest,
            size,
            media_type,
            _key(event, context, values),
        )

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
        values = dict(payload)
        return UsageProposal(
            context.task_id,
            context.run_id,
            context.packet_digest,
            context.fence,
            event.sequence,
            provider_call_id,
            payload["price_table_digest"],
            numbers[0],
            numbers[1],
            numbers[2],
            numbers[3],
            numbers[4],
            _key(event, context, values),
        )

    def _terminal_proposal(self, event: CanonicalEvent, context: ProposalContext) -> TerminalProposal:
        identity = (context.task_id, context.run_id, context.packet_digest)
        if identity in self._terminal:
            raise BrokerError("duplicate_terminal")
        if event.event_type == "run.completed":
            if set(event.payload) != {"summary"}:
                raise BrokerError("terminal_fields")
            summary = event.payload["summary"]
            failure_class = reason = diagnostic = None
        elif event.event_type == "run.failed":
            if set(event.payload) != {"failure_class", "diagnostic"}:
                raise BrokerError("terminal_fields")
            failure_class = event.payload["failure_class"]
            diagnostic = event.payload["diagnostic"]
            if not isinstance(failure_class, str) or not isinstance(diagnostic, str):
                raise BrokerError("terminal_fields")
            try:
                failure_class = FailureClass(failure_class).value
            except ValueError as exc:
                raise BrokerError("failure_class") from exc
            reason = None
            summary = f"{failure_class}: {diagnostic}"
        else:
            if set(event.payload) != {"reason", "diagnostic"}:
                raise BrokerError("terminal_fields")
            reason = event.payload["reason"]
            diagnostic = event.payload["diagnostic"]
            if not isinstance(reason, str) or not isinstance(diagnostic, str):
                raise BrokerError("terminal_fields")
            failure_class = None
            summary = f"{reason}: {diagnostic}"
        if not isinstance(summary, str):
            raise BrokerError("terminal_fields")
        summary = _redact(summary)
        if len(summary.encode("utf-8")) > context.max_note_bytes:
            raise BrokerError("terminal_too_large")
        reason = _redact(reason) if reason is not None else None
        diagnostic = _redact(diagnostic) if diagnostic is not None else None
        values = {
            "terminal_type": event.event_type,
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
            event.event_type,
            summary,
            failure_class,
            reason,
            diagnostic,
            _key(event, context, values),
        )
        self._terminal.add(identity)
        return proposal
