from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from adaptive_trust_ci.github_app import generate_app_jwt

SECRET_PATH = Path("/tmp/wh.secret")
URL = "https://claw.taild9f611.ts.net/webhooks/github"


def main() -> None:
    secret = SECRET_PATH.read_text(encoding="utf-8").strip()
    SECRET_PATH.unlink(missing_ok=True)
    if not secret:
        print(json.dumps({"status": "error", "detail": "empty webhook secret"}))
        return
    pem = Path(os.environ["TRUST_CI_GITHUB_APP_PRIVATE_KEY_PATH"]).read_bytes()
    app_id = int(os.environ["TRUST_CI_GITHUB_APP_ID"])
    token = generate_app_jwt(app_id, pem, now=datetime.now(timezone.utc))
    body = json.dumps(
        {
            "url": URL,
            "content_type": "json",
            "secret": secret,
            "insecure_ssl": "0",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/app/hook/config",
        data=body,
        method="PATCH",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "adaptive-trust-ci/2.1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")[:400]
        print(json.dumps({"status": exc.code, "error": raw}))
        return
    print(
        json.dumps(
            {
                "status": 200,
                "url": data.get("url"),
                "content_type": data.get("content_type"),
                "insecure_ssl": data.get("insecure_ssl"),
                "secret_set": bool(data.get("secret")),
            }
        )
    )


if __name__ == "__main__":
    main()
