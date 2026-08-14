# Custom module lifecycle

A custom module normally needs a stable module ID, install metadata, `include.php`, namespaced classes under `lib/`, language phrases, and explicit installation/update/uninstall behavior.

Review checklist:

- `RegisterModule` and `UnRegisterModule` symmetry.
- Event handler registration and unregistration symmetry.
- Agents/jobs removed during uninstall.
- Database objects, files, options, and permissions have documented uninstall policy.
- Updates are versioned and safe to rerun.
- Module namespace/autoload matches directory and class layout.
- No business data is silently deleted on routine uninstall.
- Localization exists for administrative/user-facing text.
