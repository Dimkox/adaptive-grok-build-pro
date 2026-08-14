# Bitrix local guidance

Custom Bitrix work belongs under `local/`. Treat `bitrix/modules`, `bitrix/components`, and `bitrix/js` as protected core paths.

- Prefer D7 APIs: `Bitrix\Main\Loader`, `EventManager`, ORM `DataManager`.
- Encapsulate Bitrix APIs behind project services. Do not spread globals through domain code.
- Install, update, and uninstall must be symmetrical. Register and unregister event handlers explicitly. Remove module agents on uninstall.
- Keep business logic out of component templates. Validate and authorize request data.
- Account for managed cache, tag cache, composite mode, permissions, and multilingual phrases.
- Never patch Bitrix core as a routine fix.
