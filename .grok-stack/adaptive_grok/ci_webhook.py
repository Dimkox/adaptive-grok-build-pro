from __future__ import annotations

import hashlib
import hmac
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .ci_config import CIConfig
from .ci_github import GitHubClient
from .ci_store import DurableStore

ACCEPTED_ACTIONS = frozenset({"opened", "reopened", "synchronize", "ready_for_review"})


def verify_github_signature(secret: bytes, body: bytes, header: str | None) -> bool:
    if not secret or not header or not header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)


def intake_pull_request(
    payload: dict[str, Any],
    *,
    config: CIConfig,
    store: DurableStore,
    github: GitHubClient | None = None,
) -> dict[str, Any] | None:
    if payload.get("action") not in ACCEPTED_ACTIONS:
        return None
    pull = payload.get("pull_request")
    repo_obj = payload.get("repository")
    if not isinstance(pull, dict) or not isinstance(repo_obj, dict) or pull.get("draft"):
        return None
    repo = str(repo_obj.get("full_name") or "")
    if config.allowed_repositories and repo not in config.allowed_repositories:
        raise ValueError(f"repository is not allowed: {repo}")
    base = pull.get("base") or {}
    head = pull.get("head") or {}
    base_ref = str(base.get("ref") or "")
    if base_ref != config.default_branch:
        return None
    base_sha = str(base.get("sha") or "")
    head_sha = str(head.get("sha") or "")
    clone_url = str(repo_obj.get("clone_url") or "")
    if len(base_sha) != 40 or len(head_sha) != 40 or not clone_url:
        raise ValueError("pull request payload has no exact base/head SHA or clone URL")
    branch = str(head.get("ref") or f"pr-{pull.get('number', 'unknown')}")
    job = store.enqueue_job(
        repo=repo,
        clone_url=clone_url,
        base_sha=base_sha,
        head_sha=head_sha,
        branch=branch,
        profiles=list(config.verification_profiles),
        required_approvals=list(config.webhook_required_approvals),
        status_context=config.status_context,
        max_attempts=config.max_attempts,
    )
    if github:
        github.set_commit_status(
            repo,
            head_sha,
            "pending",
            config.status_context,
            "queued in trusted self-hosted CI",
            config.status_target_url,
        )
    return job


class WebhookApplication:
    def __init__(self, config: CIConfig, store: DurableStore, github: GitHubClient) -> None:
        self.config = config
        self.store = store
        self.github = github
        self.secret = Path(config.webhook_secret_file).read_bytes().strip()
        if not self.secret:
            raise RuntimeError("GitHub webhook secret is empty")

    def handle(self, event: str | None, signature: str | None, body: bytes) -> tuple[int, dict[str, Any]]:
        if not verify_github_signature(self.secret, body, signature):
            return 401, {"error": "invalid signature"}
        if event == "ping":
            return 200, {"ok": True}
        if event != "pull_request":
            return 202, {"ignored": event or "unknown"}
        try:
            payload = json.loads(body)
            if not isinstance(payload, dict):
                raise ValueError("payload is not an object")
            job = intake_pull_request(payload, config=self.config, store=self.store, github=self.github)
        except (ValueError, json.JSONDecodeError) as exc:
            return 400, {"error": str(exc)}
        return (202, {"ignored": True}) if job is None else (202, {"job_id": job["id"], "status": job["status"]})


def serve_webhook(application: WebhookApplication) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/github/webhook":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_error(400)
                return
            if length < 1 or length > 2_000_000:
                self.send_error(413)
                return
            body = self.rfile.read(length)
            status, response = application.handle(
                self.headers.get("X-GitHub-Event"),
                self.headers.get("X-Hub-Signature-256"),
                body,
            )
            data = json.dumps(response).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer((application.config.webhook_listen_host, application.config.webhook_listen_port), Handler)
    server.serve_forever()
