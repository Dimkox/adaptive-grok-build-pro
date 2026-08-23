# Protected control-plane writes

Opaque shell rewrites of `.grok/**`, `.grok-stack/**`, `AGENTS.md`, Trust CI, governance files, and repository policy remain blocked even when a local path grant exists. Commands such as `sed -i`, redirection, heredoc-to-target, `python -c`, formatter `--fix`, and arbitrary copy/move operations are too broad to audit safely.

Use a normal structured `Edit`, `Write`, or `apply_patch` call for a single coherent edit. For a multi-file batch, use the validated writer below.

## 1. Create one exact grant covering every target

```bash
python3 scripts/grok_approve.py protected-path \
  --action protected-path-write \
  --resource '.grok/agents/*.md' \
  --resource '.grok-stack/config/routing.json' \
  --reason 'Apply reviewed agent reasoning policy'
```

The grant is bound to the current repository, route/change, Git HEAD, tree fingerprint, target patterns, and TTL. Create the manifest only after the grant, outside the repository, so it does not invalidate the tree binding.

## 2. Build a manifest outside the repository

```json
{
  "schema_version": 1,
  "operations": [
    {
      "path": ".grok/agents/architect.md",
      "expected_sha256": "<current lowercase SHA-256>",
      "content_base64": "<complete replacement bytes in base64>"
    },
    {
      "path": ".grok/agents/general_implementer.md",
      "expected_sha256": "<current lowercase SHA-256>",
      "content": "complete UTF-8 replacement text\n"
    }
  ]
}
```

Use `MISSING` as `expected_sha256` only when creating a new file under an existing control-plane directory. Every operation must contain exactly one of `content` or `content_base64`.

## 3. Validate, then apply atomically

```bash
python3 scripts/grok_protected_write.py --manifest /tmp/control-plane-write.json --dry-run
python3 scripts/grok_protected_write.py --manifest /tmp/control-plane-write.json
```

The writer validates the complete batch before the first mutation:

- the manifest is outside the repository;
- every target stays inside the repository and belongs to the configured control plane;
- Git metadata, secrets, symlinks, and non-regular files are rejected;
- every target has a matching exact protected-path grant;
- every current file hash matches `expected_sha256`;
- file and total batch size limits are enforced.

Files are staged in their target directories and replaced atomically per file. If a later replacement fails, already-replaced files are restored from the preflight snapshot. Arbitrary shell mutation remains denied.
