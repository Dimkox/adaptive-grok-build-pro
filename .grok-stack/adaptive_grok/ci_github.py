from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class GitHubAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class BranchPolicy:
    status_context: str
    required_reviews: int = 0

    def protection_payload(self) -> dict[str, Any]:
        if self.required_reviews < 0:
            raise ValueError("required_reviews cannot be negative")
        reviews: dict[str, Any] | None = None
        if self.required_reviews:
            reviews = {
                "dismiss_stale_reviews": True,
                "require_code_owner_reviews": True,
                "required_approving_review_count": self.required_reviews,
                "require_last_push_approval": False,
            }
        return {
            "required_status_checks": {"strict": True, "contexts": [self.status_context]},
            "enforce_admins": True,
            "required_pull_request_reviews": reviews,
            "restrictions": None,
            "required_linear_history": True,
            "allow_force_pushes": False,
            "allow_deletions": False,
            "block_creations": False,
            "required_conversation_resolution": True,
            "lock_branch": False,
            "allow_fork_syncing": False,
        }


class GitHubClient:
    def __init__(self, token: str, api_url: str = "https://api.github.com", timeout: int = 30) -> None:
        if not token.strip():
            raise ValueError("GitHub token is required")
        self.token = token.strip()
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = self.api_url + path
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "adaptive-grok-self-hosted-ci",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:2000]
            raise GitHubAPIError(f"GitHub {method} {path} failed: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise GitHubAPIError(f"GitHub {method} {path} failed: {exc.reason}") from exc
        return json.loads(body) if body else None

    @staticmethod
    def _repo(repo: str) -> str:
        if repo.count("/") != 1:
            raise ValueError("repository must be owner/name")
        return "/".join(urllib.parse.quote(part, safe="") for part in repo.split("/"))

    def set_commit_status(
        self,
        repo: str,
        sha: str,
        state: str,
        context: str,
        description: str,
        target_url: str | None = None,
    ) -> Any:
        if state not in {"error", "failure", "pending", "success"} or len(sha) != 40:
            raise ValueError("invalid commit status")
        payload: dict[str, Any] = {"state": state, "context": context, "description": description[:140]}
        if target_url:
            payload["target_url"] = target_url
        return self.request("POST", f"/repos/{self._repo(repo)}/statuses/{sha}", payload)

    def get_branch_protection(self, repo: str, branch: str) -> dict[str, Any] | None:
        path = f"/repos/{self._repo(repo)}/branches/{urllib.parse.quote(branch, safe='')}/protection"
        try:
            data = self.request("GET", path)
        except GitHubAPIError as exc:
            if " 404 " in str(exc):
                return None
            raise
        return data if isinstance(data, dict) else None

    def apply_branch_protection(self, repo: str, branch: str, policy: BranchPolicy) -> Any:
        path = f"/repos/{self._repo(repo)}/branches/{urllib.parse.quote(branch, safe='')}/protection"
        return self.request("PUT", path, policy.protection_payload())


def branch_protection_gaps(current: dict[str, Any] | None, policy: BranchPolicy) -> list[str]:
    if not current:
        return ["branch protection is not configured"]
    gaps: list[str] = []
    checks = current.get("required_status_checks") or {}
    contexts = checks.get("contexts") or []
    checks_list = checks.get("checks") or []
    names = set(str(item) for item in contexts)
    names.update(str(item.get("context")) for item in checks_list if isinstance(item, dict))
    if policy.status_context not in names:
        gaps.append(f"required status is missing: {policy.status_context}")
    if not checks.get("strict"):
        gaps.append("required status checks are not strict")
    if not (current.get("enforce_admins") or {}).get("enabled"):
        gaps.append("administrators are not protected")
    if not (current.get("required_linear_history") or {}).get("enabled"):
        gaps.append("linear history is not required")
    if (current.get("allow_force_pushes") or {}).get("enabled"):
        gaps.append("force pushes are allowed")
    if (current.get("allow_deletions") or {}).get("enabled"):
        gaps.append("branch deletion is allowed")
    if not (current.get("required_conversation_resolution") or {}).get("enabled"):
        gaps.append("conversation resolution is not required")
    reviews = current.get("required_pull_request_reviews")
    count = int((reviews or {}).get("required_approving_review_count") or 0)
    if count < policy.required_reviews:
        gaps.append(f"required approving reviews is {count}, expected at least {policy.required_reviews}")
    return gaps
