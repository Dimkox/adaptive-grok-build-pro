# Rollback

```bash
docker compose --project-name adaptive-trust-ci stop worker runner-loader
# leave postgres + api running
# delete the overlay file; do not compose down -v
```

Do not PATCH a published Check Run to success. Optional closed HMAC POST cancels PR #5 jobs. Verify: `/health/ready` 200; no Trust CI container mounts `/var/run/docker.sock`; hooks empty; `main` unprotected.
