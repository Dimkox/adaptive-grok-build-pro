# Reviewed operation candidate — not activated

Route `68274cb876e4`. This plan installs four new host files and manages only their three units, one enablement symlink, and the dedicated nft table. The parent coordinator owns exact grants and execution after independent code, test, security, and release review. Preparation executed no installation, daemon reload, enablement, start, stop, GitHub write, or webhook POST.

The reviewed files are in `/home/pall/.cache/agbp-run/issues-wave-20260921/ci-ingress/artifacts/`. [The manifest](evidence/artifact-manifest.json) gives every source, destination, byte count, and SHA-256. The manifest SHA-256 is `b4b45a7c453812942cbc33a2b88239613be7079435a445c9b208ab00f54f714d`. [Static evidence](evidence/preparation-verification.json) records what actually ran.

Coordinator results `operation-result-01.json` and `operation-result-02.json` under that host-local stage record exclusive installation, syntax checks, and `daemon-reload` on September 21 at 08:10 UTC. Result `03` records the previous gate refusing before any start; all three units remain inactive. Resume only at the corrected read-only gate below after all four reviews rebind, the coordinator commits the handoff, and a new exact grant binds that state. Do not rerun the exclusive installation against these existing files or overwrite the original result files. The four resource bytes and original preparation manifest remain unchanged.

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

The following read-only gate first checks identities with narrowly selected `systemctl show` properties. It then uses the installed `busctl` for named, typed property reads: systemctl's human-readable output suppresses empty `Exec*` arrays even with `--all`, and quotes/escapes some dependency names. A typed empty array is accepted only after the D-Bus property read succeeds with its exact expected signature; a missing property or read error is never treated as empty. No whole-interface dump, environment, or credential property is requested.

`Upholds` must remain empty. Socket `Wants` must remain empty; the two `PrivateTmp=yes` services must have exactly their measured implicit `Wants=tmp.mount`. That sole exception is accepted only while `tmp.mount` is still not-found/inactive, with no fragment, drop-ins, activation dependencies, or transient definition. A real mount definition appearing returns to review; this plan never starts or installs it. All `Requires`, `BindsTo`, and `After` sets must equal the measured sets below. Thus outgoing dependency links cannot add unrelated activation edges without refusal. The final `effective_unit_gate=pass` is required; an exception, nonzero exit, missing output, or unrecognized dependency is a refusal. Keep the effective-property output with the operation evidence. Repeat this gate before reactivation and after any later daemon reload while the bridge is stopped; changed definitions need fresh review, not a wider allowlist.

**Exact continuation from the current stopped installation:** run this gate as the next operation, without rerunning installation or the already completed syntax/reload block. It first verifies the pinned manifest, all four installed SHA-256 values, regular files owned `root:root` at mode `0644`, all three inactive identities, no bridge enablement links, and absence of the dedicated nft table. Only a complete pass permits the separately granted start block that follows. The same prerequisite checks apply after stop/disable recovery. Parent retains the CPU-lane restriction: no PR #170 event until the current full verification lane is released, regardless of bridge connectivity.

