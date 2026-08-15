# Fail-open hooks after git pull on any project

Change ID: `20260815-fail-open-hooks-after-git-pull-on-any-project-8abd64`

## Problem

`err.log` from `google-ads-automation`: Grok runs `project/adaptive` hooks as `python3 pre_tool_use.py` in the **project root**. Scripts live in `.grok/hooks/`. Python exits 2 → PreToolUse **denies every tool**, Stop loops 8 times. `git pull` cannot run from the agent.

## Outcome

Old `adaptive.json` (`python3 pre_tool_use.py`) and missing scripts no longer lock a project after pull/install.

## Scope

Root dispatch shims, fail-open hook commands, installer copies shims, tests, repair the live Ads project config.
