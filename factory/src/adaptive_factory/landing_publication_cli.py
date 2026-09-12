"""Owner-configured landing publication CLI; independent of HTTP landing API v1."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import quote

from .contracts import canonical_json
from .landing_artifact import DEPLOY_MEMBERS, MAX_ARCHIVE_BYTES
from .landing_artifact_retention import RetainedLandingArtifact
from .landing_contracts import LandingInputV1, SiteArtifactV1, strict_json_object
from .landing_sqlite_store import APPLICATION_ID, SCHEMA_VERSION
from .settings import read_private_file


def _config(path, control_root):
    from adaptive_delivery.landing_publication_contracts import PublicationError, PublicationTargetV1

    data = strict_json_object(read_private_file(Path(path), 16_384), maximum=16_384)
    if set(data) != {
        "schema_version", "control_repository", "route_id", "change_id",
        "publication_state_root", "landing_state_root", "tenant_id", "repository_id", "target",
    } or data["schema_version"] != 1 or data["control_repository"] != str(control_root):
        raise PublicationError("publication_config")
    for key in ("route_id", "change_id", "tenant_id", "repository_id"):
        if not isinstance(data[key], str) or not 1 <= len(data[key]) <= 256:
            raise PublicationError("publication_config")
    try:
        target = PublicationTargetV1(**data["target"])
    except (TypeError, ValueError):
        raise PublicationError("publication_target") from None
    roots = [Path(data[key]) for key in ("publication_state_root", "landing_state_root")]
    roots.extend((Path(target.root), control_root))
    if any(not path.is_absolute() or ".." in path.parts for path in roots):
        raise PublicationError("publication_config_path")
    if any(left == right or left in right.parents or right in left.parents
           for index, left in enumerate(roots) for right in roots[index + 1:]):
        raise PublicationError("publication_config_overlap")
    return data, target


def _bundle(config, target, reference):
    from adaptive_delivery.landing_filesystem import private_root
    from adaptive_delivery.landing_publication_contracts import PublicationBundle, PublicationError

    if not isinstance(reference, dict) or set(reference) != {"tenant_id", "repository_id", "job_id"}:
        raise PublicationError("publication_artifact_reference")
    if reference["tenant_id"] != config["tenant_id"] or reference["repository_id"] != config["repository_id"]:
        raise PublicationError("publication_artifact_scope")
    root = Path(config["landing_state_root"])
    descriptor = private_root(root)
    connection = None
    try:
        database = root / "landing.sqlite3"
        # Validate metadata only; SQLite owns reading the durable WAL snapshot.
        metadata = database.lstat()
        import stat

        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600):
            raise PublicationError("publication_landing_state")
        connection = sqlite3.connect(f"file:{quote(str(database), safe='/')}?mode=ro",
                                     uri=True, isolation_level=None, timeout=5)
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        identity = (connection.execute("PRAGMA application_id").fetchone()[0],
                    connection.execute("PRAGMA user_version").fetchone()[0])
        if identity != (APPLICATION_ID, SCHEMA_VERSION):
            raise PublicationError("publication_landing_schema")
        row = connection.execute(
            "SELECT source_json,artifact_json,sealed_artifact_json,state FROM landing_jobs "
            "WHERE tenant_id=? AND repository_id=? AND job_id=?",
            (reference["tenant_id"], reference["repository_id"], reference["job_id"]),
        ).fetchone()
        if row is None or row[3] != "artifact_ready" or row[1] is None or row[2] is None:
            raise PublicationError("publication_artifact_unavailable")
        source = LandingInputV1.from_dict(strict_json_object(bytes(row[0])))
        artifact = SiteArtifactV1.from_dict(strict_json_object(bytes(row[1])))
        retained = RetainedLandingArtifact.from_dict(strict_json_object(bytes(row[2]), maximum=4_194_304))
        if (
            (source.tenant_id, source.repository_id, source.job_id)
            != (reference["tenant_id"], reference["repository_id"], reference["job_id"])
            or retained.artifact != artifact or artifact.canonical_origin.rstrip("/") != target.public_origin
        ):
            raise PublicationError("publication_artifact_binding")
        output = retained.output_root
        for key in ("control_repository", "publication_state_root", "landing_state_root"):
            root_path = Path(config[key])
            if root_path == output or root_path in output.parents or output in root_path.parents:
                raise PublicationError("publication_artifact_path")
        deployment = Path(target.root)
        if deployment == output or deployment in output.parents or output in deployment.parents:
            raise PublicationError("publication_artifact_path")
        retained.validate(source)
        archive = read_private_file(retained.zip_path, MAX_ARCHIVE_BYTES)
        result = PublicationBundle(canonical_json(artifact.to_dict()), retained.manifest_bytes,
                                   archive, retained.member_names)
        result.validate()
        return result
    finally:
        if connection is not None:
            connection.close()
        os.close(descriptor)


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
    match = re.search(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?$", remote)
    if match is None or match.group(1).removesuffix(".git") != "Dimkox/adaptive-grok-build-pro":
        raise PublicationError("publication_control_repository")
    head = git_head(control_root)
    fingerprint = tree_fingerprint(control_root)
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
            "scope": "production", "actions": ["external-write"],
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
            if created.tzinfo is None or expires.tzinfo is None or not created <= now < expires:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        matches.append(grant)
    if len(matches) != 1:
        raise PublicationError("publication_exact_grant_unavailable")
    return hashlib.sha256(canonical_json(matches[0])).hexdigest()


def main(argv=None, *, control_root: Path | None = None) -> int:
    from adaptive_delivery.landing_filesystem import FilesystemLandingPublisher
    from adaptive_delivery.landing_publication import LandingPublicationCoordinator, PublicationStore
    from adaptive_delivery.landing_publication_contracts import PublicationError

    root = control_root or Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Exact local-filesystem landing publication; disabled by default")
    parser.add_argument("phase", choices=("prepare", "apply", "reconcile", "status", "observe"))
    parser.add_argument("--config", required=True)
    parser.add_argument("--action", choices=("stage", "activate", "restore"))
    parser.add_argument("--request-id")
    parser.add_argument("--request-digest")
    parser.add_argument("--job-id")
    parser.add_argument("--restore-from")
    parser.add_argument("--live", action="store_true")
    arguments = parser.parse_args(argv)
    store = None
    try:
        if arguments.phase == "apply" and not arguments.live:
            raise PublicationError("publication_live_disabled")
        config, target = _config(arguments.config, root)
        adapter = FilesystemLandingPublisher(target)
        if arguments.phase == "observe":
            result = adapter.observe()
        else:
            store = PublicationStore(Path(config["publication_state_root"]),
                                     readonly=arguments.phase == "status")
            coordinator = LandingPublicationCoordinator(
                store, adapter, lambda reference: _bundle(config, target, reference)
            )
            if arguments.phase == "prepare":
                if arguments.action is None or arguments.request_id is None:
                    raise PublicationError("publication_prepare_arguments")
                reference = None
                if arguments.action != "restore":
                    if not arguments.job_id:
                        raise PublicationError("publication_job_required")
                    reference = {"tenant_id": config["tenant_id"], "repository_id": config["repository_id"],
                                 "job_id": arguments.job_id}
                result = coordinator.prepare(request_id=arguments.request_id, action=arguments.action,
                                              artifact_ref=reference, restore_from=arguments.restore_from)
            elif arguments.phase == "apply":
                result = coordinator.apply(arguments.request_digest,
                                             lambda request: _authority(config, root, request))
            elif arguments.phase == "reconcile":
                result = coordinator.reconcile(arguments.request_digest)
            else:
                result = store.get(arguments.request_digest)
        print(canonical_json(result).decode("utf-8"))
        return 0
    except Exception as exc:
        reason = str(exc) if isinstance(exc, PublicationError) else "publication_unavailable"
        print(canonical_json({"schema_version": 1, "state": "unavailable", "reason": reason}).decode())
        return 2
    finally:
        if store is not None:
            store.close()


if __name__ == "__main__":
    raise SystemExit(main())
