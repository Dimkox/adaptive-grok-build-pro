# Rollback

```bash
sudo tailscale funnel --https=443 --set-path=/webhooks/github off
```

Never `sudo tailscale funnel reset`. Never `sudo tailscale funnel --https=443 off`. Revert docs/test commit. No compose rollback (env unchanged).
