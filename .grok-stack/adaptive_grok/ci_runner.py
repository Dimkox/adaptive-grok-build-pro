from __future__ import annotations

import os
import pwd
import grp
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .ci_config import CIConfig
from .ci_crypto import sha256_json, sign_receipt
from .ci_github import GitHubClient
from .ci_store import DurableStore


class InfrastructureError(RuntimeError):
    pass


@dataclass(frozen=True)
class VerificationResult:
    status: str
    report: dict[str, Any]


Verifier = Callable[[Path, dict[str, Any], CIConfig], VerificationResult]


def _run(args: list[str], *, cwd: Path | None = None, timeout: int = 900, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout, env=env, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InfrastructureError(f"command failed to execute: {args[0]}: {exc}") from exc


def _git(root: Path, *args: str, timeout: int = 300) -> str:
    proc = _run(["git", *args], cwd=root, timeout=timeout)
    if proc.returncode:
        raise InfrastructureError((proc.stderr or proc.stdout or "git failed")[-4000:])
    return proc.stdout.strip()


def clean_environment(config: CIConfig) -> dict[str, str]:
    env: dict[str, str] = {
        "PATH": os.environ.get("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"),
        "HOME": "/tmp/adaptive-grok-ci-job-home",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "CI": "true",
    }
    for name in config.pass_environment:
        if name in os.environ:
            env[name] = os.environ[name]
    return env


def _sandbox_prefix(config: CIConfig) -> list[str]:
    if os.geteuid() != 0:
        if config.require_root_controller:
            raise InfrastructureError("trusted CI controller must run as root")
        return []
    try:
        uid = pwd.getpwnam(config.sandbox_user).pw_uid
        gid = grp.getgrnam(config.sandbox_group).gr_gid
    except KeyError as exc:
        raise InfrastructureError("sandbox user/group is not installed") from exc
    if not shutil.which("setpriv"):
        raise InfrastructureError("setpriv is required for untrusted candidate checks")
    return [
        "setpriv",
        f"--reuid={uid}",
        f"--regid={gid}",
        "--clear-groups",
        "--no-new-privs",
    ]


def prepare_exact_checkout(job: dict[str, Any], config: CIConfig, token: str | None = None) -> Path:
    config.workspace_root.mkdir(parents=True, exist_ok=True, mode=0o750)
    worktree = Path(tempfile.mkdtemp(prefix=f"job-{job['id'][:12]}-", dir=config.workspace_root))
    try:
        _git(worktree, "init", "-q")
        _git(worktree, "remote", "add", "origin", job["clone_url"])
        fetch = ["git"]
        if token:
            basic = __import__("base64").b64encode(f"x-access-token:{token}".encode()).decode()
            fetch.extend(["-c", f"http.extraHeader=Authorization: Basic {basic}"])
        fetch.extend(["fetch", "--no-tags", "--depth=1", "origin", job["head_sha"], job["base_sha"]])
        proc = _run(fetch, cwd=worktree, timeout=600)
        if proc.returncode:
            raise InfrastructureError((proc.stderr or proc.stdout or "git fetch failed")[-4000:])
        _git(worktree, "checkout", "--detach", "-q", job["head_sha"])
        actual = _git(worktree, "rev-parse", "HEAD")
        if actual != job["head_sha"]:
            raise InfrastructureError(f"checkout moved: expected {job['head_sha']}, got {actual}")
        if os.geteuid() == 0:
            uid = pwd.getpwnam(config.sandbox_user).pw_uid
            gid = grp.getgrnam(config.sandbox_group).gr_gid
            for path in [worktree, *worktree.rglob("*")]:
                try:
                    os.chown(path, uid, gid, follow_symlinks=False)
                except FileNotFoundError:
                    pass
        return worktree
    except Exception:
        shutil.rmtree(worktree, ignore_errors=True)
        raise


def changed_paths(worktree: Path, job: dict[str, Any]) -> list[str]:
    proc = _run(
        ["git", "diff", "--name-only", "--diff-filter=ACDMRTUXB", job["base_sha"], job["head_sha"]],
        cwd=worktree,
        timeout=120,
    )
    if proc.returncode:
        raise InfrastructureError((proc.stderr or proc.stdout or "git diff failed")[-4000:])
    return sorted({line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()})


def required_approval_scopes(worktree: Path, job: dict[str, Any], config: CIConfig) -> tuple[list[str], list[str]]:
    paths = changed_paths(worktree, job)
    scopes = set(job.get("required_approvals") or [])
    if any(config.is_trusted_path(path) for path in paths):
        scopes.add("trust-change")
    scopes.update(config.approval_scopes_for_paths(paths))
    return sorted(scopes), paths


def _parse_report(output: str) -> dict[str, Any]:
    try:
        report = __import__("json").loads(output)
    except __import__("json").JSONDecodeError as exc:
        raise InfrastructureError("trusted verifier did not return JSON") from exc
    if not isinstance(report, dict) or not isinstance(report.get("checks"), list):
        raise InfrastructureError("trusted verifier returned an invalid report")
    return report


def default_verifier(worktree: Path, job: dict[str, Any], config: CIConfig) -> VerificationResult:
    verifier = Path(__file__).resolve().parents[2] / "scripts" / "grok_ci_verify.py"
    if not verifier.is_file():
        raise InfrastructureError(f"trusted verifier wrapper is missing: {verifier}")
    command = [
        *_sandbox_prefix(config),
        sys.executable,
        str(verifier),
        "--repo", str(worktree),
        "--mode", config.verification_mode,
        "--base-sha", job["base_sha"],
        "--head-sha", job["head_sha"],
    ]
    for profile in job.get("profiles") or config.verification_profiles:
        command.extend(["--profile", profile])
    proc = _run(command, cwd=worktree, timeout=1800, env=clean_environment(config))
    report = _parse_report(proc.stdout)
    checks = {str(item.get("name")): str(item.get("status")) for item in report["checks"] if isinstance(item, dict)}
    gaps = [name for name in config.required_checks if checks.get(name) != "pass"]
    if gaps:
        report["trusted_gate_gaps"] = gaps
    status = "pass" if proc.returncode == 0 and not gaps and report.get("status") == "pass" else "fail"
    return VerificationResult(status, report)


def run_external_commands(worktree: Path, config: CIConfig) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    prefix = _sandbox_prefix(config)
    for argv in config.external_commands:
        proc = _run([*prefix, *argv], cwd=worktree, timeout=1800, env=clean_environment(config))
        results.append({
            "name": "external:" + " ".join(argv),
            "status": "pass" if proc.returncode == 0 else "fail",
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-12000:],
            "stderr": proc.stderr[-12000:],
        })
    return results


