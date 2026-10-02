# Repository exploration

Read-only analysis compared source `531089f1709d7b707a76aeae23a35cbd1b238a61` with PR2 head `c78dfb301d4b957d338f9fbc61d1a9e6a7bf1fe5`. The genuinely new runtime delta is the cumulative `total_usd_micros` integer guard. Source tests had moved to `factory/tests/decision_contract_cases.py`; the historical audit signature fix was already present and the predecessor report was obsolete. A direct reproduction returned `9223372036854775927`, proving current aggregate overflow.
