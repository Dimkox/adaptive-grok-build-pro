# Factory preflight fixture-clock repair

Route `78b680187560`; writer `ai_implementer`. Root's full preflight passed every check except `factory-postgres-exit`, where three existing composition tests expected `artifact_ready` but received `rejected`. Before this repair, the factory diff against the routed base was empty; no historical-accounting import changed factory production behavior.

## Reproduction and root cause

The exact focused reproduction before editing fixtures was:

```bash
PYTHONPATH=factory/src python3 -m unittest factory.tests.test_landing_live.FactoryLiveAutoLandingTests.test_injected_executor_automatically_seals_complete_artifact factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_grok_compose_seals_complete_artifact_with_mocked_http factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_qwen_compose_seals_complete_artifact_with_mocked_http
```

```text
Ran 3 tests in 0.161s
FAILED (failures=3)
All three: AssertionError: 'artifact_ready' != 'rejected'
```

Read-only source tracing established the relevant boundary: `LandingApplicationService.submit` uses its injected clock to set `received_at` and a 24-hour expiry. `PrivateLandingBlobStore.read` compares expiry to its own clock and raises `blob_expired`; the normalizer turns that contract error into a rejected result. Both composition fixtures injected `FIXED_TIME` into their services but omitted the blob-store clock. A working SQLite fixture already injects one common frozen time into both components.

This bounded in-process diagnostic probe reproduced the rejection reason without changing production files or bypassing any check:

```bash
PYTHONPATH=factory/src python3 - <<'PY'
import unittest
from unittest.mock import patch
from adaptive_factory.landing_service import LandingApplicationService
from adaptive_factory.landing_intake import PrivateLandingBlobStore

original_submit = LandingApplicationService.submit
def observed_submit(self, *args, **kwargs):
    result = original_submit(self, *args, **kwargs)
    print('diagnostic', kwargs['job_id'], result.job.state, result.job.reason_code,
          'service_time', self._clock().isoformat(),
          'source_expiry', result.job.source.expires_at.isoformat())
    return result

original_init = PrivateLandingBlobStore.__init__
def observed_init(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    print('blob_clock', self._clock().isoformat(), 'injected', kwargs.get('clock') is not None)

names = [
    'factory.tests.test_landing_live.FactoryLiveAutoLandingTests.test_injected_executor_automatically_seals_complete_artifact',
    'factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_grok_compose_seals_complete_artifact_with_mocked_http',
    'factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_qwen_compose_seals_complete_artifact_with_mocked_http',
]
with patch.object(LandingApplicationService, 'submit', observed_submit), \
     patch.object(PrivateLandingBlobStore, '__init__', observed_init):
    result = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    raise SystemExit(not result.wasSuccessful())
PY
```

Observed before repair: all three reasons were `blob_expired`; all blob clocks were uninjected and read `2026-09-10T19:49:08Z` (fractional seconds omitted here). The first service used `2026-09-06T12:00:00Z` and expired its source at `2026-09-07T12:00:00Z`. The other two used `2026-09-06T19:00:00Z` and expired at `2026-09-07T19:00:00Z`. This directly confirmed the mixed-clock hypothesis.

## Repair and focused green

Add `clock=lambda: FIXED_TIME` to the existing `PrivateLandingBlobStore` constructor in each of:

- `factory/tests/test_landing_live.py`
- `factory/tests/test_landing_live_executors.py`

The factory diff is exactly two test-fixture lines. Existing artifact-readiness, member completeness, unavailable-provider and other assertions remain unchanged. No production expiry check, provider implementation, network policy or skip changed; the mocked HTTP transport remains in use.

Rerunning the exact three-test command above after the repair:

```text
Ran 3 tests in 0.840s
OK
```

Surrounding fixture tests and static checks:

```text
PYTHONPATH=factory/src python3 -m unittest factory.tests.test_landing_live factory.tests.test_landing_live_executors
Ran 18 tests in 0.917s
OK

ruff check factory/tests/test_landing_live.py factory/tests/test_landing_live_executors.py
All checks passed!

git diff --check
exit 0
```

The sole remaining verification work is root's disposable factory check and final routed verification/review. This focused repair does not claim those checks have passed and creates no receipt or delivery authority.
