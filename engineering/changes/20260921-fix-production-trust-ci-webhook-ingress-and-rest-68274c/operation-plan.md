# Reviewed operation candidate — not activated

Route `68274cb876e4`. This plan installs four new host files and manages only their three units, one enablement symlink, and the dedicated nft table. The parent coordinator owns exact grants and execution after independent code, test, security, and release review. Preparation executed no installation, daemon reload, enablement, start, stop, GitHub write, or webhook POST.

The reviewed files are in `/home/pall/.cache/agbp-run/issues-wave-20260921/ci-ingress/artifacts/`. [The manifest](evidence/artifact-manifest.json) gives every source, destination, byte count, and SHA-256. The manifest SHA-256 is `b4b45a7c453812942cbc33a2b88239613be7079435a445c9b208ab00f54f714d`. [Static evidence](evidence/preparation-verification.json) records what actually ran.

## Resource and authority boundary

| Resource | Allowed operation |
| --- | --- |
| `/etc/systemd/system/adaptive-trust-ci-webhook-bridge.socket` | Create only when absent; later remove only this installed file |
| `/etc/systemd/system/adaptive-trust-ci-webhook-bridge.service` | Same |
| `/etc/systemd/system/adaptive-trust-ci-webhook-bridge-guard.service` | Same |
| `/etc/adaptive-trust-ci-webhook-bridge.nft` | Same |
| `adaptive-trust-ci-webhook-bridge.socket` | Start, stop, enable, disable |
| `adaptive-trust-ci-webhook-bridge.service` | Socket activation and stop; no independent enablement |
| `adaptive-trust-ci-webhook-bridge-guard.service` | Start and stop; no independent enablement |
| `/etc/systemd/system/multi-user.target.wants/adaptive-trust-ci-webhook-bridge.socket` | Create/remove through exact socket enable/disable |
| nft `inet adaptive_trust_ci_webhook_bridge` | Create/remove through the guard only |
| systemd manager | `daemon-reload` to read/remove only the named files; no manager reexec |

Existing `wg-vpn-namespace.service`, veth interfaces, addresses, routes, Tailscale configuration, Docker/API/worker services, database, deployed policy/holdout/images, trust stores, and credentials receive no writes. The new units require the already active namespace unit; initial preflight refuses an inactive or changed namespace unit. At boot the socket depends on the existing namespace creator. Explicit recovery starts only the bridge after the namespace is healthy; this plan never restarts or recreates the namespace itself.

## Ordering and network behavior

The guard installs the nft file as one transaction. `create table` fails if that name already exists; it never flushes or takes over a table. The chain has policy `accept`, with three rules limited to destination `10.200.200.1`, TCP port `18080`: wrong interface drops first; wrong source drops second; the verified interface and peer have a counted accept rule. Other traffic has no drop rule in this table. No `IPAddressAllow` claim is made because this systemd build lacks BPF support.

The socket uses only `10.200.200.1:18080`, `BindToDevice=veth-vpn-h`, and `Accept=no`. `BindsTo` and `After` tie it to the guard and namespace; device binding adds its device dependency. Both proxy and socket depend on the guard, and the proxy follows the socket, so a guard stop transaction stops the proxy and socket before deleting the table. The guard itself binds to the verified veth device and existing namespace unit. An external root-level firewall deletion is outside this dependency guarantee; inspect the table during every acceptance.

The socket deliberately uses `DefaultDependencies=no`: an ordinary network/guard service starts after `basic.target`, whereas a default socket would be ordered before `sockets.target`, creating a boot ordering cycle. The unit restores explicit sysinit and shutdown dependencies and enables under `multi-user.target`. Static systemd validation found no cycle; cold-boot behavior remains untested. Device loss stops the bridge; device return needs explicit bridge reactivation after namespace health, and is not claimed as automatic recovery.

The service runs the installed `systemd-socket-proxyd 127.0.0.1:18080` with a dynamic user, no capabilities, and filesystem/kernel hardening. It remains in the host network namespace; no `PrivateNetwork`, namespace path, or wildcard bind is configured. It forwards bytes for every API path reachable by the allowed peer. Existing Funnel's sole public handler remains `/webhooks/github`; path isolation and backend HMAC/authentication remain separate boundaries.

