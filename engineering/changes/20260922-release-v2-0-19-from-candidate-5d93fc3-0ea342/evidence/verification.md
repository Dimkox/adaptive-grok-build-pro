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

## Rebind note

The preceding verification description is historical and names the superseded input candidate. The current final run must bind to route base `7650a5e12aad55bdcf730cd37e2faf162bec0486`, the frozen release-sync HEAD after the current evidence reports are committed, and its resulting tree fingerprint. No prior receipt is reused after the restack.
