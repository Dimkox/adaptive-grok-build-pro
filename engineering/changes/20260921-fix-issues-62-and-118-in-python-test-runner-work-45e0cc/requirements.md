# Acceptance requirements

1. Auto worker counts respect visible process cgroup quotas and affinity under deterministic fixture hierarchies, including tighter parents and fractional quotas.
2. Relevant malformed/unavailable/ambiguous/bounded-out capacity evidence uses the explicit conservative fallback; known unlimited and expected absent controls remain distinct.
3. Explicit workers, environment precedence, default-off, child suppression, other POSIX and non-POSIX behavior remain compatible without unnecessary Linux reads.
4. Retained PR135 platform fallback selects actual serial execution before launch and preserves coverage-only measured pins, actual backend reporting and supported xdist pins.
5. Exact test collection, no rerun-on-failure, cleanup and fresh coverage remain meaningful. Retain non-vacuous zero-test serial rejection regressions on the measured runtime without changing already-correct accounting or claiming untested interpreter behavior.
6. Current complete verification and all selected independent code/test/security reviews qualify only the actual source tree; PR135 closes as superseded only after successor delivery.
