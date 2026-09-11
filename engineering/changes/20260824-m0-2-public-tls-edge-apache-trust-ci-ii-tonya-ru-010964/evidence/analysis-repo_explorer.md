# repo_explorer live probe — M0.2 TLS edge (claw)

Route: `01096425a38d`. Change: `20260824-m0-2-public-tls-edge-apache-trust-ci-ii-tonya-ru-010964`. Host: claw (this machine). Probe time: 2026-08-24. No `.env`/PEM/webhook secret/privkey read. No apt-install or writes except this evidence file.

## 1. Public IPv4 of this host

| Method | Result |
|---|---|
| `hostname -I` | RFC1918 only: `192.168.0.229` (LAN `enp6s0`) plus docker/vpn bridges (`10.200.200.1`, `172.17–27.x`) |
| `ip -4 route get 1.1.1.1` | `via 192.168.0.1 dev enp6s0 src 192.168.0.229` |
| `curl -4 -s ifconfig.me` | **`91.197.106.11`** (egress/public IPv4) |

Public iface `enp6s0` has **no global IPv6** (`ip -6 addr show scope global` empty; `ip -6 route get 2001:4860:4860::8888` produced no route line). **Do not create AAAA** until IPv6 is configured on the public path.

Note: host is NAT behind `192.168.0.1`; FirstVDS public mapping for claw is the ifconfig.me address **91.197.106.11**, not the LAN address.

## 2. DNS `trust-ci.ii-tonya.ru`

`dnsutils`/`dig` present.

| Query | Result |
|---|---|
| `dig +short A trust-ci.ii-tonya.ru` | **`157.22.187.237`** |
| `dig +short AAAA trust-ci.ii-tonya.ru` | **empty** (exit 0, no records) |
| `getent ahostsv4` | `157.22.187.237` |
| `python3 getaddrinfo AF_INET` | `['157.22.187.237']` |
| `python3 getaddrinfo AF_INET6` | no native AAAA (`Errno -5`) |

**A record does not match this host’s public IPv4.** DNS `157.22.187.237` ≠ claw `91.197.106.11`. AAAA correctly absent.

## 3. Listeners `:80` `:443` `:18080` `:8080`

`ss -ltn` (and `-ltnp` where permitted):

| Port | Bind | Owner |
|---|---|---|
| **80** | **not listening** | nobody |
| **443** | **not listening** | nobody |
| **18080** | `127.0.0.1:18080` | Trust CI API publish |
| **8080** | `127.0.0.1:8080` | `searxng-instance` (unrelated) |

- `systemctl is-active apache2` → **inactive**; `is-enabled` → **not-found**.
- Host `apache2ctl` / `/usr/sbin/apache2` / `/etc/apache2` **absent**.
- Apache PIDs (`2735` root, children as `pall`) are **inside a Docker cgroup** (`docker-fa6528557cf9…`), image `pulsengineering-dev-php:8.3.25-apache` container `pulsengineering-dev-web-1`, published only as **container-internal 80/tcp**, not host 80/443.
- Unrelated edge: Caddy `n8n-proxy` publishes `0.0.0.0:3001` and `0.0.0.0:5678`, not 80/443.

**Host Apache does not hold 80/443. Nothing currently holds 80/443 on claw.** Installing/enabling host Apache for this change would not fight an existing host bind (still must not overlay Caddy onto 80/443).

## 4. Loopback API + compose + overlay

`GET http://127.0.0.1:18080/health/ready` → **HTTP 200**, body `{"status":"ready",...}` (`policy_digest` present; status_publisher `worker-github-app`).

Compose project **`adaptive-trust-ci`**: `running(3)` files:

- `/home/pall/grok-projects/adaptive-grok-build-pro/trust-ci/compose.yaml`
- `/home/pall/adaptive-trust-ci-host/compose.host-socket.yaml`

Containers:

| Name | Status | Ports |
|---|---|---|
| `adaptive-trust-ci-api-1` | Up ~4h (healthy) | **`127.0.0.1:18080->8080/tcp`** (loopback only) |
| `adaptive-trust-ci-postgres-1` | Up ~49m (healthy) | 5432 (internal) |
| `adaptive-trust-ci-worker-1` | Up ~3h | no host ports |

**Overlay path exists:** `/home/pall/adaptive-trust-ci-host/compose.host-socket.yaml` mode **`0600`** (`-rw-------`, owner `pall`). File contents not dumped.

## 5. Apache vhosts

- `/etc/apache2/sites-available/trust-ci.conf` → **does not exist** (no `/etc/apache2` tree).
- Other vhost **names**: none on the host Apache (package/config not installed). Docker PHP-Apache is a different stack (`pulsengineering-dev-web-1`), not a host vhost list.

## 6. ufw / public URL key

- `ufw status` without root: “need to be root”.
- `sudo -n ufw status` → **`Status: inactive`**.
- INPUT iptables (sudo -n, no dump of secrets): **policy ACCEPT**, empty chain.
- Local firewall is not filtering 80/443; FirstVDS external firewall was **not** probed from here.
- `grep '^TRUST_CI_PUBLIC_BASE_URL=' trust-ci/env/common.env` (single key only):  
  **`TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`**  
  (still loopback HTTP; not `https://trust-ci.ii-tonya.ru`).

---

DNS match? **No** (A=`157.22.187.237` vs claw public `91.197.106.11`; AAAA empty). Apache holds 80/443? **No** (ports free; host apache2 not installed; only docker PHP-Apache off-host-ports). API still loopback 18080? **Yes** (`127.0.0.1:18080->8080/tcp`, `/health/ready` ready). Overlay path: **`/home/pall/adaptive-trust-ci-host/compose.host-socket.yaml` exists, mode 0600.**
