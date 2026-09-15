# Delivery

No product tag or GitHub Release is part of this fix. Delivery uses fix/grok-reasoning-usage -> pull request -> external policy-epoch check for exact SHA -> required approvals -> merge -> install that merged source for the Grok executor only. Local receipts do not authorize merge or replace the external gate.

## Concrete runtime activation

The prepared service is adaptive-l5-grok.service, currently stopped and disabled. Its private provider environment and host configuration are /etc/adaptive-l5/grok-provider.conf and /etc/adaptive-l5/grok-host.json. Its independent state roots are /var/lib/adaptive-l5-grok and its socket is /run/adaptive-l5-grok/control.sock. Configuration selects grok-vision, pinned to grok-4.6. Do not copy credentials into the repository or reports.

After merge authorization and exact-SHA external success, obtain an independent clean clone at the merged commit and use factory/runtime/install-claw.sh with that exact commit and the existing landing source fde60e040167c10975b00d11f578c4da6763069a. Prepare a new immutable release under /opt/adaptive-l5/releases/<merged-sha>. Update only the Grok config control-repository path and Grok unit release paths, validate both, start Grok, check readiness, and submit one new synthetic job through its authenticated socket. Require artifact_ready and an artifact digest before enabling the unit at boot. Do not publish the synthetic page or retry the original failed job.

Preserve adaptive-l5.service, its installed release 5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a, PID 698333, existing Qwen config and state. Verify Qwen health and configuration hash before and after activation. Failed Grok validation stops/disables only the new unit and preserves its records.

Current live diagnostics made four bounded provider attempts: original installed service rejection, installed transport diagnosis, invalid candidate timeout, and source-verified candidate executor acceptance. The last accepted arithmetic but its diagnostic harness failed the subsequent draft-decoder call; full artifact acceptance is still pending. Local evidence cannot substitute for the merged runtime check.
