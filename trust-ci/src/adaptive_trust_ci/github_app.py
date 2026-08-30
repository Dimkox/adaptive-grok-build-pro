from __future__ import annotations

import base64
import threading
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .github import (
    GitHubClient,
    GitHubError,
    GitHubTransportError,
    Transport,
    UrllibTransport,
    unpack_transport_response,
)
from .models import canonical_json, parse_datetime, utc_now
from .provenance import CorroboratedMerge, MergedPullRequestFact, ProvenanceMismatch


class RetryableGitHubError(GitHubError):
    def __init__(self, message: str, *, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class IncompleteGitHubSearch(GitHubError):
    """GitHub explicitly reports that a search page omitted results."""


def _retry_after_seconds(headers, payload) -> int | float | None:
    retry_after = headers.get('retry-after')
    if isinstance(retry_after, str) and retry_after.isdigit():
        retry_after = int(retry_after)
    else:
        retry_after = payload.get('retry_after') if isinstance(payload, dict) else None
    if type(retry_after) not in (int, float) or retry_after < 0:
        return None
    return retry_after


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')


def generate_app_jwt(app_id: int, private_key_pem: bytes, *, now: datetime) -> str:
    if isinstance(app_id, bool) or app_id <= 0:
        raise ValueError('GitHub App ID must be positive')
    try:
        key = serialization.load_pem_private_key(private_key_pem, password=None)
    except (TypeError, ValueError) as exc:
        raise ValueError('invalid GitHub App private key') from exc
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError('GitHub App private key must be RSA')
    current = now.astimezone(timezone.utc)
    header = {'alg': 'RS256', 'typ': 'JWT'}
    payload = {
        'iat': int(current.timestamp()) - 60,
        'exp': int((current + timedelta(minutes=9)).timestamp()),
        'iss': str(app_id),
    }
    signing_input = f'{_b64url(canonical_json(header))}.{_b64url(canonical_json(payload))}'.encode('ascii')
    signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f'{signing_input.decode("ascii")}.{_b64url(signature)}'


@dataclass
class GitHubAppAuth:
    app_id: int
    installation_id: int
    private_key_path: Path
    transport: Transport | None = None
    api_url: str = 'https://api.github.com'
    api_version: str = '2026-03-10'
    now_fn: Callable[[], datetime] = utc_now
    _cached_token: str | None = field(init=False, default=None)
    _cached_expiry: datetime | None = field(init=False, default=None)
    _lock: threading.Lock = field(init=False, default_factory=threading.Lock)

    def __post_init__(self) -> None:
        if isinstance(self.app_id, bool) or self.app_id <= 0:
            raise ValueError('GitHub App ID must be positive')
        if isinstance(self.installation_id, bool) or self.installation_id <= 0:
            raise ValueError('GitHub App installation ID must be positive')
        self.private_key_path = self.private_key_path.resolve()
        self.api_url = self.api_url.rstrip('/')
        self.transport = self.transport or UrllibTransport()

    def installation_token(self) -> str:
        with self._lock:
            now = self.now_fn().astimezone(timezone.utc)
            if self._cached_token and self._cached_expiry and self._cached_expiry > now + timedelta(minutes=2):
                return self._cached_token
            try:
                private_key = self.private_key_path.read_bytes()
            except OSError as exc:
                raise GitHubError(f'cannot read GitHub App private key: {self.private_key_path}') from exc
            jwt = generate_app_jwt(self.app_id, private_key, now=now)
            assert self.transport is not None
            try:
                status, response, response_headers = unpack_transport_response(self.transport.request(
                    'POST',
                    f'{self.api_url}/app/installations/{self.installation_id}/access_tokens',
                    {
                        'Accept': 'application/vnd.github+json',
                        'Authorization': f'Bearer {jwt}',
                        'Content-Type': 'application/json',
                        'User-Agent': 'adaptive-trust-ci/2.1.0',
                        'X-GitHub-Api-Version': self.api_version,
                    },
                    {
                        'permissions': {
                            'administration': 'read',
                            'checks': 'write',
                            'contents': 'read',
                            'pull_requests': 'read',
                        }
                    },
                ))
            except GitHubTransportError as exc:
                raise RetryableGitHubError('GitHub App token transport temporarily unavailable') from exc
            if status == 429 or 500 <= status <= 599:
                raise RetryableGitHubError(
                    f'GitHub App token request returned {status}',
                    retry_after_seconds=_retry_after_seconds(response_headers, response),
                )
            if status != 201 or not isinstance(response, dict):
                raise GitHubError(f'GitHub App token request returned {status}: {response}')
            token = str(response.get('token') or '').strip()
            expires_at = response.get('expires_at')
            if not token or not isinstance(expires_at, str):
                raise GitHubError('GitHub App token response is missing token or expires_at')
            expiry = parse_datetime(expires_at)
            if expiry <= now:
                raise GitHubError('GitHub App returned an already expired installation token')
            self._cached_token = token
            self._cached_expiry = expiry
            return token


@dataclass
class GitHubAppClient(GitHubClient):
    """Installation-authenticated, immutable merge provenance adapter."""

    now_fn: Callable[[], datetime] = utc_now
    expected_protected_ref: str | None = None
    required_check_name: str | None = None
    required_check_app_id: int | None = None

    def _request(self, method: str, path: str, body=None):
        assert self.transport is not None
        try:
            status, payload, headers = unpack_transport_response(
                self.transport.request(method, f'{self.api_url}{path}', self._headers(), body)
            )
        except GitHubTransportError as exc:
            raise RetryableGitHubError('GitHub transport temporarily unavailable') from exc
        if status == 429 or 500 <= status <= 599:
            raise RetryableGitHubError(
                f'GitHub API {method} {path} returned {status}',
                retry_after_seconds=_retry_after_seconds(headers, payload),
            )
        if status < 200 or status >= 300:
            raise GitHubError(f'GitHub API {method} {path} returned {status}: {payload}')
        return payload

    def get_pull(self, repository: str, pr_number: int) -> dict:
        response = self._request('GET', f'/repos/{repository}/pulls/{pr_number}')
        if not isinstance(response, dict):
            raise ProvenanceMismatch('github merge fact mismatch')
        return response

    def get_commit(self, repository: str, sha: str) -> dict:
        response = self._request('GET', f'/repos/{repository}/git/commits/{sha}')
        if not isinstance(response, dict):
            raise ProvenanceMismatch('exact commit mismatch')
        return response

    def get_required_status_checks(self, repository: str, protected_ref: str) -> dict:
        branch = protected_ref.removeprefix('refs/heads/')
        response = self._request(
            'GET',
            f'/repos/{repository}/branches/{urllib.parse.quote(branch, safe="")}/protection/required_status_checks',
        )
        if not isinstance(response, dict):
            raise ProvenanceMismatch('protected branch status unavailable')
        return response

    def list_closed_pulls(
        self,
        repository: str,
        *,
        updated_after: str,
        page: int,
        per_page: int,
    ) -> list[dict]:
        query = urllib.parse.urlencode(
            {
                'q': f'repo:{repository} is:pr is:merged updated:>={updated_after}',
                'sort': 'updated',
                'order': 'asc',
                'page': page,
                'per_page': per_page,
            }
        )
        response = self._request('GET', f'/search/issues?{query}')
        if isinstance(response, dict) and response.get('incomplete_results') is True:
            raise IncompleteGitHubSearch('GitHub pull reconciliation search is incomplete')
        values = response.get('items') if isinstance(response, dict) else None
        if not isinstance(values, list):
            raise GitHubError('GitHub pull reconciliation response is not a list')
        pulls: list[dict] = []
        for value in values:
            if not isinstance(value, dict) or type(value.get('number')) is not int:
                raise GitHubError('GitHub pull reconciliation item is malformed')
            pull = self.get_pull(repository, value['number'])
            if str(pull.get('updated_at', '')) >= updated_after:
                pulls.append(pull)
        return pulls

    def corroborate_merge(self, fact: MergedPullRequestFact) -> CorroboratedMerge:
        if (
            self.expected_protected_ref is None
            or self.required_check_name is None
            or type(self.required_check_app_id) is not int
            or self.required_check_app_id <= 0
        ):
            raise ProvenanceMismatch('protected branch protection verification is not configured')
        if fact.protected_ref != self.expected_protected_ref:
            raise ProvenanceMismatch('github merge fact protection mismatch')
        try:
            pull = self.get_pull(fact.repository, fact.pr_number)
        except RetryableGitHubError:
            raise
        except GitHubError as exc:
            raise ProvenanceMismatch('github merge fact unavailable') from exc
        base = pull.get('base')
        head = pull.get('head')
        api_repository = base.get('repo') if isinstance(base, dict) else None
        if (
            pull.get('number') != fact.pr_number
            or pull.get('merged') is not True
            or pull.get('merge_commit_sha') != fact.merged_commit_sha
            or not isinstance(base, dict)
            or base.get('ref') != fact.protected_ref.removeprefix('refs/heads/')
            or not isinstance(api_repository, dict)
            or api_repository.get('id') != fact.repository_id
            or str(api_repository.get('full_name', '')).lower() != fact.repository
            or not isinstance(head, dict)
            or head.get('sha') != fact.head_sha
        ):
            raise ProvenanceMismatch('github merge fact mismatch')
        try:
            protection = self.get_required_status_checks(fact.repository, fact.protected_ref)
        except RetryableGitHubError:
            raise
        except (GitHubError, ProvenanceMismatch) as exc:
            raise ProvenanceMismatch('protected branch status unavailable') from exc
        checks = protection.get('checks')
        if (
            protection.get('strict') is not True
            or not isinstance(checks, list)
            or not any(
                isinstance(check, dict)
                and check.get('context') == self.required_check_name
                and check.get('app_id') == self.required_check_app_id
                for check in checks
            )
        ):
            raise ProvenanceMismatch('protected branch protection required App check mismatch')
        try:
            commit = self.get_commit(fact.repository, fact.merged_commit_sha)
        except RetryableGitHubError:
            raise
        except (GitHubError, ProvenanceMismatch) as exc:
            raise ProvenanceMismatch('exact commit unavailable') from exc
        if commit.get('sha') != fact.merged_commit_sha:
            raise ProvenanceMismatch('exact commit mismatch')
        return CorroboratedMerge.from_fact(
            fact,
            required_check_name=self.required_check_name,
            required_check_app_id=self.required_check_app_id,
            now=self.now_fn(),
        )
