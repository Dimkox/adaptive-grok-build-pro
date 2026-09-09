# Deferred issue: discover OpenClaw workspace paths before reading

Status: reported by user, deferred; not reproduced in the target repository.
Target: `/home/pall/grok-projects/google-ads-automation`.

## Observed evidence

While preparing to inspect Dima's SOUL/ADS/TOOLS files and mounts, the downstream agent attempted to read `deploy/openclaw/workspace/SOUL.md` and `deploy/openclaw/workspace/ADS.md`. Both reads reported that the files did not exist. The `project/adaptive:pre_tool_use` hook allowed the read invocation; this does not prove path existence or establish an Ads authorization defect.

## Bounded follow-up

1. Inspect that repository's entrypoint and actual tracked paths using `rg --files`; inspect the relevant deployment/mount configuration without reading secrets.
2. Resolve repository source paths versus container runtime mount paths before reading SOUL/ADS/TOOLS. Stop with a precise missing-path result if no source mapping exists; do not invent a layout or create replacement policy files.
3. Determine whether the faulty assumption originates in factory-generated guidance, the downstream agent prompt, or deployment drift. Root cause is currently unconfirmed.
4. Add a regression for a nonstandard/missing OpenClaw workspace layout and repair only the responsible discovery step.

Acceptance: the agent names the actual source/mount mapping or reports the exact missing prerequisite before dependent reads; it never treats a successful permission hook as a filesystem existence check. This issue does not authorize Ads mutations, changes to Dima's permissions, warehouse CLI operations, deployment or external writes.

Handoff: keep separate from the current pilot CSP/sandbox/test-discovery review repairs. No downstream repository was changed while recording this report.
