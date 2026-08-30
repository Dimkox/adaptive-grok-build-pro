from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta
from pathlib import Path

from .api import create_app
from .backup import create_backup, prune_backups, restore_drill, verify_backup
from .github import GitHubClient
from .github_app import generate_app_jwt
from .holdout import bundle_digest, verify_bundle
from .migrations import PostgresMigrator
from .models import (
    ApprovalEnvelope,
    ApprovalPayload,
    AttestationEnvelope,
    PromotionEnvelope,
    PromotionExpectedBinding,
    PromotionPayload,
    parse_datetime,
    utc_now,
)
from .policy import Policy
from .settings import ApiSettings, CommonSettings, WorkerSettings
from .signing import (
    PromotionError,
    Signer,
    TrustStore,
    sign_approval,
    sign_promotion,
    verify_approval,
    verify_attestation,
    verify_promotion,
)
from .store import PostgresStore
from .worker import Worker, install_signal_handlers


class NoPromotionRedirects(urllib.request.HTTPRedirectHandler):
    """Never forward a signed envelope or idempotency key to a redirect target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='adaptive-trust-ci')
    sub = parser.add_subparsers(dest='command', required=True)

    api = sub.add_parser('api', help='Run the webhook and approval API')
    api.add_argument('--host', default='127.0.0.1')
    api.add_argument('--port', type=int, default=8080)

    worker = sub.add_parser('worker', help='Run a durable Trust CI worker')
    worker.add_argument('--once', action='store_true')

    sub.add_parser('migrate', help='Apply pending checksum-locked PostgreSQL migrations')
    sub.add_parser('migration-status', help='Report applied and pending migrations')
    sub.add_parser('policy-digest', help='Print the authoritative policy digest')
    sub.add_parser('doctor', help='Validate policy, database and role-specific files')

    holdout = sub.add_parser('holdout-digest', help='Print deterministic digest of a trusted holdout directory')
    holdout.add_argument('--path', required=True, type=Path)

    keygen = sub.add_parser('keygen', help='Generate an Ed25519 key pair')
    keygen.add_argument('--private', required=True, type=Path)
    keygen.add_argument('--public', required=True, type=Path)

    trust_store = sub.add_parser('trust-store-validate', help='Validate key lifecycle, revocation and scopes')
    trust_store.add_argument('--trust-store', required=True, type=Path)

    approval = sub.add_parser('approval-create', help='Create a human-signed exact-SHA approval')
    approval.add_argument('--private-key', required=True, type=Path)
    approval.add_argument('--policy', required=True, type=Path)
    approval.add_argument('--actor', required=True)
    approval.add_argument('--repository', required=True)
    approval.add_argument('--pr-number', required=True, type=int)
    approval.add_argument('--base-sha', required=True)
    approval.add_argument('--head-sha', required=True)
    approval.add_argument('--scope', required=True)
    approval.add_argument('--reason', required=True)
    approval.add_argument('--ttl', type=int, default=900, help='Approval lifetime in seconds')
    approval.add_argument('--output', required=True, type=Path)

    verify = sub.add_parser('approval-verify', help='Verify an approval envelope offline')
    verify.add_argument('--approval', required=True, type=Path)
    verify.add_argument('--trust-store', required=True, type=Path)
    verify.add_argument('--policy', required=True, type=Path)
    verify.add_argument('--repository', required=True)
    verify.add_argument('--pr-number', required=True, type=int)
    verify.add_argument('--base-sha', required=True)
    verify.add_argument('--head-sha', required=True)

    submit = sub.add_parser('approval-submit', help='Submit a signed approval to the API')
    submit.add_argument('--approval', required=True, type=Path)
    submit.add_argument('--url', required=True, help='Base URL, for example https://ci.example.com')

    promotion = sub.add_parser(
        'promotion-create', help='Create an offline human-signed production promotion'
    )
    promotion.add_argument('--private-key', required=True, type=Path)
    promotion.add_argument('--output', required=True, type=Path)
    promotion.add_argument('--schema-version', required=True, type=int)
    promotion.add_argument('--promotion-id', required=True)
    promotion.add_argument('--nonce', required=True)
    promotion.add_argument('--actor', required=True)
    promotion.add_argument('--key-id', required=True)
    promotion.add_argument('--repository', required=True)
    promotion.add_argument('--merged-commit-sha', required=True)
    promotion.add_argument('--artifact-sha256', required=True)
    promotion.add_argument('--target-environment', required=True)
    promotion.add_argument('--policy-epoch', required=True)
    promotion.add_argument('--source-attestation-id', required=True)
    promotion.add_argument('--reason', required=True)
    promotion.add_argument('--issued-at', required=True)
    promotion.add_argument('--expires-at', required=True)

    promotion_verify = sub.add_parser(
        'promotion-verify', help='Verify a promotion envelope entirely offline'
    )
    promotion_verify.add_argument('--promotion', required=True, type=Path)
    promotion_verify.add_argument('--trust-store', required=True, type=Path)
    promotion_verify.add_argument('--repository', required=True)
    promotion_verify.add_argument('--merged-commit-sha', required=True)
    promotion_verify.add_argument('--artifact-sha256', required=True)
    promotion_verify.add_argument('--target-environment', required=True)
    promotion_verify.add_argument('--policy-epoch', required=True)
    promotion_verify.add_argument('--source-attestation-id', required=True)
    promotion_verify.add_argument('--max-ttl-seconds', required=True, type=int)

    promotion_submit = sub.add_parser(
        'promotion-submit', help='Submit one existing promotion envelope without refreshing it'
    )
    promotion_submit.add_argument('--promotion', required=True, type=Path)
    promotion_submit.add_argument('--url', required=True)
    promotion_submit.add_argument('--idempotency-key', required=True)
    promotion_submit.add_argument('--correlation-id', required=True)
    promotion_submit.add_argument('--timeout-seconds', type=int, default=10)

    attest = sub.add_parser('attestation-verify', help='Verify a signed CI attestation offline')
    attest.add_argument('--attestation', required=True, type=Path)
    attest.add_argument('--public-key', required=True, type=Path)

    protect = sub.add_parser('branch-protect', help='Bind required exact-SHA status to a GitHub App')
    protect.add_argument('--repository', required=True)
    protect.add_argument('--branch', default='main')
    protect.add_argument('--required-reviews', type=int, default=0)
    protect.add_argument('--context', help='Exact policy-epoch check name; defaults to policy.check_name')
    protect.add_argument('--policy', type=Path)
    protect.add_argument('--app-id', type=int)
    protect.add_argument('--previous-context', help='Current exact policy-epoch check name for add-before-remove cutover')
    protect.add_argument('--previous-app-id', type=int, help='GitHub App ID owning --previous-context')

    backup = sub.add_parser('backup-create', help='Create an integrity-checked custom-format PostgreSQL backup')
    backup.add_argument('--output-dir', type=Path)
    backup.add_argument('--database-label', required=True)

    backup_verify = sub.add_parser('backup-verify', help='Verify backup size and SHA-256 manifest')
    backup_verify.add_argument('--dump', required=True, type=Path)
    backup_verify.add_argument('--manifest', required=True, type=Path)

    backup_prune = sub.add_parser('backup-prune', help='Delete only verified backups outside retention policy')
    backup_prune.add_argument('--directory', type=Path)
    backup_prune.add_argument('--keep-last', type=int, default=14)
    backup_prune.add_argument('--max-age-days', type=int, default=30)

    restore = sub.add_parser('restore-drill', help='Restore a backup into an explicitly disposable database')
    restore.add_argument('--dump', required=True, type=Path)
    restore.add_argument('--manifest', required=True, type=Path)
    restore.add_argument('--confirm-disposable', action='store_true')

    kill = sub.add_parser('kill-switch', help='Manage the server-side emergency stop')
    kill.add_argument('action', choices=['on', 'off', 'status'])

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == 'api':
        import uvicorn

        settings = ApiSettings.load()
        uvicorn.run(create_app(settings), host=args.host, port=args.port, access_log=True)
        return 0

    if args.command == 'worker':
        worker = Worker.build(WorkerSettings.load())
        install_signal_handlers(worker)
        return worker.run(once=args.once)

    if args.command == 'migrate':
        settings = CommonSettings.load()
        plan = PostgresMigrator(settings.database_url).apply()
        print(json.dumps({'status': 'schema-applied', **plan.to_dict()}, ensure_ascii=False, indent=2))
        return 0

    if args.command == 'migration-status':
        settings = CommonSettings.load()
        plan = PostgresMigrator(settings.database_url).status()
        print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
        return 1 if plan.pending else 0

    if args.command == 'policy-digest':
        settings = CommonSettings.load()
        print(Policy.load(settings.policy_path).digest)
        return 0

    if args.command == 'holdout-digest':
        print(bundle_digest(args.path))
        return 0

    if args.command == 'doctor':
        return _doctor()

    if args.command == 'keygen':
        signer = Signer.generate()
        signer.write_keypair(args.private, args.public)
        print(json.dumps({'key_id': signer.key_id, 'private': str(args.private), 'public': str(args.public)}))
        return 0

    if args.command == 'trust-store-validate':
        report = TrustStore.load(args.trust_store).report(utc_now())
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if not any(item['status'] == 'active' for item in report['keys']) else 0

    if args.command == 'approval-create':
        policy = Policy.load(args.policy)
        if args.scope not in policy.approval_scopes:
            raise SystemExit(f'scope is not configured by policy: {args.scope}')
        if args.ttl > policy.max_approval_ttl_seconds:
            raise SystemExit('requested TTL exceeds policy')
        signer = Signer.from_private_file(args.private_key)
        payload = ApprovalPayload.new(
            actor=args.actor,
            key_id=signer.key_id,
            repository=args.repository,
            pr_number=args.pr_number,
            base_sha=args.base_sha,
            head_sha=args.head_sha,
            policy_digest=policy.digest,
            scope=args.scope,
            reason=args.reason,
            ttl_seconds=args.ttl,
        )
        envelope = sign_approval(payload, signer)
        _write_new_json(args.output, envelope.to_dict(), mode=0o600)
        print(json.dumps({'approval_id': payload.approval_id, 'key_id': signer.key_id, 'output': str(args.output)}))
        return 0

    if args.command == 'approval-verify':
        policy = Policy.load(args.policy)
        envelope = ApprovalEnvelope.from_dict(_read_json(args.approval))
        verified = verify_approval(
            envelope,
            TrustStore.load(args.trust_store),
            expected_repository=args.repository,
            expected_pr_number=args.pr_number,
            expected_base_sha=args.base_sha,
            expected_head_sha=args.head_sha,
            expected_policy_digest=policy.digest,
            now=utc_now(),
            max_ttl_seconds=policy.max_approval_ttl_seconds,
        )
        print(json.dumps(verified.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == 'approval-submit':
        payload = args.approval.read_bytes()
        request = urllib.request.Request(
            args.url.rstrip('/') + '/approvals',
            data=payload,
            method='POST',
            headers={'Content-Type': 'application/json', 'User-Agent': 'adaptive-trust-ci-human/2.1.0'},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                sys.stdout.buffer.write(response.read())
                sys.stdout.write('\n')
        except urllib.error.HTTPError as exc:
            sys.stderr.buffer.write(exc.read())
            return 1
        return 0

    if args.command == 'promotion-create':
        return _promotion_create(args)

    if args.command == 'promotion-verify':
        return _promotion_verify(args)

    if args.command == 'promotion-submit':
        return _promotion_submit(args)

    if args.command == 'attestation-verify':
        envelope = AttestationEnvelope.from_dict(_read_json(args.attestation))
        verified = verify_attestation(envelope, args.public_key.read_bytes())
        print(json.dumps(verified.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == 'branch-protect':
        policy_path = args.policy or _required_path_env('TRUST_CI_POLICY_PATH')
        if not policy_path.is_file():
            raise SystemExit('--policy or TRUST_CI_POLICY_PATH must name the deployed policy')
        policy = Policy.load(policy_path)
        check_name = args.context or policy.check_name
        app_id = args.app_id or _required_int_env('TRUST_CI_GITHUB_APP_ID')
        admin_token = os.environ.get('TRUST_CI_GITHUB_ADMIN_TOKEN', '').strip()
        if not admin_token:
            raise SystemExit('TRUST_CI_GITHUB_ADMIN_TOKEN is required only for this administration command')
        github = GitHubClient(token=admin_token)
        if bool(args.previous_context) != bool(args.previous_app_id):
            raise SystemExit('--previous-context and --previous-app-id must be provided together')
        if args.previous_context:
            result = github.cutover_branch_protection(
                args.repository, args.branch,
                old_check_name=args.previous_context, old_app_id=args.previous_app_id,
                new_check_name=check_name, new_app_id=app_id,
                required_reviews=args.required_reviews,
            )
        else:
            result = github.configure_branch_protection(
                args.repository, args.branch, check_name=check_name, app_id=app_id,
                required_reviews=args.required_reviews,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == 'backup-create':
        settings = CommonSettings.load()
        output_dir = args.output_dir.resolve() if args.output_dir else _required_path_env('TRUST_CI_BACKUP_DIR')
        result = create_backup(
            settings.database_url,
            output_dir,
            database_label=args.database_label,
        )
        print(
            json.dumps(
                {
                    'dump_path': str(result.dump_path),
                    'manifest_path': str(result.manifest_path),
                    'sha256': result.sha256,
                    'size_bytes': result.size_bytes,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == 'backup-verify':
        print(json.dumps(verify_backup(args.dump, args.manifest), ensure_ascii=False, indent=2))
        return 0

    if args.command == 'backup-prune':
        directory = args.directory.resolve() if args.directory else _required_path_env('TRUST_CI_BACKUP_DIR')
        report = prune_backups(
            directory,
            keep_last=args.keep_last,
            max_age_days=args.max_age_days,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if args.command == 'restore-drill':
        target = os.environ.get('TRUST_CI_RESTORE_DATABASE_URL', '').strip()
        if not target:
            raise SystemExit('TRUST_CI_RESTORE_DATABASE_URL is required for a disposable restore target')
        report = restore_drill(
            target,
            args.dump,
            args.manifest,
            confirm_disposable=args.confirm_disposable,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if args.command == 'kill-switch':
        settings = CommonSettings.load()
        path = settings.kill_switch_path
        if args.action == 'status':
            print('on' if path.exists() else 'off')
            return 0
        if args.action == 'on':
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text(f'stopped_at={utc_now().isoformat()}\n', encoding='utf-8')
                os.chmod(path, 0o600)
            print('on')
            return 0
        path.unlink(missing_ok=True)
        print('off')
        return 0

    raise AssertionError(args.command)


def _doctor() -> int:
    role = os.environ.get('TRUST_CI_ROLE', 'all').strip().lower()
    common = CommonSettings.load()
    policy = Policy.load(common.policy_path)
    checks: list[dict[str, str]] = [
        {'name': 'policy', 'status': 'pass', 'detail': policy.digest},
        {'name': 'required-check', 'status': 'pass', 'detail': policy.check_name},
        {'name': 'kill-switch', 'status': 'warn' if common.stopped else 'pass', 'detail': str(common.kill_switch_path)},
    ]
    try:
        actual_holdout = verify_bundle(policy.holdout.path, policy.holdout.digest)
        checks.append({'name': 'holdout', 'status': 'pass', 'detail': actual_holdout})
    except Exception as exc:
        checks.append({'name': 'holdout', 'status': 'fail', 'detail': str(exc)})
    try:
        PostgresStore(common.database_url).ping()
        checks.append({'name': 'postgres', 'status': 'pass', 'detail': 'reachable'})
        migrations = PostgresMigrator(common.database_url).status()
        checks.append(
            {
                'name': 'migrations',
                'status': 'fail' if migrations.pending else 'pass',
                'detail': f'applied={len(migrations.applied)} pending={len(migrations.pending)}',
            }
        )
    except Exception as exc:
        checks.append({'name': 'postgres', 'status': 'fail', 'detail': str(exc)})
    if role in {'all', 'api'}:
        api = ApiSettings.load()
        trust_store = TrustStore.load(api.trust_store_path)
        report = trust_store.report(utc_now())
        active_keys = sum(1 for item in report['keys'] if item['status'] == 'active')
        checks.append(
            {
                'name': 'trust-store',
                'status': 'pass' if active_keys else 'fail',
                'detail': f'{api.trust_store_path}; active_keys={active_keys}',
            }
        )
    if role in {'all', 'worker'}:
        worker = WorkerSettings.load()
        signer = Signer.from_private_file(worker.ci_signing_key_path)
        checks.append({'name': 'ci-signer', 'status': 'pass', 'detail': signer.key_id})
        checks.append(
            {
                'name': 'runner-image',
                'status': 'pass' if worker.runner_image == policy.sandbox.image else 'fail',
                'detail': worker.runner_image,
            }
        )
        try:
            generate_app_jwt(worker.github_app_id, worker.github_app_private_key_path.read_bytes(), now=utc_now())
            checks.append({'name': 'github-app-key', 'status': 'pass', 'detail': str(worker.github_app_id)})
        except Exception as exc:
            checks.append({'name': 'github-app-key', 'status': 'fail', 'detail': str(exc)})
        runtime = policy.sandbox.runtime
        found = any((Path(directory) / runtime).is_file() for directory in os.environ.get('PATH', '').split(os.pathsep))
        checks.append({'name': 'sandbox-runtime', 'status': 'pass' if found else 'fail', 'detail': runtime})
    print(json.dumps({'checks': checks}, ensure_ascii=False, indent=2))
    return 1 if any(item['status'] == 'fail' for item in checks) else 0


def _required_int_env(name: str) -> int:
    raw = os.environ.get(name, '').strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f'{name} must be a positive integer') from exc
    if value <= 0:
        raise SystemExit(f'{name} must be a positive integer')
    return value


def _required_path_env(name: str) -> Path:
    raw = os.environ.get(name, '').strip()
    if not raw:
        raise SystemExit(f'{name} is required')
    return Path(raw).expanduser().resolve()


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f'cannot read JSON file {path}: {exc}') from exc
    if not isinstance(data, dict):
        raise SystemExit(f'JSON root must be an object: {path}')
    return data


def _write_new_json(path: Path, data: dict, *, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, mode)
    except FileExistsError as exc:
        raise SystemExit(f'refusing to overwrite existing file: {path}') from exc
    with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())


def _promotion_create(args: argparse.Namespace) -> int:
    try:
        if '\n' in str(args.private_key) or 'PRIVATE KEY' in str(args.private_key).upper():
            raise ValueError
        signer = Signer.from_private_pem(
            _read_secure_regular_file(args.private_key, 16 * 1024, private=True)
        )
        payload = PromotionPayload(
            schema_version=args.schema_version,
            promotion_id=args.promotion_id,
            nonce=args.nonce,
            actor=args.actor,
            key_id=args.key_id,
            repository=args.repository,
            merged_commit_sha=args.merged_commit_sha,
            artifact_sha256=args.artifact_sha256,
            target_environment=args.target_environment,
            policy_epoch=args.policy_epoch,
            source_attestation_id=args.source_attestation_id,
            reason=args.reason,
            issued_at=args.issued_at,
            expires_at=args.expires_at,
        )
        issued = parse_datetime(payload.issued_at)
        expires = parse_datetime(payload.expires_at)
        current = utc_now()
        if (
            issued - current > timedelta(seconds=60)
            or current >= expires
            or (expires - issued).total_seconds() > 3600
        ):
            raise ValueError
        envelope = sign_promotion(payload, signer)
        _write_atomic_new_json(args.output, envelope.to_dict())
    except (Exception, SystemExit):
        print('promotion-create failed: invalid local input', file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                'promotion_id': payload.promotion_id,
                'key_id': payload.key_id,
                'output': str(args.output),
            },
            separators=(',', ':'),
        )
    )
    return 0


def _promotion_verify(args: argparse.Namespace) -> int:
    try:
        envelope = PromotionEnvelope.from_dict(_read_bounded_json(args.promotion, 16 * 1024))
        expected = PromotionExpectedBinding(
            repository=args.repository,
            merged_commit_sha=args.merged_commit_sha,
            artifact_sha256=args.artifact_sha256,
            target_environment=args.target_environment,
            policy_epoch=args.policy_epoch,
            source_attestation_id=args.source_attestation_id,
        )
        trust_store = TrustStore.load(args.trust_store)
        verified = verify_promotion(
            envelope,
            trust_store,
            expected,
            utc_now(),
            args.max_ttl_seconds,
        )
    except PromotionError:
        print('promotion-verify failed: authorization rejected', file=sys.stderr)
        return 3
    except (Exception, SystemExit):
        print('promotion-verify failed: invalid local input', file=sys.stderr)
        return 2
    print(
        json.dumps(
            {'promotion_id': verified.promotion_id, 'key_id': verified.key_id, 'valid': True},
            separators=(',', ':'),
        )
    )
    return 0


def _promotion_submit(args: argparse.Namespace) -> int:
    try:
        payload = _read_bounded_bytes(args.promotion, 16 * 1024)
        PromotionEnvelope.from_dict(
            json.loads(payload.decode('utf-8'), object_pairs_hook=_strict_cli_object)
        )
        _require_cli_header(args.idempotency_key, 16, 128)
        _require_cli_header(args.correlation_id, 1, 128)
        if type(args.timeout_seconds) is not int or not 1 <= args.timeout_seconds <= 30:
            raise ValueError
        parsed = urllib.parse.urlsplit(args.url)
        if (
            parsed.scheme != 'https'
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError
        endpoint = args.url.rstrip('/') + '/promotions'
        request = urllib.request.Request(
            endpoint,
            data=payload,
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'Idempotency-Key': args.idempotency_key,
                'X-Correlation-ID': args.correlation_id,
                'User-Agent': 'adaptive-trust-ci-human/2.1.0',
            },
        )
    except (Exception, SystemExit):
        print('promotion-submit failed: invalid local input', file=sys.stderr)
        return 2
    try:
        with _open_promotion_request(request, timeout=args.timeout_seconds) as response:
            raw = _read_bounded_response(response)
            status = int(getattr(response, 'status', 0))
    except urllib.error.HTTPError as exc:
        status = exc.code
        try:
            raw = _read_bounded_response(exc)
        except ValueError:
            raw = b''
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        print('promotion-submit failed: dependency unavailable', file=sys.stderr)
        return 5
    if status in {200, 201}:
        _print_bounded_response(status, raw)
        return 0
    if status == 409:
        _print_bounded_response(status, raw, stream=sys.stderr)
        return 4
    if status in {400, 401, 403, 422}:
        _print_bounded_response(status, raw, stream=sys.stderr)
        return 3
    _print_bounded_response(status, raw, stream=sys.stderr)
    return 5


def _read_bounded_bytes(path: Path, maximum: int) -> bytes:
    raw = _read_secure_regular_file(path, maximum)
    if not raw or len(raw) > maximum:
        raise ValueError
    return raw


def _open_promotion_request(request: urllib.request.Request, *, timeout: int):
    opener = urllib.request.build_opener(
        NoPromotionRedirects(), urllib.request.ProxyHandler({})
    )
    return opener.open(request, timeout=timeout)


def _read_secure_regular_file(
    path: Path, maximum: int, *, private: bool = False
) -> bytes:
    if type(maximum) is not int or maximum <= 0:
        raise ValueError
    required_flags = ('O_NOFOLLOW', 'O_CLOEXEC', 'O_NONBLOCK')
    if any(not hasattr(os, name) for name in required_flags):
        raise OSError('secure file-open flags are unavailable')
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
    descriptor = os.open(os.fspath(path), flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > maximum:
            raise ValueError
        if private and (
            metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise ValueError
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(remaining, 64 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b''.join(chunks)
        if len(raw) > maximum:
            raise ValueError
        return raw
    finally:
        os.close(descriptor)


def _read_bounded_json(path: Path, maximum: int) -> dict:
    raw = _read_bounded_bytes(path, maximum)
    data = json.loads(raw.decode('utf-8'), object_pairs_hook=_strict_cli_object)
    if not isinstance(data, dict):
        raise ValueError
    return data


def _require_cli_header(value: str, minimum: int, maximum: int) -> None:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or not minimum <= len(value.encode('utf-8')) <= maximum
        or ',' in value
        or any(ord(character) < 33 or ord(character) > 126 for character in value)
    ):
        raise ValueError


def _read_bounded_response(response: object) -> bytes:
    raw = response.read(64 * 1024 + 1)
    if len(raw) > 64 * 1024:
        raise ValueError
    return raw


def _print_bounded_response(status: int, raw: bytes, *, stream=None) -> None:
    allowed = {
        'promotion_id', 'operation_id', 'correlation_id', 'code', 'status',
        'consumed', 'idempotent_replay', 'expires_at', 'policy_epoch',
        'repository', 'merged_commit_sha', 'artifact_sha256',
        'target_environment', 'source_attestation_id',
    }
    try:
        parsed = (
            json.loads(raw.decode('utf-8'), object_pairs_hook=_strict_cli_object)
            if raw
            else {}
        )
        if not isinstance(parsed, dict):
            raise ValueError
        bounded = {
            key: value
            for key, value in parsed.items()
            if key in allowed
            and isinstance(value, (str, int, bool))
            and len(str(value).encode('utf-8')) <= 512
        }
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        bounded = {}
    print(
        json.dumps({'http_status': status, **bounded}, separators=(',', ':')),
        file=stream or sys.stdout,
    )


def _strict_cli_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _write_atomic_new_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f'.{path.name}.', suffix='.tmp', dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
            descriptor = -1
            json.dump(data, handle, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(main())
