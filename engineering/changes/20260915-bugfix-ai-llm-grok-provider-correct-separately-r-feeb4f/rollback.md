# Recovery

The new Grok unit is stopped/disabled; Qwen remains active. After exact-SHA Trust CI and merge, install a new immutable release for Grok only. On failed validation stop/disable adaptive-l5-grok.service and preserve its failed row/config/artifacts; do not replay the original task or restore/remove locks. No schema migration is needed.