## 1. Refresh preflight and exact bytes

Run from the stage directory for the checksum file. Refuse a hash difference and return changed bytes to the same writer and reviewers.

```bash
sha256sum --check SHA256SUMS
sudo -n true
systemctl show wg-vpn-namespace.service --property=Id,LoadState,ActiveState,SubState,Type,RemainAfterExit
ip -json address show dev veth-vpn-h
sudo -n ip -n vpn -json address show dev veth-vpn-n
sudo -n ip -n vpn -json route get 10.200.200.1 from 100.119.249.65
sudo -n ip netns exec vpn tailscale serve status --json
ss -H -lnt sport = :18080
curl --noproxy '*' --silent --show-error --connect-timeout 2 --max-time 5 --output /dev/null --write-out '%{http_code}\n' http://127.0.0.1:18080/health/ready
```

Require the namespace unit `active/exited`, `Type=oneshot`, `RemainAfterExit=yes`; host `veth-vpn-h` UP at `10.200.200.1/30`; actual peer `veth-vpn-n` UP at `10.200.200.2/30` with reciprocal link indexes; only loopback port 18080 listening; readiness 200. Confirm source `100.119.249.65` still belongs to namespace `vpn` and its route uses `veth-vpn-n`. The Funnel JSON must still have exactly its known HTTPS 443 handler `/webhooks/github` → `http://10.200.200.1:18080/webhooks/github` with that host's Funnel enabled. Any topology/configuration difference needs reassessment; do not adjust existing resources to force this candidate to fit.

The following **installation command** repeats name-conflict and firewall checks immediately before exclusive file creation. It verifies the pinned manifest and all four payloads before writing. A collision refuses instead of overwriting. Run it only after the parent has recorded the exact operational grant.

```bash
sudo -n python3 -B - <<'PY'
import hashlib, json, os, pathlib, subprocess
root = pathlib.Path('/home/pall/.cache/agbp-run/issues-wave-20260921/ci-ingress')
manifest_bytes = (root / 'artifact-manifest.json').read_bytes()
assert hashlib.sha256(manifest_bytes).hexdigest() == 'b4b45a7c453812942cbc33a2b88239613be7079435a445c9b208ab00f54f714d'
files = json.loads(manifest_bytes)['installed_files']
unit_paths = subprocess.check_output(['systemd-analyze', 'unit-paths'], text=True).splitlines()
for name in files:
    if name.endswith('.nft'):
        continue
    assert subprocess.check_output(['systemctl', 'show', name, '-p', 'LoadState', '--value'], text=True).strip() == 'not-found', name
    for parent in map(pathlib.Path, unit_paths):
        assert not os.path.lexists(parent / name) and not os.path.lexists(parent / (name + '.d')), name
        for pattern in ('*.wants/' + name, '*.requires/' + name, '*.upholds/' + name):
            assert not list(parent.glob(pattern)), name
rules = json.loads(subprocess.check_output(['nft', '-json', 'list', 'ruleset'], text=True))['nftables']
assert not any(x.get('table', {}).get('name') == 'adaptive_trust_ci_webhook_bridge' for x in rules)
assert not any(x.get('chain', {}).get('hook') == 'input' for x in rules), 'Input firewall topology changed'
payloads = {}
for name, entry in files.items():
    payloads[name] = pathlib.Path(entry['source']).read_bytes()
    assert hashlib.sha256(payloads[name]).hexdigest() == entry['sha256'], name
    assert not os.path.lexists(entry['destination']), entry['destination']
created = []
try:
    for name, entry in files.items():
        path = pathlib.Path(entry['destination'])
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
        with os.fdopen(fd, 'wb') as handle:
            identity = os.fstat(handle.fileno())
            created.append((path, identity.st_dev, identity.st_ino))
            handle.write(payloads[name])
            handle.flush()
            os.fsync(handle.fileno())
            os.fchmod(handle.fileno(), 0o644)
except BaseException:
    for path, device, inode in reversed(created):
        if path.exists() and (path.stat().st_dev, path.stat().st_ino) == (device, inode):
            path.unlink()
    raise
print(json.dumps({'installed_only': [str(path) for path, _, _ in created], 'activated': False}))
PY
```

