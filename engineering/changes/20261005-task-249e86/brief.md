# Narrow local Trust CI verifier compatibility

Typed authority: change-spec.yaml. Owner explicitly approved this separate narrow PR. Agreed comparison base refreshed only to actual merged main326908bf6367b05b65b83818ee84a093c1e45872 after PR245; old initial checkpoint remains historical. No Trust CI implementation belongs in this candidate.

Outcome: local checker accepts only independently reviewed exact004_public_admission and forward005_public_pending_bootstrap bytes and four explicitly named bound public contract registrations. The bounded forward ruling adds only the exact reviewed005 identity alongside004; fixed primary/mirror path membership is separate from digest keys. Preserve separation, historical migration integrity, mirrors, version sequence and deployed trust boundaries. Fix architecture_fitness.py and focused regressions, not rule data, scope selector, loader, factory runtime or deployed authority.
