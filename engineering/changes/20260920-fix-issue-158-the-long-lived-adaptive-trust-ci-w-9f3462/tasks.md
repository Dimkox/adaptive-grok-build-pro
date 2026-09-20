# Tasks — Fix issue #158: the long-lived adaptive-trust-ci worker accumulates unreaped [git] defunct children (measured 4 over ~24h, NRestarts=0), so every subprocess path must reap on all outcomes including the accepted 'zombie_only' classification; locate the real leak empirically rather than assuming a missing wait, add a test whose control fails on current code, and keep exit-status classification and all attestation/policy semantics untouched.

- [ ] Freeze contracts and expected behavior.
- [ ] Add failing test or characterization test.
- [ ] Implement the smallest vertical change.
- [ ] Run selected quality profile.
- [ ] Complete independent reviews.
- [ ] Bind evidence to the final tree fingerprint.
