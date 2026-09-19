"""Opaque systemd credential client; one fixed synthetic job per upgraded unit."""
import argparse
import json
import os
from pathlib import Path
import stat
import time
import httpx
from adaptive_factory.landing_http import HttpLandingProfile
from adaptive_factory.landing_failover_contracts import CAPABILITY_FIELDS, check_seal, validate_receipt

parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=("offline", "capability", "accept", "observe"))
parser.add_argument("service", choices=("qwen", "grok"))
args = parser.parse_args()
suffix, profile = ("", "qwen-omni-intl") if args.service == "qwen" else ("-grok", "grok-vision")
job = "runtime-26a0d3d-20260919-" + args.service
base_sha = "fde60e040167c10975b00d11f578c4da6763069a"
base_tree = "21817e70e079b772e1f3114a80dfc0320d1ada91"
repo = "github.com/Dimkox/ai-dark-factory-landing"
result = {"service": args.service, "mode": args.mode, "job_id": job, "client_posts": 0}
try:
    credential_path = Path(os.environ["CREDENTIALS_DIRECTORY"]) / "landing-client"
    fd = os.open(credential_path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, os.geteuid())
                or stat.S_IMODE(info.st_mode) not in (0o400, 0o440, 0o600) or info.st_size > 4096):
            raise RuntimeError("credential_metadata")
        token = stream.read(4097).decode("utf-8").strip()
    if not 16 <= len(token) <= 4096 or any(c.isspace() for c in token):
        raise RuntimeError("credential_shape")
    headers = {"Authorization": "Bearer " + token, "X-Repository-ID": repo,
               "X-Correlation-ID": job, "Accept-Encoding": "identity"}
    transport = httpx.HTTPTransport(uds="/run/adaptive-l5" + suffix + "/control.sock", retries=0)
    with httpx.Client(transport=transport, base_url="http://localhost", timeout=150,
                      trust_env=False, follow_redirects=False) as client:
        ready = client.get("/health/ready")
        assert ready.status_code == 200 and ready.json() == {
            "status": "ready", "component": "landing-local", "production_verified": False}
        capability = client.get("/v2/landing-backend", headers=headers)
        if args.mode == "offline":
            assert capability.status_code == 409
            result.update({"status": "offline_ready", "capability_http_status": 409})
        else:
            assert capability.status_code == 200
            facts = capability.json()
            check_seal("landing-backend-v1", facts, CAPABILITY_FIELDS)
            expected = HttpLandingProfile.for_provider(profile, available=True)
            assert facts["attempt_protocol"] == 1
            assert facts["profile"] == expected.to_facts() and facts["profile_digest"] == expected.profile_digest
            assert (facts["repository_id"], facts["exact_base_sha"], facts["exact_base_tree"]) == (repo, base_sha, base_tree)
            result.update({"profile": profile, "profile_digest": expected.profile_digest,
                           "model": facts["profile"]["model_id"], "status": "capability_ready"})
            if args.mode in {"accept", "observe"}:
                attempt_path = "/v2/landing-jobs/" + job + "/attempt"
                response = client.get(attempt_path, headers=headers)
                if response.status_code == 404 and args.mode == "accept":
                    bound_headers = {**headers, "Idempotency-Key": job, "Content-Type": "text/plain",
                        "X-Exact-Base-SHA": base_sha, "X-Exact-Base-Tree": base_tree,
                        "X-Expected-Actor-ID": facts["actor_id"], "X-Expected-Profile-Digest": expected.profile_digest}
                    result["client_posts"] = 1
                    started = time.monotonic()
                    try:
                        submitted = client.post("/v1/landing-inputs", headers=bound_headers,
                            content=b"Create an English landing page for a fictional local gardening club. One hero section. No links, prices, contacts or factual claims.")
                        result["submit_http_status"] = submitted.status_code
                    except httpx.HTTPError:
                        result["submit_outcome"] = "ambiguous"
                    result["elapsed_ms"] = round((time.monotonic() - started) * 1000)
                    response = client.get(attempt_path, headers=headers)
                assert response.status_code == 200
                receipt = response.json()
                source, observation, artifact = validate_receipt(receipt)
                result.update({"state": receipt["state"], "attempt_digest": receipt["digest"],
                    "provider_evidence_digest": receipt["provider_evidence_digest"], "reason_code": receipt["reason_code"],
                    "observation": ({k: getattr(observation, k) for k in ("category", "dispatched", "usage_status", "usage_input_units", "usage_output_units", "http_status")} if observation else None)})
                assert source.job_id == job and source.exact_base_sha == base_sha
                assert (source.tenant_id, source.repository_id, source.exact_base_tree) == (facts["actor_id"], repo, base_tree)
                fetched = client.get("/v1/landing-jobs/" + job + "/result", headers=headers)
                assert fetched.status_code == 200
                payload = fetched.json()
                result.update({key: payload.get(key) for key in ("artifact_digest", "live_url")})
                assert receipt["state"] == "artifact_ready" and artifact and result["artifact_digest"]
                assert payload["job_id"] == job and payload["state"] == receipt["state"]
                assert payload["artifact_digest"] == artifact.artifact_digest
                assert observation and observation.category == "normalized" and observation.dispatched
                assert observation.usage_status == "reported" and artifact.profile_digest == expected.profile_digest
                assert payload["live_url"] is None
                result["status"] = "accepted_runtime_artifact"
    print(json.dumps(result, sort_keys=True))
except Exception as exc:
    result.update({"status": "failed", "error_type": type(exc).__name__})
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(1) from None
