# Architecture — M1 typed spec

See `evidence/analysis-architect.md` for the binding ruling.

Intent plane only. `spec.py` loads a restricted YAML subset, validates a local JSON Schema subset, computes a canonical digest, and applies completeness rules. CLI is `scripts/grok_spec.py`. Markdown is explanation, not authority.

M0 live Trust Authority is not met on this host (8080 is SearXNG, no TLS Trust CI, no cosign, main unprotected). User unattended auto-approve is the named bootstrap exception to start M1; it is not merge authority.
