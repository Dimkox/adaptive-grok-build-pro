from __future__ import annotations

import base64
import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
except ImportError as exc:  # pragma: no cover - installer prevents this
    raise RuntimeError("cryptography with Ed25519 support is required") from exc


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_private(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def generate_keypair(private_key_path: str | Path, public_key_path: str | Path, key_id: str) -> dict[str, Any]:
    if not key_id.strip():
        raise ValueError("key_id is required")
    private_path = Path(private_key_path).expanduser().resolve()
    public_path = Path(public_key_path).expanduser().resolve()
    if private_path.exists() or public_path.exists():
        raise FileExistsError("refusing to overwrite an existing key")
    key = Ed25519PrivateKey.generate()
    private_bytes = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_bytes = key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    _write_private(private_path, private_bytes)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_text(
        json.dumps({"key_id": key_id, "algorithm": "ed25519", "public_key": base64.b64encode(public_bytes).decode()}, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(public_path, 0o644)
    return {"key_id": key_id, "private_key": str(private_path), "public_key": str(public_path)}


def load_private_key(path: str | Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("private key is not Ed25519")
    return key


def load_allowed_signers(path: str | Path) -> dict[str, Ed25519PublicKey]:
    data = _read_json(path)
    entries = data.get("signers") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise ValueError("allowed signers file must contain a signers list")
    result: dict[str, Ed25519PublicKey] = {}
    for item in entries:
        if not isinstance(item, dict) or item.get("algorithm") != "ed25519":
            raise ValueError("every signer must use ed25519")
        key_id = str(item.get("key_id") or "").strip()
        encoded = str(item.get("public_key") or "").strip()
        if not key_id or key_id in result:
            raise ValueError("signer key_id is missing or duplicated")
        try:
            raw = base64.b64decode(encoded, validate=True)
            result[key_id] = Ed25519PublicKey.from_public_bytes(raw)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"invalid public key for signer {key_id}") from exc
    if not result:
        raise ValueError("at least one signer is required")
    return result


def create_approval_request(
    *,
    job: dict[str, Any],
    scope: str,
    actor: str,
    reason: str,
    ttl_minutes: int = 15,
    issued_at: datetime | None = None,
    nonce: str | None = None,
) -> dict[str, Any]:
    if ttl_minutes < 1 or ttl_minutes > 1440:
        raise ValueError("ttl_minutes must be between 1 and 1440")
    for field in ("id", "repo", "head_sha"):
        if not job.get(field):
            raise ValueError(f"job is missing {field}")
    if len(str(job["head_sha"])) != 40:
        raise ValueError("approval must bind a full head SHA")
    if not scope.strip() or not actor.strip() or not reason.strip():
        raise ValueError("scope, actor, and reason are required")
    current = issued_at or now_utc()
    expires = current + timedelta(minutes=ttl_minutes)
    return {
        "schema_version": 1,
        "approval_id": uuid.uuid4().hex,
        "nonce": nonce or uuid.uuid4().hex,
        "job_id": job["id"],
        "repo": job["repo"],
        "head_sha": job["head_sha"],
        "base_sha": job.get("base_sha"),
        "route_id": job.get("route_id"),
        "change_id": job.get("change_id"),
        "scope": scope.strip(),
        "actor": actor.strip(),
        "reason": reason.strip(),
        "issued_at": current.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "expires_at": expires.astimezone(timezone.utc).isoformat(timespec="seconds"),
    }


def sign_payload(payload: dict[str, Any], private_key_path: str | Path, key_id: str) -> dict[str, Any]:
    if "signature" in payload or "key_id" in payload:
        raise ValueError("payload is already an envelope")
    signature = load_private_key(private_key_path).sign(canonical_json(payload))
    return {
        "payload": payload,
        "key_id": key_id,
        "algorithm": "ed25519",
        "signature": base64.b64encode(signature).decode(),
    }


def verify_approval_envelope(
    envelope: dict[str, Any],
    allowed_signers_path: str | Path,
    *,
    expected_job: dict[str, Any] | None = None,
    at: datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(envelope, dict) or envelope.get("algorithm") != "ed25519":
        raise ValueError("unsupported approval envelope")
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("approval payload is missing")
    key_id = str(envelope.get("key_id") or "")
    key = load_allowed_signers(allowed_signers_path).get(key_id)
    if key is None:
        raise ValueError("approval signer is not trusted")
    try:
        signature = base64.b64decode(str(envelope.get("signature") or ""), validate=True)
        key.verify(signature, canonical_json(payload))
    except (ValueError, InvalidSignature) as exc:
        raise ValueError("approval signature is invalid") from exc
    required = {
        "schema_version", "approval_id", "nonce", "job_id", "repo", "head_sha", "scope",
        "actor", "reason", "issued_at", "expires_at",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError("approval payload fields missing: " + ", ".join(missing))
    if payload.get("schema_version") != 1 or len(str(payload["head_sha"])) != 40:
        raise ValueError("approval schema or head SHA is invalid")
    try:
        issued = datetime.fromisoformat(str(payload["issued_at"]))
        expires = datetime.fromisoformat(str(payload["expires_at"]))
    except ValueError as exc:
        raise ValueError("approval timestamps are invalid") from exc
    if issued.tzinfo is None or expires.tzinfo is None or expires <= issued:
        raise ValueError("approval timestamps must be ordered and timezone-aware")
    moment = at or now_utc()
    if issued > moment + timedelta(minutes=5):
        raise ValueError("approval was issued in the future")
    if expires < moment:
        raise ValueError("approval has expired")
    if expected_job:
        for field in ("job_id", "repo", "head_sha"):
            expected = expected_job["id"] if field == "job_id" else expected_job[field]
            if payload.get(field) != expected:
                raise ValueError(f"approval {field} does not match the durable job")
        for field in ("base_sha", "route_id", "change_id"):
            if payload.get(field) != expected_job.get(field):
                raise ValueError(f"approval {field} does not match the durable job")
    return {
        **payload,
        "key_id": key_id,
        "payload_hash": sha256_json(payload),
        "envelope_json": json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    }


def sign_receipt(payload: dict[str, Any], private_key_path: str | Path | None, key_id: str | None) -> tuple[str | None, str | None]:
    if not private_key_path or not key_id:
        return None, None
    signature = load_private_key(private_key_path).sign(canonical_json(payload))
    return base64.b64encode(signature).decode(), key_id
