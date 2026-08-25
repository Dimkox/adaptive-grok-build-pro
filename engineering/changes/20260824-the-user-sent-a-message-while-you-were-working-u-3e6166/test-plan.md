# Test plan

Tracked compose stays DinD. **No product test updates this slice.** Do not weaken `assertNotIn('/var/run/docker.sock', compose)`.

Live proof (not a unit test):

1. `curl -fsS http://127.0.0.1:18080/health/ready`
2. `docker compose --project-name adaptive-trust-ci ps` — worker running
3. HMAC POST returns 200 + `job_id`
4. `gh api repos/Dimkox/adaptive-grok-build-pro/commits/<exact-sha>/check-runs` filtered for name + `app.id=4694114`

If only overlay + gitignored env + `/tmp` scripts: skip `grok_verify` (no-op product tree). If activation report / plan / `decisions.md` change, run `python3 scripts/grok_verify.py --mode pr` and route reviews.
