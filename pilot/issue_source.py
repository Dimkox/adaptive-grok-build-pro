"""Read one pinned GitHub issue through a transport owned by the operator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

from .contracts import ContractError, IssueSnapshotV1
from .profile import PilotProfileV1


@dataclass(frozen=True)
class IssueObservation:
    repository_full_name: str
    repository_node_id: str
    issue_number: int
    issue_node_id: str
    state: str
    updated_at: str
    author_login: str
    author_association: str
    title: str
    body: str
    is_pull_request: bool


@dataclass(frozen=True)
class BaseObservation:
    sha: str
    tree: str


class IssueTransport(Protocol):
    def fetch_issue(self, repository: str, issue_number: int) -> IssueObservation: ...

    def fetch_ref(self, repository: str, base_ref: str) -> BaseObservation: ...


def issue_observation_from_github(value: Mapping[str, Any]) -> IssueObservation:
    """Reduce GitHub JSON to the closed, non-routing issue facts."""
    try:
        author = value["author"]
        if not isinstance(author, Mapping):
            raise TypeError
        return IssueObservation(
            repository_full_name=str(value["repository_full_name"]),
            repository_node_id=str(value["repository_node_id"]),
            issue_number=int(value["number"]),
            issue_node_id=str(value["node_id"]),
            state=str(value["state"]),
            updated_at=str(value["updated_at"]),
            author_login=str(author["login"]),
            author_association=str(value["author_association"]),
            title=str(value["title"]),
            body=str(value.get("body") or ""),
            is_pull_request=bool(value.get("pull_request")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("invalid_issue_observation") from exc


class IssueSource:
    def __init__(
        self,
        profile: PilotProfileV1,
        transport: IssueTransport,
        *,
        source_adapter_digest: str,
        auth_principal_digest: str,
        clock=None,
    ) -> None:
        self._profile = profile
        self._transport = transport
        self._source_adapter_digest = source_adapter_digest
        self._auth_principal_digest = auth_principal_digest
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def snapshot(
        self,
        *,
        job_id: str,
        issue_number: int,
        acceptance_ids: tuple[str, ...],
    ) -> IssueSnapshotV1:
        profile = self._profile
        issue = self._transport.fetch_issue(profile.github_name, issue_number)
        base = self._transport.fetch_ref(profile.github_name, profile.base_ref)
        if issue.issue_number != issue_number:
            raise ContractError("target_mismatch", "issue_number")
        if issue.repository_full_name != profile.github_name or issue.is_pull_request:
            raise ContractError("target_mismatch", "issue_repository")
        if issue.state != "open":
            raise ContractError("target_mismatch", "issue_state")
        if (base.sha, base.tree) != (profile.base_sha, profile.base_tree):
            raise ContractError("stale_input", "base")
        now = self._clock()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ContractError("invalid_time", "clock")
        fetched_at = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return IssueSnapshotV1.from_facts(
            {
                "schema_version": 1,
                "job_id": job_id,
                "profile_digest": profile.profile_digest,
                "repository_id": profile.repository_id,
                "repository_node_id": issue.repository_node_id,
                "issue_number": issue.issue_number,
                "issue_node_id": issue.issue_node_id,
                "state": issue.state,
                "updated_at": issue.updated_at,
                "author_login": issue.author_login,
                "author_association": issue.author_association,
                "title": issue.title,
                "body": issue.body,
                "base_ref": profile.base_ref,
                "base_sha": base.sha,
                "base_tree": base.tree,
                "acceptance_ids": list(acceptance_ids),
                "source_adapter_digest": self._source_adapter_digest,
                "auth_principal_digest": self._auth_principal_digest,
                "fetched_at": fetched_at,
            }
        )
