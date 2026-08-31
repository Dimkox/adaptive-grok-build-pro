from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import uuid

import httpx

from .settings import read_token_file


MAX_BODY_BYTES = 1_048_576


def _load(path: str) -> dict:
    raw = sys.stdin.buffer.read(MAX_BODY_BYTES + 1) if path == "-" else Path(path).read_bytes()
    if len(raw) > MAX_BODY_BYTES: raise SystemExit("input exceeds 1 MiB")
    value = json.loads(raw)
    if not isinstance(value, dict): raise SystemExit("JSON object required")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adaptive-factory")
    parser.add_argument("--socket", default="/run/adaptive-factory/control.sock")
    parser.add_argument("--token-file", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("health")
    intake = sub.add_parser("intake"); intake.add_argument("file")
    show = sub.add_parser("show"); show.add_argument("task_id")
    listing = sub.add_parser("list"); listing.add_argument("repository_id")
    cancel = sub.add_parser("cancel"); cancel.add_argument("task_id"); cancel.add_argument("reason")
    kill = sub.add_parser("kill"); kill.add_argument("scope_key"); kill.add_argument("reason")
    unkill = sub.add_parser("unkill"); unkill.add_argument("scope_key"); unkill.add_argument("reason")
    reconcile = sub.add_parser("reconcile"); reconcile.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
    token = read_token_file(Path(args.token_file))
    correlation = str(uuid.uuid4()); key = str(uuid.uuid4())
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": key, "X-Correlation-ID": correlation}
    transport = httpx.HTTPTransport(uds=args.socket)
    with httpx.Client(transport=transport, base_url="http://factory.local", timeout=5.0) as client:
        if args.command == "health": response = client.get("/health/ready")
        elif args.command == "intake":
            body = _load(args.file); headers["Idempotency-Key"] = body.get("request_id", key); response = client.post("/v1/tasks", headers=headers, json=body)
        elif args.command == "show": response = client.get(f"/v1/tasks/{args.task_id}", headers=headers)
        elif args.command == "list": response = client.get("/v1/tasks", headers=headers, params={"repository_id": args.repository_id})
        elif args.command == "cancel": response = client.post(f"/v1/tasks/{args.task_id}/cancel", headers=headers, json={"reason": args.reason})
        elif args.command in {"kill", "unkill"}: response = client.post("/v1/kill-switches", headers=headers, json={"scope_key": args.scope_key, "enabled": args.command == "kill", "reason": args.reason})
        else: response = client.post("/v1/reconcile", headers=headers, json={"limit": args.limit})
    print(json.dumps(response.json(), sort_keys=True, separators=(",", ":")))
    return 0 if response.is_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
