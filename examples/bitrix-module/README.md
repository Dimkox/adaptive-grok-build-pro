# Reference Bitrix module

A coherent structural example for custom development under `local/modules`:

- D7 namespace registration and ORM `DataManager`;
- compatible registration of a legacy main-module event;
- explicit event unregistering;
- database create/drop symmetry with a `savedata` escape hatch;
- Bitrix-agent cleanup during uninstall;
- service code that can be unit-tested without booting Bitrix.

It is a reference, not a marketplace-ready module. A real module still needs project-specific migrations, permissions, localization, update scripts, monitoring, and compatibility testing against the deployed Bitrix version.

Run the isolated service tests after installing dev dependencies:

```bash
composer install
composer test
```
