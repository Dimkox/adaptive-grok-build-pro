from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Protocol


class GitHubError(RuntimeError):
    pass


class Transport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any] | str]: ...


class UrllibTransport:
    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any] | str]:
        raw = json.dumps(body).encode('utf-8') if body is not None else None
        request = urllib.request.Request(url, data=raw, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, _decode_response(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, _decode_response(exc.read())
        except OSError as exc:
            raise GitHubError(f'GitHub request failed: {exc}') from exc


def _decode_response(payload: bytes) -> dict[str, Any] | str:
    if not payload:
        return {}
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return payload.decode('utf-8', errors='replace')
    return value if isinstance(value, dict) else {'value': value}


def branch_protection_payload(
    status_context: str,
    *,
    app_id: int,
    required_reviews: int = 0,
) -> dict[str, Any]:
    if not status_context.strip():
        raise ValueError('status_context is required')
    if isinstance(app_id, bool) or app_id <= 0:
        raise ValueError('app_id must be positive')
    if required_reviews < 0 or required_reviews > 6:
        raise ValueError('required_reviews must be between 0 and 6')
    return {
        'required_status_checks': {
            'strict': True,
            'checks': [{'context': status_context, 'app_id': app_id}],
        },
        'enforce_admins': True,
        'required_pull_request_reviews': {
            'dismiss_stale_reviews': True,
            'require_code_owner_reviews': False,
            'required_approving_review_count': required_reviews,
            'require_last_push_approval': False,
        },
        'restrictions': None,
        'required_linear_history': True,
        'allow_force_pushes': False,
        'allow_deletions': False,
        'block_creations': False,
        'required_conversation_resolution': True,
        'lock_branch': False,
        'allow_fork_syncing': False,
    }


@dataclass
class GitHubClient:
    token: str | None = None
    token_provider: Callable[[], str] | None = None
    transport: Transport | None = None
    api_url: str = 'https://api.github.com'
    api_version: str = '2022-11-28'

    def __post_init__(self) -> None:
        if bool(self.token and self.token.strip()) == bool(self.token_provider):
            raise ValueError('provide exactly one of token or token_provider')
        self.api_url = self.api_url.rstrip('/')
        self.transport = self.transport or UrllibTransport()

    def _access_token(self) -> str:
        value = self.token_provider() if self.token_provider else str(self.token or '')
        value = value.strip()
        if not value:
            raise GitHubError('GitHub access token provider returned an empty token')
        return value

    def _headers(self) -> dict[str, str]:
        return {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {self._access_token()}',
            'Content-Type': 'application/json',
            'User-Agent': 'adaptive-trust-ci/2.1.0',
            'X-GitHub-Api-Version': self.api_version,
        }

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any] | str:
        assert self.transport is not None
        status, payload = self.transport.request(method, f'{self.api_url}{path}', self._headers(), body)
        if status < 200 or status >= 300:
            raise GitHubError(f'GitHub API {method} {path} returned {status}: {payload}')
        return payload

    def post_status(
        self,
        repository: str,
        sha: str,
        *,
        state: str,
        description: str,
        target_url: str,
        context: str,
    ) -> None:
        if state not in {'error', 'failure', 'pending', 'success'}:
            raise ValueError(f'unsupported GitHub status state: {state}')
        self._request(
            'POST',
            f'/repos/{repository}/statuses/{sha}',
            {
                'state': state,
                'target_url': target_url,
                'description': description[:140],
                'context': context,
            },
        )

    def configure_branch_protection(
        self,
        repository: str,
        branch: str,
        *,
        status_context: str,
        app_id: int,
        required_reviews: int = 0,
    ) -> dict[str, Any] | str:
        encoded_branch = urllib.parse.quote(branch, safe='')
        return self._request(
            'PUT',
            f'/repos/{repository}/branches/{encoded_branch}/protection',
            branch_protection_payload(status_context, app_id=app_id, required_reviews=required_reviews),
        )