```bash
python3 -B - <<'PY'
import hashlib, json, os, stat, subprocess
from pathlib import Path
prefix = 'adaptive-trust-ci-webhook-bridge'
socket = prefix + '.socket'
proxy = prefix + '.service'
guard = prefix + '-guard.service'
device = r'sys-subsystem-net-devices-veth\x2dvpn\x2dh.device'
namespace = 'wg-vpn-namespace.service'
units = (socket, proxy, guard)
object_prefix = '/org/freedesktop/systemd1/unit/adaptive_2dtrust_2dci_2dwebhook_2dbridge'
object_paths = {socket: object_prefix + '_2esocket', proxy: object_prefix + '_2eservice', guard: object_prefix + '_2dguard_2eservice', 'tmp.mount': '/org/freedesktop/systemd1/unit/tmp_2emount'}
def require(condition, reason):
    if not condition:
        raise SystemExit('effective_unit_gate=REFUSED: ' + reason)
def show(unit, names):
    result = subprocess.run(['systemctl', 'show', '--all', '--property=' + ','.join(names), unit], capture_output=True, text=True, timeout=10, check=True)
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
def typed(unit, interface, name, signature):
    result = subprocess.run(['busctl', '--system', '--json=short', 'get-property', 'org.freedesktop.systemd1', object_paths[unit], 'org.freedesktop.systemd1.' + interface, name], capture_output=True, text=True, timeout=10, check=True)
    value = json.loads(result.stdout)
    require(value.get('type') == signature and 'data' in value, unit + ': missing/wrong typed ' + name)
    return value['data']
stage = Path('/home/pall/.cache/agbp-run/issues-wave-20260921/ci-ingress')
manifest_bytes = (stage / 'artifact-manifest.json').read_bytes()
require(hashlib.sha256(manifest_bytes).hexdigest() == 'b4b45a7c453812942cbc33a2b88239613be7079435a445c9b208ab00f54f714d', 'artifact manifest changed')
for name, entry in json.loads(manifest_bytes)['installed_files'].items():
    descriptor = os.open(entry['destination'], os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as handle:
        info = os.fstat(handle.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_gid == 0 and stat.S_IMODE(info.st_mode) == 0o644, name + ': installed type/owner/mode differs')
        payload = handle.read()
        require(len(payload) == entry['bytes'] and hashlib.sha256(payload).hexdigest() == entry['sha256'], name + ': installed bytes differ')
    print(json.dumps({'installed_file': entry['destination'], 'sha256': entry['sha256'], 'owner': 'root:root', 'mode': '0644'}))
identity_fields = ('Id', 'LoadState', 'ActiveState', 'FragmentPath', 'DropInPaths', 'UnitFileState')
for unit in units:
    values = show(unit, identity_fields)
    require(all(field in values for field in identity_fields), unit + ': missing identity property')
    require(values['Id'] == unit and values['LoadState'] == 'loaded' and values['ActiveState'] == 'inactive', unit + ': identity/state differs')
    require(values['FragmentPath'] == '/etc/systemd/system/' + unit, unit + ': unexpected fragment')
    require(values['DropInPaths'] == '', unit + ': effective drop-in present; return to review without reading it')
    require(values['UnitFileState'] == ('disabled' if unit == socket else 'static'), unit + ': unexpected enablement state')
    print(json.dumps(values))
unit_paths = subprocess.check_output(['systemd-analyze', 'unit-paths'], text=True, timeout=10).splitlines()
for parent in map(Path, unit_paths):
    for unit in units:
        for pattern in ('*.wants/' + unit, '*.requires/' + unit, '*.upholds/' + unit):
            require(not list(parent.glob(pattern)), unit + ': unexpected enablement/dependency link')
tables = json.loads(subprocess.check_output(['sudo', '-n', 'nft', '-json', 'list', 'tables'], text=True, timeout=10))['nftables']
require(not any(item.get('table', {}).get('family') == 'inet' and item.get('table', {}).get('name') == 'adaptive_trust_ci_webhook_bridge' for item in tables), 'bridge guard table already exists; stop and review')
tmp_identity = {name: typed('tmp.mount', 'Unit', name, signature) for name, signature in (('Id', 's'), ('LoadState', 's'), ('ActiveState', 's'), ('FragmentPath', 's'), ('DropInPaths', 'as'), ('Transient', 'b'), ('Requires', 'as'), ('Wants', 'as'), ('Upholds', 'as'), ('BindsTo', 'as'))}
require(tmp_identity == {'Id': 'tmp.mount', 'LoadState': 'not-found', 'ActiveState': 'inactive', 'FragmentPath': '', 'DropInPaths': [], 'Transient': False, 'Requires': [], 'Wants': [], 'Upholds': [], 'BindsTo': []}, 'tmp.mount is no longer an absent/inactive dependency; return to review')
print(json.dumps(tmp_identity))
for path in ('/tmp', '/var/tmp'):
    mount = subprocess.check_output(['findmnt', '--noheadings', '--output', 'TARGET', '--target', path], text=True, timeout=5).strip()
    require(mount == '/', 'PrivateTmp mount topology changed; return to review')
expected_binds = {socket: {namespace, guard, device}, proxy: {socket, guard}, guard: {namespace, device}}
common_requirements = {'sysinit.target', 'system.slice'}
service_ordering = common_requirements | {'-.mount', 'basic.target', 'systemd-journald.socket', 'systemd-tmpfiles-setup.service', 'tmp.mount'}
expected_start = {proxy: ['/usr/lib/systemd/systemd-socket-proxyd', ['/usr/lib/systemd/systemd-socket-proxyd', '127.0.0.1:18080'], False], guard: ['/usr/sbin/nft', ['/usr/sbin/nft', '--file', '/etc/adaptive-trust-ci-webhook-bridge.nft'], False]}
expected_stop = {proxy: None, guard: ['/usr/sbin/nft', ['/usr/sbin/nft', 'delete', 'table', 'inet', 'adaptive_trust_ci_webhook_bridge'], False]}
command_signature = 'a(sasbttttuii)'
for unit in units:
    values = {name: typed(unit, 'Unit', name, 'as') for name in ('Requires', 'Wants', 'Upholds', 'BindsTo', 'After')}
    values['DefaultDependencies'] = typed(unit, 'Unit', 'DefaultDependencies', 'b')
    require(set(values['BindsTo']) == expected_binds[unit], unit + ': BindsTo differs')
    require(set(values['Requires']) == common_requirements | (set() if unit == socket else {'-.mount'}), unit + ': Requires differs')
    require(set(values['After']) == expected_binds[unit] | (common_requirements if unit == socket else service_ordering), unit + ': After differs')
    require(set(values['Wants']) == (set() if unit == socket else {'tmp.mount'}), unit + ': Wants differs')
    require(values['Upholds'] == [], unit + ': unexpected Upholds dependency')
    require(values['DefaultDependencies'] is (unit != socket), unit + ': default dependencies differ')
    interface = 'Socket' if unit == socket else 'Service'
    hooks = ('ExecStartPre', 'ExecStartPost', 'ExecStopPre', 'ExecStopPost') if unit == socket else ('ExecCondition', 'ExecStartPre', 'ExecStartPost', 'ExecStopPost')
    for name in hooks:
        values[name] = typed(unit, interface, name, command_signature)
        require(values[name] == [], unit + ': unexpected ' + name)
    if unit == socket:
        values['Listen'] = typed(unit, interface, 'Listen', 'a(ss)')
        values['BindToDevice'] = typed(unit, interface, 'BindToDevice', 's')
        values['Accept'] = typed(unit, interface, 'Accept', 'b')
        require(values['Listen'] == [['Stream', '10.200.200.1:18080']], unit + ': listener differs')
        require(values['BindToDevice'] == 'veth-vpn-h' and values['Accept'] is False, unit + ': socket mode/device differs')
    else:
        values['PrivateTmp'] = typed(unit, interface, 'PrivateTmp', 'b')
        require(values['PrivateTmp'] is True, unit + ': expected PrivateTmp boundary differs')
        for name, expected in (('ExecStart', expected_start[unit]), ('ExecStop', expected_stop[unit])):
            rows = typed(unit, interface, name, command_signature)
            values[name] = [row[:3] for row in rows]
            if expected is None:
                require(rows == [], unit + ': unexpected ' + name)
            else:
                require(len(rows) == 1 and len(rows[0]) == 10 and rows[0][:3] == expected, unit + ': ' + name + ' differs')
    print(json.dumps({'Id': unit, **values}))
print('effective_unit_gate=pass')
PY
```

The comparison uses typed dependency arrays as unordered sets, preserving literal systemd unit-name escapes. Required explicit edges remain, including socket/guard/device stop ordering. The exact measured sets also contain documented sysinit/basic, system slice, journald, tmpfiles, and root-mount edges. The installed `PrivateTmp` readback adds `Wants=tmp.mount` and `After=tmp.mount` even though both temporary paths currently reside on `/`; [systemd v255's implementation](https://github.com/systemd/systemd/blob/v255/src/core/unit.c#L1227-L1241) explicitly adds that weak `/tmp` edge and requires the mounts for `/var/tmp`. This corrects the earlier assumption that current mount topology implied an empty `Wants` set. Its target must remain absent/inactive; no other Wants or any Upholds is accepted. The socket has no basic/sockets-target ordering allowance. Unit-specific `ExecStart`/`ExecStop` must contain exactly one reviewed executable/argument vector with error ignoring disabled, or an actual typed empty array where no command is configured. All socket pre/post and service condition/pre/post hooks must likewise be typed empty arrays. No extra command, address, namespace service, mount, or dependency is accepted by inference.

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