class TrustedRunner:
    def __init__(
        self,
        config: CIConfig,
        store: DurableStore,
        github: GitHubClient,
        *,
        verifier: Verifier = default_verifier,
        worker_id: str | None = None,
    ) -> None:
        self.config = config
        self.store = store
        self.github = github
        self.verifier = verifier
        self.worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}"

    def _status(self, job: dict[str, Any], state: str, description: str) -> None:
        self.github.set_commit_status(
            job["repo"], job["head_sha"], state, job["status_context"], description, self.config.status_target_url
        )

    def run_job(self, job: dict[str, Any]) -> dict[str, Any]:
        checkout: Path | None = None
        try:
            self._status(job, "pending", "trusted self-hosted CI is running")
            token = os.environ.get(self.config.github_token_env)
            checkout = prepare_exact_checkout(job, self.config, token)
            scopes, paths = required_approval_scopes(checkout, job, self.config)
            missing = self.store.missing_approvals(job["id"], scopes, job["head_sha"])
            if missing:
                blocked = self.store.block_job(job["id"], self.worker_id, "missing signed approvals: " + ", ".join(missing))
                self._status(job, "pending", "waiting for signed approval: " + ", ".join(missing))
                return blocked

            verification = self.verifier(checkout, job, self.config)
            external = run_external_commands(checkout, self.config)
            if any(item["status"] != "pass" for item in external):
                verification = VerificationResult("fail", {**verification.report, "external_checks": external})
            else:
                verification.report["external_checks"] = external

            receipt = {
                "schema_version": 1,
                "kind": "trusted-ci",
                "job_id": job["id"],
                "repo": job["repo"],
                "base_sha": job["base_sha"],
                "head_sha": job["head_sha"],
                "branch": job["branch"],
                "route_id": job.get("route_id"),
                "change_id": job.get("change_id"),
                "config_digest": self.config.digest,
                "runner_id": self.worker_id,
                "changed_paths": paths,
                "approval_scopes": scopes,
                "approvals": self.store.valid_approvals(job["id"], scopes, job["head_sha"]),
                "verification": verification.report,
                "status": verification.status,
            }
            signature, key_id = sign_receipt(receipt, self.config.receipt_signing_key, self.config.receipt_key_id)
            payload_hash = sha256_json(receipt)
            self.store.record_receipt(
                job_id=job["id"], head_sha=job["head_sha"], kind="trusted-ci",
                status=verification.status, payload_hash=payload_hash, payload=receipt,
                signature=signature, key_id=key_id,
            )
            if verification.status == "pass":
                result = self.store.finish_job(job["id"], self.worker_id, status="succeeded", result=receipt)
                self._status(job, "success", "trusted exact-SHA verification passed")
            else:
                result = self.store.finish_job(job["id"], self.worker_id, status="failed", result=receipt, error="trusted verification failed")
                self._status(job, "failure", "trusted exact-SHA verification failed")
            return result
        except InfrastructureError as exc:
            result = self.store.retry_or_dead(job["id"], self.worker_id, str(exc))
            self._status(job, "error" if result["status"] == "dead" else "pending", f"CI infrastructure error; state={result['status']}")
            return result
        finally:
            if checkout:
                shutil.rmtree(checkout, ignore_errors=True)

    def run_once(self) -> dict[str, Any] | None:
        job = self.store.lease_next(self.worker_id, self.config.lease_seconds)
        return self.run_job(job) if job else None

    def run_forever(self) -> None:
        while True:
            result = self.run_once()
            if result is None:
                time.sleep(self.config.poll_seconds)
