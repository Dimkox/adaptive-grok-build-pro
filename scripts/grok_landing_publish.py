"""Repository entrypoint for explicit local landing publication operations."""

from pathlib import Path
from datetime import datetime, timedelta, timezone
import hashlib
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
for component in (ROOT / ".grok-stack", ROOT / "delivery/src", ROOT / "factory/src"):
    sys.path.insert(0, str(component))

from adaptive_factory.landing_publication_cli import main as publication_main
from adaptive_factory.contracts import canonical_json
from adaptive_factory.landing_contracts import strict_json_object
from adaptive_factory.settings import read_private_file

def _authority(config, control_root, request):
    from adaptive_delivery.landing_publication_contracts import PublicationError
    from adaptive_grok.state import get_active_change, get_active_route
    from adaptive_grok.util import git_head, git_output, tree_fingerprint

    route, change = get_active_route(control_root), get_active_change(control_root)
    if (
        not isinstance(route, dict) or not isinstance(change, dict)
        or route.get("route_id") != config["route_id"]
        or route.get("change_id") != config["change_id"]
        or change.get("change_id") != config["change_id"]
    ):
        raise PublicationError("publication_control_route")
    remote = git_output(control_root, "config", "--get", "remote.origin.url") or ""
    match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([^/\s]+/[^/\s]+?)(?:\.git)?", remote)
    if match is None or match.group(1) != "Dimkox/adaptive-grok-build-pro":
        raise PublicationError("publication_control_repository")
    head = git_head(control_root)
    fingerprint = tree_fingerprint(control_root)
    if (not isinstance(head, str) or re.fullmatch(r"[0-9a-f]{40}", head) is None
            or not isinstance(fingerprint, str) or re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None):
        raise PublicationError("publication_control_identity")
    grants = strict_json_object(
        b'{"grants":' + read_private_file(control_root / ".grok-stack/runtime/approvals.json", 1_048_576) + b'}',
        maximum=1_048_600,
    )["grants"]
    if not isinstance(grants, list) or len(grants) > 200:
        raise PublicationError("publication_grants")
    now = datetime.now(timezone.utc)
    matches = []
    for grant in grants:
        if not isinstance(grant, dict):
            continue
        required = {
            "schema_version": 2, "authorization": "delegated-local-grant",
            "repository": "Dimkox/adaptive-grok-build-pro",
            "route_id": config["route_id"], "change_id": config["change_id"],
            "git_head": head, "tree_fingerprint": fingerprint,
            "scope": "external-write", "actions": ["external-write"],
            "resources": [request.resource],
        }
        if any(grant.get(key) != value for key, value in required.items()):
            continue
        if grant.get("source") not in {"standing-user-consent", "explicit-user-consent"}:
            continue
        if not re.fullmatch(r"[0-9a-f]{16}", str(grant.get("id", ""))):
            continue
        try:
            created = datetime.fromisoformat(grant["created_at"])
            expires = datetime.fromisoformat(grant["expires_at"])
            if (created.tzinfo is None or expires.tzinfo is None or not created <= now < expires
                    or expires - created > timedelta(days=1)):
                continue
        except (KeyError, TypeError, ValueError):
            continue
        matches.append(grant)
    if len(matches) != 1:
        raise PublicationError("publication_exact_grant_unavailable")
    return hashlib.sha256(canonical_json(matches[0])).hexdigest()


def main(argv=None):
    return publication_main(argv, control_root=ROOT, authority=_authority)


if __name__ == "__main__":
    raise SystemExit(main())
