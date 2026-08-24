# repo_explorer: host identity (route c8e5e567a15d)

This machine is **not a laptop**. It is a **desktop** host named **claw**.

| Fact | Value |
| --- | --- |
| `hostname` | `claw` |
| `hostnamectl` chassis | `desktop` (icon `computer-desktop`; vendor INTEL, model X99 W-D4H) |
| CPU model | `Intel(R) Xeon(R) CPU E5-2680 v4 @ 2.40GHz` |
| MemTotal | `16268340 kB` (~16 GiB) |
| Git branch | `milestone/m0-live-trust-authority` |
| Git HEAD (short/full) | `9f84dfd` / `9f84dfd7b5458e5394314c5f6913aa5c6631c058` |

`http://127.0.0.1:8080/` returns HTTP 200 and HTML containing **SearXNG**. Docker maps `searxng-instance` (`searxng/searxng:2026.6.11-4dd0bf486`) `127.0.0.1:8080->8080/tcp`.

Other containers on the same Docker engine (names only): `n8n-core`, `n8n-proxy`, `backup-postgres`, `drive-sync`, `ruflo-mcp`, `backup-mongo`, `ruflo-mongo`, `postgres-db`, `proxy-gateway`, `pulsengineering-dev-gateway-1`, `pulsengineering-dev-web-1`, `pulsengineering-dev-db-1`, `proxy-gateway-a2`, `domestos-pg`, `obsidian-couch`.

No secrets, PEM, or `.env` files were read. No push.
