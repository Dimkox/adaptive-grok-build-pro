# Final verification — v2.0.19 release sync

The frozen release-sync tree is verified with:

```text
python3 scripts/grok_verify.py --mode pr
```

The machine-bound result is the route receipt at
`.grok-stack/runtime/receipts/0ea34220576f/verification.json`; it binds the
exact final HEAD, tree fingerprint, route base `5d93fc3d68869ab26799935adab5fa62be5e2a80`,
change specification, and required verification profiles (`base`, `contracts`).
No merge, tag, artifact publication, GitHub Release, or deployment is authorized
by this local record; each remains downstream of the exact external Trust CI
check and named action grant.
