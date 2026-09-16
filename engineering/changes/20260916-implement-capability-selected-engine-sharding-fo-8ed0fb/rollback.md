# Rollback

forward_fix <=2: revert restores main's `_python`/`_command_check` and deletes the runner module (unreferenced with it); no external state, no installed components, nothing deployed. Opt-in config files (if any exist on a host) become inert; runner output was never merge authority, so rollback cannot fake evidence.