## 2. Activate in guarded order

Before activation, refresh the healthy topology and ensure the unchanged installed file hashes match the manifest. The syntax checks below are bounded; `nft --check` performs no mutation and must precede creating the table.

```bash
sudo -n systemd-analyze verify /etc/systemd/system/adaptive-trust-ci-webhook-bridge.socket /etc/systemd/system/adaptive-trust-ci-webhook-bridge.service /etc/systemd/system/adaptive-trust-ci-webhook-bridge-guard.service
sudo -n nft --check --file /etc/adaptive-trust-ci-webhook-bridge.nft
sudo -n systemctl daemon-reload
```

**Mandatory gate after `daemon-reload` and before any unit start:** the earlier exact-name directory scan cannot detect every effective override. Systemd also loads dash-prefix directories such as `adaptive-.service.d/` and type-wide `service.d/` or `socket.d/`. For all three units, require `LoadState=loaded`, `ActiveState=inactive`, empty effective `DropInPaths`, and `FragmentPath` equal to the exact installed `/etc/systemd/system/<unit>` path. A missing property, inherited override, unexpected fragment, command, listener, or dependency stops the operation before any start and returns it to independent review. Do not read or change override contents, environment properties, credential properties, or foreign files to make the check pass. Previously collected pre-install `not-found` properties do not satisfy this gate.

The following read-only gate uses narrowly selected `systemctl show` properties. It checks all unit identities before asking for command properties, then compares the effective configuration. Effective `Wants` and `Upholds` must both be empty: outgoing `<unit>.wants/*` or `<unit>.upholds/*` links can start unrelated units without a drop-in and are not covered by the initial incoming-link scan. Effective `Requires` is constrained separately. The final `effective_unit_gate=pass` is required; an exception, nonzero exit, missing output, or unrecognized dependency is a refusal. Keep the effective-property output with the operation evidence. Repeat this gate before reactivation and after any later daemon reload while the bridge is stopped; changed definitions need fresh review, not a wider allowlist.

