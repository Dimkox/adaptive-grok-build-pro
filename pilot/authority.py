"""Literal, exact-operation authority for the two pilot publication effects."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import re
from typing import Callable, Iterable, Mapping

from .contracts import HEX40, HEX64, canonical_json, contract_digest


_HEX16 = re.compile(r"^[0-9a-f]{16}$")
_RESOURCE_KINDS = {
    "branch_push": ("production", "git-push-branch", "git-push-branch"),
    "proposal_create": ("external-write", "external-write", "pull-request-create"),
}


class AuthorityError(RuntimeError):
    pass


@dataclass(frozen=True)
class ControlBinding:
    repository: str
    route_id: str
    change_id: str
    git_head: str
    tree_fingerprint: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repository):
            raise AuthorityError("control_binding")
        if not self.route_id or not self.change_id:
            raise AuthorityError("control_binding")
        if HEX40.fullmatch(self.git_head) is None or HEX64.fullmatch(self.tree_fingerprint) is None:
            raise AuthorityError("control_binding")


@dataclass(frozen=True)
class GrantUseV1:
    schema_version: int
    grant_id: str
    source: str
    scope: str
    action: str
    resource: str
    request_digest: str
    repository: str
    route_id: str
    change_id: str
    git_head: str
    tree_fingerprint: str
    created_at: str
    expires_at: str
    grant_digest: str
    grant_use_digest: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def operation_resource(kind: str, request_digest: str) -> str:
    try:
        suffix = _RESOURCE_KINDS[kind][2]
    except KeyError as exc:
        raise AuthorityError("operation_kind") from exc
    if not isinstance(request_digest, str) or HEX64.fullmatch(request_digest) is None:
        raise AuthorityError("request_digest")
    return f"github-operation/v1/{suffix}/{request_digest}"


class LiteralGrantAuthority:
    """Resolve one exact current grant; never delegates matching to fnmatch."""

    def __init__(
        self,
        binding: ControlBinding,
        grants: Iterable[Mapping[str, object]],
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._binding = binding
        self._grants = tuple(dict(item) for item in grants)
        self._now = now or (lambda: datetime.now(timezone.utc))

    def authorize(self, kind: str, request_digest: str) -> GrantUseV1:
        try:
            scope, action, _resource_kind = _RESOURCE_KINDS[kind]
        except KeyError as exc:
            raise AuthorityError("operation_kind") from exc
        resource = operation_resource(kind, request_digest)
        now = self._now()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise AuthorityError("authority_clock")
        now = now.astimezone(timezone.utc)
        matches: list[tuple[dict[str, object], datetime, datetime]] = []
        for raw in self._grants:
            parsed = self._match(raw, scope=scope, action=action, resource=resource, now=now)
            if parsed is not None:
                matches.append((raw, *parsed))
        if not matches:
            raise AuthorityError("grant_unavailable")
        if len(matches) != 1:
            raise AuthorityError("grant_ambiguous")
        grant, created, expires = matches[0]
        grant_digest = contract_digest("delegated-grant", _canonical_grant(grant))
        facts = {
            "schema_version": 1,
            "grant_id": str(grant["id"]),
            "source": str(grant["source"]),
            "scope": scope,
            "action": action,
            "resource": resource,
            "request_digest": request_digest,
            "repository": self._binding.repository,
            "route_id": self._binding.route_id,
            "change_id": self._binding.change_id,
            "git_head": self._binding.git_head,
            "tree_fingerprint": self._binding.tree_fingerprint,
            "created_at": created.isoformat(timespec="seconds"),
            "expires_at": expires.isoformat(timespec="seconds"),
            "grant_digest": grant_digest,
        }
        use_digest = contract_digest("grant-use", facts)
        return GrantUseV1(**facts, grant_use_digest=use_digest)

    def _match(
        self,
        grant: Mapping[str, object],
        *,
        scope: str,
        action: str,
        resource: str,
        now: datetime,
    ) -> tuple[datetime, datetime] | None:
        required = {
            "schema_version": 2,
            "authorization": "delegated-local-grant",
            "scope": scope,
            "repository": self._binding.repository,
            "route_id": self._binding.route_id,
            "change_id": self._binding.change_id,
            "git_head": self._binding.git_head,
            "tree_fingerprint": self._binding.tree_fingerprint,
        }
        if any(grant.get(key) != value for key, value in required.items()):
            return None
        if grant.get("source") not in {"explicit-user-consent", "standing-user-consent"}:
            return None
        if _HEX16.fullmatch(str(grant.get("id", ""))) is None:
            return None
        if grant.get("actions") != [action] or grant.get("resources") != [resource]:
            return None
        if any(character in resource for character in "*?[]"):
            return None
        try:
            created = datetime.fromisoformat(str(grant["created_at"]))
            expires = datetime.fromisoformat(str(grant["expires_at"]))
        except (KeyError, TypeError, ValueError):
            return None
        if created.tzinfo is None or expires.tzinfo is None:
            return None
        created = created.astimezone(timezone.utc)
        expires = expires.astimezone(timezone.utc)
        if created > now or expires <= now or expires <= created:
            return None
        return created, expires


def _canonical_grant(grant: Mapping[str, object]) -> dict[str, object]:
    try:
        encoded = canonical_json(dict(grant))
    except Exception as exc:
        raise AuthorityError("grant_record") from exc
    if len(encoded) > 16_384:
        raise AuthorityError("grant_record")
    return dict(grant)
