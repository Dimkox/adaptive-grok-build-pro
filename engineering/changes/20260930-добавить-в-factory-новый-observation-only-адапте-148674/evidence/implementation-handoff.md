# Implementation handoff

Source commit: `6e170318`

## Delivered

- closed versioned Qwen/OpenRouter candidate registry with exact upstream provenance;
- default-off deterministic selection and cooldown advice;
- bounded caller-owned transport attempts with retry only before response start;
- fatal authentication, payment, daily-limit and policy outcomes;
- tenant/repository/task/run/attempt/fence/budget/registry binding on evidence;
- incomplete usage remains unknown and forces `needs_human`;
- no endpoint, credential, header/body, home-directory or settings interface.

The source repository `Dimkox/qwen-model-rotator@b76a09849c132ab62f73bee76f949bd600bc4649`
had no observed license. Its code was not copied; the independent implementation uses only
the explicitly authorized behavioral idea and records provenance.

## Verification observations

- RED: `PYTHONPATH=factory/src python3 -m unittest factory/tests/test_model_rotator.py`
  failed because `adaptive_factory.model_rotator` did not exist.
- Focused GREEN: the same command passed 7 tests.
- Related GREEN: model rotator, landing failover and prediction contracts passed 17 tests.
- Factory discovery GREEN: `PYTHONPATH=factory/src taskset -c 0-27 python3 -m unittest discover -s factory/tests -t factory -p 'test_*.py'`
  passed 956 tests with 166 conditional skips in 74.015 seconds.
- An exploratory full `grok_verify --mode pr` reached repository coverage and was cancelled
  on coordinator request to avoid contending with the authoritative integrated run. It is
  `NOT_RUN` for completion purposes; no verification receipt was recorded.

Live provider calls and qualification are `NOT_RUN`. Independent route reviews and the
authoritative integrated full verifier remain coordinator-owned.
