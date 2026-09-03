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
    if len(raw) > MAX_BODY_BYTES:
        raise SystemExit("input exceeds 1 MiB")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise SystemExit("JSON object required")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adaptive-factory")
    parser.add_argument("--socket", default="/run/adaptive-factory/control.sock")
    parser.add_argument("--token-file", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("health")
    intake = sub.add_parser("intake")
    intake.add_argument("file")
    show = sub.add_parser("show")
    show.add_argument("task_id")
    listing = sub.add_parser("list")
    listing.add_argument("repository_id")
    runs = sub.add_parser("runs")
    runs.add_argument("task_id")
    runs.add_argument("--limit", type=int, default=100)
    runs.add_argument("--cursor")
    events = sub.add_parser("events")
    events.add_argument("task_id")
    events.add_argument("--limit", type=int, default=100)
    events.add_argument("--cursor", type=int)
    cancel = sub.add_parser("cancel")
    cancel.add_argument("task_id")
    cancel.add_argument("reason")
    claim = sub.add_parser("claim")
    claim.add_argument("role", choices=("reader", "writer"))
    claim.add_argument("repository", nargs="+")
    claim.add_argument("--lease-seconds", type=int, default=30)
    heartbeat = sub.add_parser("heartbeat")
    heartbeat.add_argument("grant_file")
    transition = sub.add_parser("transition")
    transition.add_argument("grant_file")
    transition.add_argument(
        "target", choices=("analyzing", "implementing", "verifying", "reviewing")
    )
    proposal = sub.add_parser("proposal")
    proposal.add_argument("grant_file")
    proposal.add_argument("outcome")
    reserve = sub.add_parser("reserve-budget")
    reserve.add_argument("grant_file")
    reserve.add_argument("cost_usd_micros", type=int)
    reserve.add_argument("token_units", type=int)
    reserve.add_argument("wall_seconds", type=int)
    reserve.add_argument("reason_digest")
    usage = sub.add_parser("observe-usage")
    usage.add_argument("grant_file")
    usage.add_argument("provider_call_id")
    usage.add_argument("price_table_digest")
    usage.add_argument("cost_usd_micros", type=int)
    usage.add_argument("token_units", type=int)
    usage.add_argument("output_bytes", type=int)
    kill = sub.add_parser("kill")
    kill.add_argument("scope_key")
    kill.add_argument("reason")
    unkill = sub.add_parser("unkill")
    unkill.add_argument("scope_key")
    unkill.add_argument("reason")
    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
    token = read_token_file(Path(args.token_file))
    correlation = str(uuid.uuid4())
    key = str(uuid.uuid4())
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": key, "X-Correlation-ID": correlation}
    transport = httpx.HTTPTransport(uds=args.socket)
    with httpx.Client(transport=transport, base_url="http://factory.local", timeout=5.0) as client:
        if args.command == "health":
            response = client.get("/health/ready")
        elif args.command == "intake":
            body = _load(args.file)
            headers["Idempotency-Key"] = body.get("request_id", key)
            response = client.post("/v1/tasks", headers=headers, json=body)
        elif args.command == "show":
            response = client.get(f"/v1/tasks/{args.task_id}", headers=headers)
        elif args.command == "list":
            response = client.get("/v1/tasks", headers=headers, params={"repository_id": args.repository_id})
        elif args.command == "runs":
            params = {"limit": args.limit}
            if args.cursor is not None:
                params["cursor"] = args.cursor
            response = client.get(f"/v1/tasks/{args.task_id}/runs", headers=headers, params=params)
        elif args.command == "events":
            params = {"limit": args.limit}
            if args.cursor is not None:
                params["cursor"] = args.cursor
            response = client.get(f"/v1/tasks/{args.task_id}/events", headers=headers, params=params)
        elif args.command == "cancel":
            response = client.post(f"/v1/tasks/{args.task_id}/cancel", headers=headers, json={"reason": args.reason})
        elif args.command == "claim":
            response = client.post(
                "/v1/claims",
                headers=headers,
                json={
                    "role": args.role,
                    "repositories": args.repository,
                    "lease_seconds": args.lease_seconds,
                },
            )
        elif args.command == "heartbeat":
            response = client.post("/v1/heartbeats", headers=headers, json=_load(args.grant_file))
        elif args.command == "transition":
            response = client.post(
                "/v1/transitions",
                headers=headers,
                json={"grant": _load(args.grant_file), "target": args.target},
            )
        elif args.command == "proposal":
            response = client.post(
                "/v1/proposals", headers=headers, json={"grant": _load(args.grant_file), "outcome": args.outcome}
            )
        elif args.command == "reserve-budget":
            response = client.post(
                "/v1/budget-reservations",
                headers=headers,
                json={
                    "grant": _load(args.grant_file),
                    "cost_usd_micros": args.cost_usd_micros,
                    "token_units": args.token_units,
                    "wall_seconds": args.wall_seconds,
                    "reason_digest": args.reason_digest,
                },
            )
        elif args.command == "observe-usage":
            response = client.post(
                "/v1/usage-observations",
                headers=headers,
                json={
                    "grant": _load(args.grant_file),
                    "provider_call_id": args.provider_call_id,
                    "price_table_digest": args.price_table_digest,
                    "cost_usd_micros": args.cost_usd_micros,
                    "token_units": args.token_units,
                    "output_bytes": args.output_bytes,
                },
            )
        elif args.command in {"kill", "unkill"}:
            response = client.post(
                "/v1/kill-switches",
                headers=headers,
                json={"scope_key": args.scope_key, "enabled": args.command == "kill", "reason": args.reason},
            )
        else:
            response = client.post("/v1/reconcile", headers=headers, json={"limit": args.limit})
    print(json.dumps(response.json(), sort_keys=True, separators=(",", ":")))
    return 0 if response.is_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
