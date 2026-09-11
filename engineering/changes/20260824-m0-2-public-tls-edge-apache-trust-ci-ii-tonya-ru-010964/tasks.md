# Tasks

- [ ] Re-measure public IPv4. If DNS A ≠ that IP, set A `trust-ci` → claw IPv4 TTL 300 if a non-secret DNS tool exists; else document and continue HTTP vhost, stop before certbot if ACME cannot see this host.
- [ ] Install apache2 + certbot + modules. ufw allow 80/443 if ufw becomes active. Do not fight n8n Caddy 3001/5678.
- [ ] HTTP vhost for ACME as specified. configtest + reload. curl -I http://trust-ci.ii-tonya.ru/ must not timeout **once DNS points here**.
- [ ] certbot certonly webroot -d trust-ci.ii-tonya.ru -m bpall@mail.ru --agree-tos --non-interactive.
- [ ] Final HTTPS vhost exactly as user specified. configtest + reload.
- [ ] Patch gitignored env/common.env public URL only (sed/helper, print that one key). Recreate api worker with overlay. Health loopback + public.
- [ ] Unsigned POST 401 proof. certbot renew --dry-run.
- [ ] Docs: activation report URL; plan webhook stays not done; invariants green. Do not commit env or LE keys. Do not register GitHub hook.
- [ ] grok_verify --mode pr. implementation.md. No push unless later ordered.
