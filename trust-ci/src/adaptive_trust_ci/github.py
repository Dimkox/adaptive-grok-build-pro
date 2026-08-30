from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Protocol


class GitHubError(RuntimeError):
    pass


class GitHubTransportError(GitHubError):
    pass


class Transport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any] | str] | tuple[int, dict[str, Any] | str, Mapping[str, str]]: ...


class UrllibTransport:
    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any] | str, Mapping[str, str]]:
        raw = json.dumps(body).encode('utf-8') if body is not None else None
        request = urllib.request.Request(url, data=raw, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, _decode_response(response.read()), dict(response.headers.items())
        except urllib.error.HTTPError as exc:
            return exc.code, _decode_response(exc.read()), dict(exc.headers.items())
        except OSError as exc:
            raise GitHubTransportError(f'GitHub request failed: {exc}') from exc


def unpack_transport_response(response):
    if not isinstance(response, tuple) or len(response) not in (2, 3):
        raise GitHubTransportError('GitHub transport returned a malformed response')
    status, payload = response[:2]
    headers = response[2] if len(response) == 3 else {}
    if type(status) is not int or not isinstance(headers, Mapping):
        raise GitHubTransportError('GitHub transport returned a malformed response')
    return status, payload, {str(key).lower(): str(value) for key, value in headers.items()}


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
    status_context = check_name.strip()
    if not status_context:
        raise ValueError('check_name is required')
    if isinstance(app_id, bool) or app_id <= 0:
        raise ValueError('app_id must be positive')
    if isinstance(required_reviews, bool) or not 0 <= required_reviews <= 6:
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


def branch_protection_payload_for_checks(
    checks: tuple[tuple[str, int], ...], *, required_reviews: int = 0
) -> dict[str, Any]:
    if not checks:
        raise ValueError('at least one App-bound required check is required')
    normalized = []
    seen = set()
    for context, app_id in checks:
        context = context.strip()
        if not context or isinstance(app_id, bool) or app_id <= 0:
            raise ValueError('each required check needs a context and positive app_id')
        pair = (context, app_id)
        if pair in seen:
            raise ValueError('required checks must be unique')
        seen.add(pair)
        normalized.append({'context': context, 'app_id': app_id})
    if isinstance(required_reviews, bool) or not 0 <= required_reviews <= 6:
        raise ValueError('required_reviews must be between 0 and 6')
    return {
        'required_status_checks': {
            'strict': True,
            'checks': normalized,
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
        status, payload, _headers = unpack_transport_response(
            self.transport.request(method, f'{self.api_url}{path}', self._headers(), body)
        )
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

    def cutover_branch_protection(
        self,
        repository: str,
        branch: str,
        *,
        old_check_name: str,
        old_app_id: int,
        new_check_name: str,
        new_app_id: int,
        required_reviews: int = 0,
    ) -> dict[str, Any] | str:
        """Replace an App-bound epoch check without an unprotected interval."""
        old = (old_check_name.strip(), old_app_id)
        new = (new_check_name.strip(), new_app_id)
        if old == new:
            raise ValueError('old and new required checks must differ')
        encoded_branch = urllib.parse.quote(branch, safe='')
        path = f'/repos/{repository}/branches/{encoded_branch}/protection'
        current = self._request('GET', path)
        self._verify_required_checks(current, (old,))
        intermediate = (old, new)
        try:
            self._request(
                'PUT', path,
                branch_protection_payload_for_checks(
                    intermediate, required_reviews=required_reviews
                ),
            )
            self._verify_required_checks(self._request('GET', path), intermediate)
            result = self._request(
                'PUT', path,
                branch_protection_payload_for_checks((new,), required_reviews=required_reviews),
            )
            self._verify_required_checks(self._request('GET', path), (new,))
            return result
        except Exception as exc:
            try:
                self._request(
                    'PUT', path,
                    branch_protection_payload_for_checks(
                        intermediate, required_reviews=required_reviews
                    ),
                )
                self._verify_required_checks(self._request('GET', path), intermediate)
            except Exception as rollback_exc:
                raise GitHubError(
                    f'branch protection cutover failed and rollback could not be verified: {rollback_exc}'
                ) from exc
            raise GitHubError('branch protection cutover failed and was rolled back to both trusted checks') from exc

    @staticmethod
    def _verify_required_checks(
        protection: dict[str, Any] | str, expected: tuple[tuple[str, int], ...]
    ) -> None:
        if not isinstance(protection, dict):
            raise GitHubError('branch protection response is not an object')
        required = protection.get('required_status_checks')
        checks = required.get('checks') if isinstance(required, dict) else None
        if not isinstance(required, dict) or required.get('strict') is not True or not isinstance(checks, list):
            raise GitHubError('branch protection does not expose strict App-bound checks')
        actual = []
        for check in checks:
            if not isinstance(check, dict) or type(check.get('context')) is not str or type(check.get('app_id')) is not int:
                raise GitHubError('branch protection contains a malformed required check')
            actual.append((check['context'], check['app_id']))
        if set(actual) != set(expected) or len(actual) != len(expected):
            raise GitHubError(f'branch protection verification mismatch: expected={expected!r} actual={actual!r}')
