from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass

from .models import JobRequest


class WebhookError(ValueError):
    pass


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
    if pull_request.get("draft") and action != "closed":
        return None
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
