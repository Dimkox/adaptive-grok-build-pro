# Rollback and recovery

1. Disable the pilot live profile/CLI; factory execution/delivery defaults are unaffected.
2. Preserve private immutable evidence and observe any prepared/in-flight external operation. Never delete or overwrite a possibly created remote ref/PR automatically.
3. Forward-fix the pilot source through a new reviewed PR. If a published landing branch/PR is wrong, a human decides whether to close it; the pilot cannot mutate that decision.

After rollback, verify no pilot process remains, no new write was retried, the control and landing base refs are unchanged, and every retained record still validates its predecessor digest. Release artifact rollback means using the prior immutable `v2.0.14`; never retag or overwrite published assets.
