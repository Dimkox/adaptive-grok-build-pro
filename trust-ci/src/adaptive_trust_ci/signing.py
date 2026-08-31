from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .models import (
    ApprovalEnvelope,
    ApprovalPayload,
    AttestationEnvelope,
    AttestationPayload,
    canonical_json,
    parse_datetime,
    require_digest,
    require_sha,
)


class ApprovalError(ValueError):
    pass


@dataclass(frozen=True)
class Signer:
    _private_key: Ed25519PrivateKey

    @classmethod
    def generate(cls) -> 'Signer':
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def from_private_pem(cls, data: bytes) -> 'Signer':
        try:
            key = serialization.load_pem_private_key(data, password=None)
        except (TypeError, ValueError) as exc:
            raise ApprovalError('invalid private key PEM') from exc
        if not isinstance(key, Ed25519PrivateKey):
            raise ApprovalError('private key must be Ed25519')
        return cls(key)

    @classmethod
    def from_private_file(cls, path: Path) -> 'Signer':
        try:
            return cls.from_private_pem(path.read_bytes())
        except OSError as exc:
            raise ApprovalError(f'cannot read private key: {path}') from exc

    @property
    def key_id(self) -> str:
        raw = self._private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        return hashlib.sha256(raw).hexdigest()[:16]

    def private_key_pem(self) -> bytes:
        return self._private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )

    def public_key_pem(self) -> bytes:
        return self._private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def sign(self, payload: Mapping[str, Any]) -> str:
        return base64.b64encode(self._private_key.sign(canonical_json(payload))).decode('ascii')

    def write_keypair(self, private_path: Path, public_path: Path) -> None:
        if private_path.exists() or public_path.exists():
            raise ApprovalError('refusing to overwrite an existing key file')
        private_path.parent.mkdir(parents=True, exist_ok=True)
        public_path.parent.mkdir(parents=True, exist_ok=True)
        private_path.write_bytes(self.private_key_pem())
        os.chmod(private_path, 0o600)
        public_path.write_bytes(self.public_key_pem())
        os.chmod(public_path, 0o644)


@dataclass(frozen=True)
class TrustedKey:
    key_id: str
    actor: str
    public_key: Ed25519PublicKey
    scopes: frozenset[str]
    not_before: datetime | None = None
    not_after: datetime | None = None
    revoked_at: datetime | None = None

    def validate_for_approval(self, *, issued_at: datetime, current: datetime) -> None:
        issued = issued_at.astimezone(timezone.utc)
        now = current.astimezone(timezone.utc)
        if self.revoked_at is not None and now >= self.revoked_at:
            raise ApprovalError(f'approval key {self.key_id} is revoked')
        if self.not_before is not None and (issued < self.not_before or now < self.not_before):
            raise ApprovalError(f'approval key {self.key_id} is not valid yet')
        if self.not_after is not None and (issued >= self.not_after or now >= self.not_after):
            raise ApprovalError(f'approval key {self.key_id} is expired')

    def status(self, now: datetime) -> str:
        current = now.astimezone(timezone.utc)
        if self.revoked_at is not None and current >= self.revoked_at:
            return 'revoked'
        if self.not_before is not None and current < self.not_before:
            return 'not-yet-valid'
        if self.not_after is not None and current >= self.not_after:
            return 'expired'
        return 'active'


@dataclass(frozen=True)
class TrustStore:
    keys: dict[str, TrustedKey]
    schema_version: int = 1

    @classmethod
    def load(cls, path: Path) -> 'TrustStore':
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise ApprovalError(f'cannot load trust store {path}: {exc}') from exc
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> 'TrustStore':
        schema_version = data.get('schema_version')
        if schema_version not in {1, 2} or not isinstance(data.get('keys'), list):
            raise ApprovalError('invalid trust store')
        parsed: dict[str, TrustedKey] = {}
        for item in data['keys']:
            if not isinstance(item, Mapping):
                raise ApprovalError('trust-store key must be an object')
            key_id = str(item.get('key_id', '')).strip()
            actor = str(item.get('actor', '')).strip()
            scopes_raw = item.get('scopes')
            pem = str(item.get('public_key_pem', '')).encode('utf-8')
            if not key_id or not actor or not isinstance(scopes_raw, list) or not scopes_raw:
                raise ApprovalError('trust-store key identity and scopes are required')
            try:
                public_key = serialization.load_pem_public_key(pem)
            except (TypeError, ValueError) as exc:
                raise ApprovalError(f'invalid public key for {key_id}') from exc
            if not isinstance(public_key, Ed25519PublicKey):
                raise ApprovalError('public key must be Ed25519')
            raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
            actual_id = hashlib.sha256(raw).hexdigest()[:16]
            if actual_id != key_id:
                raise ApprovalError(f'key_id mismatch for actor {actor}')
            if key_id in parsed:
                raise ApprovalError(f'duplicate key_id: {key_id}')
            scopes = frozenset(str(scope).strip() for scope in scopes_raw if str(scope).strip())
            if not scopes:
                raise ApprovalError(f'trusted key {key_id} has no valid scopes')
            not_before = _optional_time(item.get('not_before'), 'not_before') if schema_version == 2 else None
            not_after = _optional_time(item.get('not_after'), 'not_after') if schema_version == 2 else None
            revoked_at = _optional_time(item.get('revoked_at'), 'revoked_at') if schema_version == 2 else None
            if not_before is not None and not_after is not None and not_after <= not_before:
                raise ApprovalError(f'trusted key {key_id} not_after must be after not_before')
            parsed[key_id] = TrustedKey(
                key_id=key_id,
                actor=actor,
                public_key=public_key,
                scopes=scopes,
                not_before=not_before,
                not_after=not_after,
                revoked_at=revoked_at,
            )
        if not parsed:
            raise ApprovalError('trust store must contain at least one key')
        return cls(parsed, schema_version=int(schema_version))

    def report(self, now: datetime) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'keys': [
                {
                    'key_id': key.key_id,
                    'actor': key.actor,
                    'scopes': sorted(key.scopes),
                    'status': key.status(now),
                    'not_before': key.not_before.isoformat() if key.not_before else None,
                    'not_after': key.not_after.isoformat() if key.not_after else None,
                    'revoked_at': key.revoked_at.isoformat() if key.revoked_at else None,
                }
                for key in sorted(self.keys.values(), key=lambda item: (item.actor, item.key_id))
            ],
        }


