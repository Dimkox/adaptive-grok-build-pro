from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
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
    check_name: str,
    *,
    app_id: int,
    required_reviews: int = 0,
) -> dict[str, Any]:
    normalized_name = check_name.strip()
    if not normalized_name:
        raise ValueError('check_name is required')
    if isinstance(app_id, bool) or app_id <= 0:
        raise ValueError('app_id must be positive')
    if isinstance(required_reviews, bool) or not 0 <= required_reviews <= 6:
        raise ValueError('required_reviews must be between 0 and 6')
    return {
        'required_status_checks': {
            'strict': True,
            'checks': [{'context': normalized_name, 'app_id': app_id}],
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
    api_version: str = '2026-03-10'

    def __post_init__(self) -> None:
        has_token = bool(self.token and self.token.strip())
        has_provider = self.token_provider is not None
        if has_token == has_provider:
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

    def ensure_check_run(
        self,
        repository: str,
        sha: str,
        *,
        name: str,
        external_id: str,
        details_url: str,
        started_at: datetime,
    ) -> int:
        """Create one App-owned Check Run per durable job, or reuse it after retry."""
        encoded_name = urllib.parse.quote(name, safe='')
        existing = self._request(
            'GET',
            f'/repos/{repository}/commits/{sha}/check-runs?check_name={encoded_name}&filter=latest&per_page=100',
        )
        if isinstance(existing, dict):
            runs = existing.get('check_runs')
            if isinstance(runs, list):
                for run in runs:
                    if (
                        isinstance(run, dict)
                        and run.get('external_id') == external_id
                        and isinstance(run.get('id'), int)
                    ):
                        check_run_id = int(run['id'])
                        self._request(
                            'PATCH',
                            f'/repos/{repository}/check-runs/{check_run_id}',
                            {
                                'status': 'in_progress',
                                'details_url': details_url,
                                'started_at': started_at.astimezone(timezone.utc).isoformat(),
                                'output': {
                                    'title': 'Adaptive Trust CI verification in progress',
                                    'summary': f'durable_job={external_id}',
                                },
                            },
                        )
                        return check_run_id
        created = self._request(
            'POST',
            f'/repos/{repository}/check-runs',
            {
                'name': name,
                'head_sha': sha,
                'status': 'in_progress',
                'external_id': external_id,
                'details_url': details_url,
                'started_at': started_at.astimezone(timezone.utc).isoformat(),
            },
        )
        if not isinstance(created, dict) or not isinstance(created.get('id'), int):
            raise GitHubError('check-run creation response has no numeric id')
        return int(created['id'])

    def complete_check_run(
        self,
        repository: str,
        check_run_id: int,
        *,
        conclusion: str,
        title: str,
        summary: str,
        completed_at: datetime,
    ) -> None:
        if conclusion not in {'success', 'failure', 'cancelled', 'timed_out', 'action_required', 'neutral'}:
            raise ValueError(f'unsupported check conclusion: {conclusion}')
        self._request(
            'PATCH',
            f'/repos/{repository}/check-runs/{check_run_id}',
            {
                'status': 'completed',
                'conclusion': conclusion,
                'completed_at': completed_at.astimezone(timezone.utc).isoformat(),
                'output': {
                    'title': title[:255],
                    'summary': summary[:65535],
                },
            },
        )

    def configure_branch_protection(
        self,
        repository: str,
        branch: str,
        *,
        check_name: str,
        app_id: int,
        required_reviews: int = 0,
    ) -> dict[str, Any] | str:
        encoded_branch = urllib.parse.quote(branch, safe='')
        return self._request(
            'PUT',
            f'/repos/{repository}/branches/{encoded_branch}/protection',
            branch_protection_payload(check_name, app_id=app_id, required_reviews=required_reviews),
        )
