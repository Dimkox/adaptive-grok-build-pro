# Implementation evidence — issue #73

## Scope

The bounded change updates the current delegated-grant producer and its two repository-owned
consumers. Immutable historical probe artifacts were not edited.

## Changes

- `.grok-stack/adaptive_grok/state.py` emits `grant_binding_digest`; the reader accepts either
  the current key or legacy `tree_fingerprint` and rejects both together.
- `scripts/grok_landing_publish.py` applies the same compatibility and ambiguity rules to the
  exact external-write authority check.
- Policy, landing-publication, and history tests cover new writes, legacy reads, dual-field
  rejection, malformed current values, and historical byte identity.
- `AGENTS.md`, `decisions.md`, and the package documents describe the neutral current field and
  the external GitGuardian boundary.

## Focused verification

Command:

`python3 -m unittest factory.tests.test_landing_publication_cli tests.test_policy tests.test_history`

Observed result: `Ran 76 tests ... OK`.

The route-wide PR verification is intentionally still pending; an earlier attempt was interrupted
by the harness and did not produce a receipt.