```bash
python3 -B - <<'PY'
import json, re, subprocess
prefix = 'adaptive-trust-ci-webhook-bridge'
socket = prefix + '.socket'
proxy = prefix + '.service'
guard = prefix + '-guard.service'
device = r'sys-subsystem-net-devices-veth\x2dvpn\x2dh.device'
namespace = 'wg-vpn-namespace.service'
units = (socket, proxy, guard)
def require(condition, reason):
    if not condition:
        raise SystemExit('effective_unit_gate=REFUSED: ' + reason)
def show(unit, names):
    result = subprocess.run(['systemctl', 'show', '--all', '--property=' + ','.join(names), unit], capture_output=True, text=True, timeout=10, check=True)
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
identity_fields = ('Id', 'LoadState', 'ActiveState', 'FragmentPath', 'DropInPaths')
for unit in units:
    values = show(unit, identity_fields)
    require(all(field in values for field in identity_fields), unit + ': missing identity property')
    require(values['Id'] == unit and values['LoadState'] == 'loaded' and values['ActiveState'] == 'inactive', unit + ': identity/state differs')
    require(values['FragmentPath'] == '/etc/systemd/system/' + unit, unit + ': unexpected fragment')
    require(values['DropInPaths'] == '', unit + ': effective drop-in present; return to review without reading it')
    print(json.dumps(values))
for path in ('/tmp', '/var/tmp'):
    mount = subprocess.check_output(['findmnt', '--noheadings', '--output', 'TARGET', '--target', path], text=True, timeout=5).strip()
    require(mount == '/', 'PrivateTmp mount topology changed; return to review')
expected_binds = {socket: {namespace, guard, device}, proxy: {socket, guard}, guard: {namespace, device}}
expected_start = {proxy: ('/usr/lib/systemd/systemd-socket-proxyd', '/usr/lib/systemd/systemd-socket-proxyd 127.0.0.1:18080'), guard: ('/usr/sbin/nft', '/usr/sbin/nft --file /etc/adaptive-trust-ci-webhook-bridge.nft')}
expected_stop = {proxy: None, guard: ('/usr/sbin/nft', '/usr/sbin/nft delete table inet adaptive_trust_ci_webhook_bridge')}
dependency_fields = ('Requires', 'Wants', 'Upholds', 'BindsTo', 'After', 'DefaultDependencies')
for unit in units:
    specific = ('Listen', 'BindToDevice', 'Accept', 'ExecStartPre', 'ExecStartPost', 'ExecStopPre', 'ExecStopPost') if unit == socket else ('ExecStart', 'ExecStop', 'ExecCondition', 'ExecStartPre', 'ExecStartPost', 'ExecStopPost')
    values = show(unit, dependency_fields + specific)
    require(all(field in values for field in dependency_fields + specific), unit + ': missing effective property')
    require(values['Wants'] == '' and values['Upholds'] == '', unit + ': unexpected Wants/Upholds activation dependency')
    binds = set(values['BindsTo'].split())
    required = set(values['Requires'].split())
    after = set(values['After'].split())
    require(binds == expected_binds[unit], unit + ': BindsTo differs')
    required_minimum = {'sysinit.target'}
    after_minimum = binds | {'sysinit.target'}
    allowed_requirements = required_minimum | binds | {'system.slice'}
    allowed_after = after_minimum | {'system.slice', 'systemd-journald.socket'}
    if unit != socket:
        after_minimum.add('basic.target')
        allowed_requirements.add('-.mount')
        allowed_after |= {'basic.target', '-.mount', 'systemd-tmpfiles-setup.service'}
    require(required_minimum <= required <= allowed_requirements, unit + ': Requires differs')
    require(after_minimum <= after <= allowed_after, unit + ': After differs')
    require(values['DefaultDependencies'] == ('no' if unit == socket else 'yes'), unit + ': default dependencies differ')
    for field in ('ExecCondition', 'ExecStartPre', 'ExecStartPost', 'ExecStopPre', 'ExecStopPost'):
        if field in values:
            require(values[field] == '', unit + ': unexpected ' + field)
    if unit == socket:
        require(values['Listen'] == '10.200.200.1:18080 (Stream)', unit + ': listener differs')
        require(values['BindToDevice'] == 'veth-vpn-h' and values['Accept'] == 'no', unit + ': socket mode/device differs')
    else:
        for field, expected in (('ExecStart', expected_start[unit]), ('ExecStop', expected_stop[unit])):
            raw = values[field]
            if expected is None:
                require(raw == '', unit + ': unexpected ' + field)
            else:
                parsed = re.findall(r'\{ path=([^;]+) ; argv\[\]=([^;]+) ; ignore_errors=([^;]+) ;', raw)
                require(parsed == [(expected[0], expected[1], 'no')] and raw.count('{') == 1, unit + ': ' + field + ' differs')
    print(json.dumps({'Id': unit, **values}))
print('effective_unit_gate=pass')
PY
```

The comparison treats dependency values as unordered sets. Required explicit edges are preserved, including socket/guard/device stop ordering. Its only additional allowed edges follow the installed systemd 255 manuals: `BindToDevice` adds the device `BindsTo`/`After`; ordinary services add sysinit/basic ordering; `Slice=system.slice` adds slice requirements/ordering; journal output adds journald ordering; and `PrivateTmp=yes` adds tmpfiles ordering plus mount requirements for `/tmp` and `/var/tmp`. Both temporary paths were measured on `/`, so only `-.mount` is admitted for that mount dependency. A `BindsTo` requirement reported in the requirement set is the same reviewed edge, not a new dependency. There is no allowance for `Wants` or `Upholds`; an unexpected implicit activation edge also refuses and returns to review. The socket has no `basic.target`/`sockets.target` ordering allowance. Unit-specific `ExecStart`/`ExecStop` must be exactly the proxyd and nft commands above; socket units have no such main command properties, so all supported socket pre/post command hooks must instead be empty. No extra command, address, namespace service, mount, or dependency is accepted by inference.

Only after this gate passes, the initial start commands are:

```bash
sudo -n systemctl start adaptive-trust-ci-webhook-bridge-guard.service
sudo -n nft list table inet adaptive_trust_ci_webhook_bridge
sudo -n systemctl start adaptive-trust-ci-webhook-bridge.socket
```

