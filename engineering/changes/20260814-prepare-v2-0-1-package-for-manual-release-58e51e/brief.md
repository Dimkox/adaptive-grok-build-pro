# Prepare v2.0.1 package for manual release

Change ID: `20260814-prepare-v2-0-1-package-for-manual-release-58e51e`
Route: `58e51ee88411`
Risk: high (release) | write_agent: none

## Outcome

Version continues after `2.0.0` as **2.0.1**. Local commit + zip + notes are ready. Human owner publishes the tag and GitHub Release.

## Scope

- Bump `VERSION` and user-facing version strings
- Default packager output follows `VERSION`
- Rebuild `dist/` artifacts
- Do not push, tag, or create a GitHub Release
