# Rollback

- `sudo a2dissite trust-ci.conf && sudo systemctl reload apache2`
- Revert gitignored `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`
- `docker compose -f compose.yaml -f /home/pall/adaptive-trust-ci-host/compose.host-socket.yaml up -d --force-recreate api worker`
- Never `compose down -v`. Never delete LE certs unless abandoning the hostname.