Inspect guard `active/exited`, socket `active/listening`, exact table rules and exact socket address/device. Stop on a failed command; do not enable persistence until the initial acceptance passes. A failed nft create cannot open the dependent socket. The proxy becomes active on the first valid client request.

## 3. Bounded HTTP and enforcement checks

The first block is status-only; no response body, headers, credentials, POST, synthetic event, or payload is stored. Expect peer ready 200, peer/public webhook 405, and every listed private public path 404. Public transport timeout/000 is inconclusive and cannot count as 405/404.

```bash
sudo -n ip netns exec vpn curl --noproxy '*' --interface 10.200.200.2 --silent --show-error --connect-timeout 2 --max-time 5 --output /dev/null --write-out 'peer_ready=%{http_code}\n' http://10.200.200.1:18080/health/ready
sudo -n ip netns exec vpn curl --noproxy '*' --interface 10.200.200.2 --silent --show-error --connect-timeout 2 --max-time 5 --output /dev/null --write-out 'peer_webhook=%{http_code}\n' http://10.200.200.1:18080/webhooks/github
curl --noproxy '*' --silent --show-error --connect-timeout 3 --max-time 8 --output /dev/null --write-out 'public_webhook=%{http_code}\n' https://claw.taild9f611.ts.net/webhooks/github
for ci_ingress_path in /health/ready /approvals /jobs/nonexistent /attestations/nonexistent /metrics /v1/jobs; do
    curl --noproxy '*' --silent --show-error --connect-timeout 3 --max-time 8 --output /dev/null --write-out "$ci_ingress_path=%{http_code}\n" "https://claw.taild9f611.ts.net$ci_ingress_path"
done
```

Measure each filter rule, not merely a connection failure. The next block reuses the current namespace source `100.119.249.65`; it creates no address, route, namespace, or raw socket. It sends at most three GET attempts to the exact bridge address, each bounded to two seconds. The allowed source must get 200 and increment its counter. The host `lo` route and correct-veth/wrong-source route must each time out with 000 and increment their respective drop counter. A timeout with no matching counter increment leaves that enforcement unproven.

```bash
python3 -B - <<'PY'
import json, subprocess
def counts():
    body = json.loads(subprocess.check_output(['sudo', '-n', 'nft', '-json', 'list', 'table', 'inet', 'adaptive_trust_ci_webhook_bridge'], text=True))['nftables']
    return {item['rule']['comment']: expr['counter']['packets'] for item in body if 'rule' in item for expr in item['rule']['expr'] if 'counter' in expr}
addresses = json.loads(subprocess.check_output(['sudo', '-n', 'ip', '-n', 'vpn', '-json', 'address', 'show'], text=True))
assert any(a.get('local') == '100.119.249.65' for interface in addresses for a in interface['addr_info'])
route = json.loads(subprocess.check_output(['sudo', '-n', 'ip', '-n', 'vpn', '-json', 'route', 'get', '10.200.200.1', 'from', '100.119.249.65'], text=True))
assert len(route) == 1 and route[0]['dev'] == 'veth-vpn-n'
curl = ['curl', '--noproxy', '*', '--silent', '--show-error', '--connect-timeout', '2', '--max-time', '2', '--output', '/dev/null', '--write-out', '%{http_code}']
peer = ['sudo', '-n', 'ip', 'netns', 'exec', 'vpn']
cases = [('bridge_allowed_peer', peer, ['--interface', '10.200.200.2'], 0, '200'), ('bridge_wrong_interface', [], [], 28, '000'), ('bridge_wrong_source', peer, ['--interface', '100.119.249.65'], 28, '000')]
for label, prefix, source, exit_code, status in cases:
    before = counts()
    result = subprocess.run(prefix + curl + source + ['http://10.200.200.1:18080/health/ready'], capture_output=True, text=True, timeout=5)
    after = counts()
    delta = after[label] - before[label]
    print(json.dumps({'control': label, 'exit_code': result.returncode, 'http_status': result.stdout, 'counter_before': before[label], 'counter_after': after[label], 'delta': delta}))
    assert result.returncode == exit_code and result.stdout == status and delta > 0, label
PY
```

