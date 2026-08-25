# Rollback

- Unpushed commit: `git reset` on this branch only. No force-push.
- After push: leave the extra commit on the draft PR. Do not PATCH Check Runs. Do not `compose down -v`.
- HMAC cannot unpublish a Check Run. Old `97390635614` on `1fc9420` stays.
