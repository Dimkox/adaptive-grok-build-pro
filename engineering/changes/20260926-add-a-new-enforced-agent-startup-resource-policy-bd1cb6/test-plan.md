# Verification boundary

The initial diff-only instruction is superseded by the September 26 selector-driven follow-up. Run `git diff --check` and `taskset -c 0-27 env GROK_TEST_WORKERS=8 PYTHONDONTWRITEBYTECODE=1 python3 scripts/grok_verify.py --mode pr`; use the actual refreshed base 33a4d3ecb73d81dbdd48195c2681813105159b5a and retain the selector's reported inventory, profile and skips. The closed docs/state lane is expected for these prose/package edits; any refusal is investigated, not overridden by a manual factory exemption.

No new runtime behavior or test is introduced. Existing focused structure/state/manifest/workflow/router modules and remaining selected checks supply local evidence; independent route code review and external exact-head Trust CI remain subsequent gates. No full-suite pass or historical component reuse is claimed for a focused run.