Then record `ss -H -lnt sport = :18080`, the three units' status, the socket `Listen`/`BindToDevice` properties, the narrow nft table, and loopback readiness 200. Only loopback `127.0.0.1:18080` and the device-bound `10.200.200.1:18080` may listen on that port. Any private-path exposure or unexpected listener requires immediate bridge rollback. Do not use a host-local request to the veth as the allowed-source oracle: its route is `lo`.

## 4. Stop/disable and same-byte reactivation

After initial acceptance, enable only the socket, then exercise a **guard stop** to prove dependency propagation. This is the meaningful stop-order check; it must remove both listening owners before removing the filter. Disable the now-inactive socket, and record disabled/inactive state, absent table, loopback-only port 18080, loopback readiness 200, VPN connection refusal, and public webhook 502. A public timeout proves no HTTP status and is recorded as inconclusive.

```bash
sudo -n systemctl enable adaptive-trust-ci-webhook-bridge.socket
sudo -n systemctl stop adaptive-trust-ci-webhook-bridge-guard.service
sudo -n systemctl disable adaptive-trust-ci-webhook-bridge.socket
systemctl show adaptive-trust-ci-webhook-bridge.socket adaptive-trust-ci-webhook-bridge.service adaptive-trust-ci-webhook-bridge-guard.service --property=Id,ActiveState,SubState,UnitFileState
sudo -n nft -json list tables
ss -H -lnt sport = :18080
```

If any socket/proxy remains active, stop both explicitly before any guard/table removal and report failed recovery; do not call the candidate accepted. Do not stop the API to simulate failure. Once the namespace is healthy, the installed four hashes are unchanged, and the mandatory effective-unit gate above passes again for all three inactive units, the exact reactivation is:

```bash
sudo -n systemctl enable --now adaptive-trust-ci-webhook-bridge.socket
systemctl is-enabled adaptive-trust-ci-webhook-bridge.socket
```

Repeat the bounded acceptance block and record actual outcomes. The socket's dependency starts the guard first. A guard whose owned table was lost outside systemd must be stopped together with its dependent listener before recovery; never remove a filter under a live socket. No device recreation or reboot is authorized by this exercise.

## 5. Full rollback, if selected

Stop/disable the added socket and explicitly stop its proxy before stopping the guard. Stop ordering closes the listener before the table disappears; any stop failure prevents subsequent removal.

```bash
sudo -n systemctl disable --now adaptive-trust-ci-webhook-bridge.socket
sudo -n systemctl stop adaptive-trust-ci-webhook-bridge.service
sudo -n systemctl stop adaptive-trust-ci-webhook-bridge-guard.service
```

First establish all three inactive, only loopback port 18080 listening, and no dedicated table. Compare all four installed files with the recorded hashes; refuse deleting a changed/foreign file. If these exact newly installed artifacts are still owned by this operation, remove only the four named files, then reload unit definitions:

```bash
sudo -n rm -- /etc/systemd/system/adaptive-trust-ci-webhook-bridge.socket /etc/systemd/system/adaptive-trust-ci-webhook-bridge.service /etc/systemd/system/adaptive-trust-ci-webhook-bridge-guard.service /etc/adaptive-trust-ci-webhook-bridge.nft
sudo -n systemctl daemon-reload
```

Recheck original loopback readiness and failed bridge/public ingress. Preserve host-local staged bytes and evidence. Do not remove another nft table, edit the global firewall, disable the namespace/Tailscale/API, or roll back deployed trust material. A guard-stop failure that leaves its table is fail-closed; preserve it until the coordinator confirms both listener owners are stopped and decides the exact owned-table recovery.

## Separate real GitHub intake

Connectivity acceptance permits the parent to consider a separately granted PR #170 `ready_for_review` action after the full verifier/installer CPU slot has finished. Refresh the PR head first; the previously observed head is `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`, not a permission to operate on a changed head. Observe a real delivery's ID/time/status, correlate actual API POST intake and job/check identifiers using authorized operator-safe readbacks, and inspect the exact-head `adaptive-trust-ci/verified@06ecf1c875bc` Check Run from App ID `4694114`. Record an unavailable delivery/job readback as unobserved, never inferred from a 405 or unrelated check. This plan neither replays a webhook nor accesses credentials, a queue database, or human approval material. Merge eligibility and issue closure remain with their exact external check and approval requirements.