def sign_approval(payload: ApprovalPayload, signer: Signer) -> ApprovalEnvelope:
    if payload.key_id != signer.key_id:
        raise ApprovalError('approval payload key_id does not match signer')
    return ApprovalEnvelope(payload=payload, signature=signer.sign(payload.to_dict()))


def verify_approval(
    envelope: ApprovalEnvelope | Mapping[str, Any],
    trust_store: TrustStore,
    *,
    expected_repository: str,
    expected_pr_number: int,
    expected_base_sha: str,
    expected_head_sha: str,
    expected_policy_digest: str,
    now: datetime,
    max_ttl_seconds: int,
) -> ApprovalPayload:
    try:
        parsed = envelope if isinstance(envelope, ApprovalEnvelope) else ApprovalEnvelope.from_dict(envelope)
    except ValueError as exc:
        raise ApprovalError(str(exc)) from exc
    payload = parsed.payload
    trusted = trust_store.keys.get(payload.key_id)
    if trusted is None:
        raise ApprovalError('approval key is not trusted')
    if payload.actor != trusted.actor:
        raise ApprovalError('approval actor does not match trusted key')
    if payload.scope not in trusted.scopes:
        raise ApprovalError('approval scope is not authorized for this key')
    if payload.repository != expected_repository:
        raise ApprovalError('approval repository mismatch')
    if payload.pr_number != expected_pr_number:
        raise ApprovalError('approval pull request mismatch')
    try:
        expected_base = require_sha(expected_base_sha, 'expected_base_sha')
        expected_head = require_sha(expected_head_sha, 'expected_head_sha')
        expected_policy = require_digest(expected_policy_digest, 'expected_policy_digest')
    except ValueError as exc:
        raise ApprovalError(str(exc)) from exc
    if payload.base_sha != expected_base:
        raise ApprovalError('approval base SHA mismatch')
    if payload.head_sha != expected_head:
        raise ApprovalError('approval head SHA mismatch')
    if payload.policy_digest != expected_policy:
        raise ApprovalError('approval policy digest mismatch')
    issued = parse_datetime(payload.issued_at)
    expires = parse_datetime(payload.expires_at)
    current = now.astimezone(timezone.utc)
    trusted.validate_for_approval(issued_at=issued, current=current)
    if (expires - issued).total_seconds() > max_ttl_seconds:
        raise ApprovalError('approval TTL exceeds policy')
    if current < issued:
        raise ApprovalError('approval is not valid yet')
    if current >= expires:
        raise ApprovalError('approval has expired')
    try:
        signature = base64.b64decode(parsed.signature, validate=True)
        trusted.public_key.verify(signature, canonical_json(payload.to_dict()))
    except (ValueError, InvalidSignature) as exc:
        raise ApprovalError('invalid approval signature') from exc
    return payload


def sign_attestation(payload: AttestationPayload, signer: Signer) -> AttestationEnvelope:
    if payload.key_id != signer.key_id:
        raise ApprovalError('attestation payload key_id does not match signer')
    return AttestationEnvelope(payload=payload, signature=signer.sign(payload.to_dict()))


def verify_attestation(
    envelope: AttestationEnvelope | Mapping[str, Any],
    public_key_pem: bytes,
) -> AttestationPayload:
    try:
        parsed = envelope if isinstance(envelope, AttestationEnvelope) else AttestationEnvelope.from_dict(envelope)
        public_key = serialization.load_pem_public_key(public_key_pem)
    except (ValueError, TypeError) as exc:
        raise ApprovalError('invalid attestation envelope or public key') from exc
    if not isinstance(public_key, Ed25519PublicKey):
        raise ApprovalError('attestation public key must be Ed25519')
    raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    key_id = hashlib.sha256(raw).hexdigest()[:16]
    if parsed.payload.key_id != key_id:
        raise ApprovalError('attestation key_id mismatch')
    try:
        signed_payload = parsed._signed_payload if parsed._signed_payload is not None else parsed.payload.to_dict()
        public_key.verify(
            base64.b64decode(parsed.signature, validate=True),
            canonical_json(signed_payload),
        )
    except (ValueError, InvalidSignature) as exc:
        raise ApprovalError('invalid attestation signature') from exc
    return parsed.payload


def _optional_time(value: Any, field_name: str) -> datetime | None:
    if value in {None, ''}:
        return None
    try:
        return parse_datetime(str(value))
    except ValueError as exc:
        raise ApprovalError(f'invalid {field_name}: {value!r}') from exc
