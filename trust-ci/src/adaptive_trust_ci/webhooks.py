from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Callable, Iterable

from .models import JobRequest, utc_now
from .provenance import MergedPullRequestFact, payload_digest


class WebhookError(ValueError):
    pass


class WebhookForbidden(WebhookError):
    pass


class WebhookUnavailable(WebhookError):
    pass


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise WebhookError('webhook body contains duplicate JSON key')
        result[key] = value
    return result


@dataclass(frozen=True)
class PullRequestEvent:
    action: str
    request: JobRequest
    closed: bool = False


_SUPPORTED_ACTIONS = {"opened", "synchronize", "reopened", "ready_for_review"}


def verify_webhook_signature(secret: str, body: bytes, signature_header: str | None) -> None:
    if not secret:
        raise WebhookError("webhook secret is not configured")
    if not signature_header or not signature_header.startswith("sha256="):
        raise WebhookError("missing or malformed webhook signature")
    supplied = signature_header.removeprefix("sha256=")
    if len(supplied) != 64:
        raise WebhookError("malformed webhook signature")
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, supplied):
        raise WebhookError("invalid webhook signature")


def parse_pull_request_event(event_name: str | None, body: bytes) -> PullRequestEvent | None:
    if event_name != "pull_request":
        return None
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise WebhookError("webhook body is not valid JSON") from exc
    if not isinstance(data, dict):
        raise WebhookError("webhook body must be an object")
    action = str(data.get("action", ""))
    if action not in _SUPPORTED_ACTIONS | {"closed"}:
        return None
    repository = data.get("repository")
    pull_request = data.get("pull_request")
    if not isinstance(repository, dict) or not isinstance(pull_request, dict):
        raise WebhookError("pull_request webhook is missing repository or pull_request")
    try:
        request = JobRequest(
            repository=str(repository["full_name"]),
            pr_number=int(pull_request["number"]),
            base_sha=str(pull_request["base"]["sha"]),
            head_sha=str(pull_request["head"]["sha"]),
            head_ref=str(pull_request["head"]["ref"]),
            base_ref=str(pull_request["base"]["ref"]),
            pipeline="pull_request",
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WebhookError(f"malformed pull_request webhook: {exc}") from exc
    return PullRequestEvent(action=action, request=request, closed=action == "closed")


def parse_merged_pull_request(body: bytes, delivery_id: str, *, now=None) -> MergedPullRequestFact | None:
    try:
        data = json.loads(body, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise WebhookError('webhook body is not valid JSON') from exc
    if not isinstance(data, dict):
        raise WebhookError('webhook body must be an object')
    if data.get('action') != 'closed':
        return None
    repository = data.get('repository')
    installation = data.get('installation')
    pull_request = data.get('pull_request')
    if not isinstance(pull_request, dict):
        raise WebhookError('merged webhook is missing pull_request')
    if pull_request.get('merged') is not True:
        return None
    if not isinstance(repository, dict) or not isinstance(installation, dict):
        raise WebhookError('merged webhook is missing provenance fields')
    try:
        base = pull_request['base']
        head = pull_request['head']
        if not isinstance(base, dict) or not isinstance(head, dict):
            raise TypeError('invalid pull request refs')
        return MergedPullRequestFact.create(
            delivery_id=delivery_id,
            payload_sha256=payload_digest(body),
            repository_id=repository['id'],
            repository=repository['full_name'],
            installation_id=installation['id'],
            pr_number=pull_request['number'],
            head_sha=head['sha'],
            base_sha=base['sha'],
            protected_ref='refs/heads/' + base['ref'],
            merged_commit_sha=pull_request['merge_commit_sha'],
            merged_at=pull_request['merged_at'],
            received_at=now or utc_now(),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WebhookError('malformed merged pull_request webhook') from exc


def ingest_merged_pull_request(
    *,
    secret: str,
    signature_header: str | None,
    event_name: str | None,
    delivery_id: str | None,
    body: bytes,
    allowed_repositories: Iterable[str],
    protected_ref: str | None,
    record_fact: Callable[[MergedPullRequestFact], object] | None,
    now=None,
) -> MergedPullRequestFact | None:
    """Authenticate and validate a merged delivery before any persistence callback."""
    verify_webhook_signature(secret, body, signature_header)
    if event_name != 'pull_request':
        return None
    if not isinstance(delivery_id, str) or not delivery_id.strip():
        raise WebhookError('missing or malformed GitHub delivery identifier')
    fact = parse_merged_pull_request(body, delivery_id, now=now)
    if fact is None:
        return None
    if (
        not isinstance(protected_ref, str)
        or not protected_ref.startswith('refs/heads/')
        or protected_ref == 'refs/heads/'
    ):
        raise WebhookError('server protected ref is not configured')
    allowed = {str(repository).lower() for repository in allowed_repositories}
    if fact.repository not in allowed:
        raise WebhookForbidden('repository is not allowed by server policy')
    if fact.protected_ref != protected_ref:
        raise WebhookForbidden('merge does not target the configured protected ref')
    if not callable(record_fact):
        raise WebhookUnavailable('durable merge fact recorder is unavailable')
    try:
        record_fact(fact)
    except Exception as exc:
        raise WebhookUnavailable('durable merge fact recorder is unavailable') from exc
    return fact
