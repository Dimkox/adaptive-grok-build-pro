# Architecture

Use shared Unicode-aware matching for short (at most four characters) single-word domain keywords in route scoring and development-prompt detection; preserve longer keyword/phrase behavior, intent precedence and genuinely selected specialist owners. Persist optional bounded matched_keywords in new route records and admit/validate it in the closed reader while older records remain valid.

The issue requests a general-owner fallback for short-only matches while also preserving genuine short-keyword specialist tasks. Apply fallback only when boundary filtering leaves no supported domain; do not demote valid SQL, UI or Bitrix D7 work. This bounded compatibility ruling is supported by independent architecture analysis. PR #140 owns release/review intent precedence and stays separate.

No new service, dependency or production-state change.
