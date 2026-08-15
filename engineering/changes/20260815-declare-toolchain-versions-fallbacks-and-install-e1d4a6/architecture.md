# Architecture

`.grok-stack/config/toolchain.json` is the pin list. Doctor compares detected versions to `minimum`. Newer than `built` is OK. Missing/old tools get an install command for `fallback` (or newer).
