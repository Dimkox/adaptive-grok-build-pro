# Review-repair TDD red evidence

Route `597b421e450b`; PR #82 pre-repair production head `18822bd08149f347c71cb9130c4e05b059ad289e`. Tests were added before changing production source; the captured run exits 1 with 18 tests, eight failing subtests and 13 error subtests. The errors below are the reproduced decoder exceptions, not setup failures.

Command:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:delivery/src:. python3 -m unittest factory.tests.test_landing_normalizer factory.tests.test_landing_live_executors.HttpLandingDraftNormalizationTests factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_malformed_sections_persist_controlled_reason_and_evidence -v
```

```text
test_duplicate_docx_document_members_are_rejected_in_both_orders (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_duplicate_docx_document_members_are_rejected_in_both_orders) ... ok
test_invalid_text_and_malformed_model_result_fail_closed (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_invalid_text_and_malformed_model_result_fail_closed) ... ok
test_malformed_sections_return_controlled_outcome_with_evidence (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_malformed_sections_return_controlled_outcome_with_evidence) ...
  test_malformed_sections_return_controlled_outcome_with_evidence (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_malformed_sections_return_controlled_outcome_with_evidence) (sections=None) ... ERROR
  test_malformed_sections_return_controlled_outcome_with_evidence (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_malformed_sections_return_controlled_outcome_with_evidence) (sections=3) ... ERROR
  test_malformed_sections_return_controlled_outcome_with_evidence (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_malformed_sections_return_controlled_outcome_with_evidence) (sections=True) ... ERROR
test_pdf_and_audio_need_human_before_blob_or_executor (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_pdf_and_audio_need_human_before_blob_or_executor) ... ok
test_profile_drift_is_rejected_before_blob_read (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_profile_drift_is_rejected_before_blob_read) ... ok
test_text_image_and_safe_docx_use_one_closed_executor_call (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_text_image_and_safe_docx_use_one_closed_executor_call) ... ok
test_unavailable_profile_stops_before_blob_read_or_executor (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_unavailable_profile_stops_before_blob_read_or_executor) ... ok
test_invalid_items_keep_their_strict_rejection (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_invalid_items_keep_their_strict_rejection) ... ok
test_item_limit_applies_before_deduplication (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_item_limit_applies_before_deduplication) ...
  test_item_limit_applies_before_deduplication (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_item_limit_applies_before_deduplication) (items=['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a']) ... FAIL
test_malformed_outer_sections_raise_contract_error (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_malformed_outer_sections_raise_contract_error) ...
  test_malformed_outer_sections_raise_contract_error (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_malformed_outer_sections_raise_contract_error) (sections=None) ... ERROR
  test_malformed_outer_sections_raise_contract_error (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_malformed_outer_sections_raise_contract_error) (sections=3) ... ERROR
  test_malformed_outer_sections_raise_contract_error (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_malformed_outer_sections_raise_contract_error) (sections=1.5) ... ERROR
  test_malformed_outer_sections_raise_contract_error (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_malformed_outer_sections_raise_contract_error) (sections=True) ... ERROR
  test_malformed_outer_sections_raise_contract_error (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_malformed_outer_sections_raise_contract_error) (sections=False) ... ERROR
  test_malformed_outer_sections_raise_contract_error (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_malformed_outer_sections_raise_contract_error) (sections='section') ... FAIL
  test_malformed_outer_sections_raise_contract_error (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_malformed_outer_sections_raise_contract_error) (sections={'items': []}) ... FAIL
test_mixed_language_and_escaped_items_have_stable_canonical_digest (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_mixed_language_and_escaped_items_have_stable_canonical_digest) ...
  test_mixed_language_and_escaped_items_have_stable_canonical_digest (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_mixed_language_and_escaped_items_have_stable_canonical_digest) (expected=('é', 'a')) ... ERROR
  test_mixed_language_and_escaped_items_have_stable_canonical_digest (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_mixed_language_and_escaped_items_have_stable_canonical_digest) (expected=('A', '"quoted"', '\\path', '\nitem', '\titem', 'é', 'Ж', '中', 'a')) ... ERROR
test_model_order_and_duplicates_are_canonicalized (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_model_order_and_duplicates_are_canonicalized) ... ok
test_section_fields_and_content_remain_closed (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_section_fields_and_content_remain_closed) ... ok
test_strict_spec_still_rejects_noncanonical_items_outside_decoder (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_strict_spec_still_rejects_noncanonical_items_outside_decoder) ... ok
test_twelve_sections_keep_their_original_order (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_twelve_sections_keep_their_original_order) ... ok
test_http_malformed_sections_return_controlled_outcome_with_evidence (factory.tests.test_landing_live_executors.HttpLandingDraftNormalizationTests.test_http_malformed_sections_return_controlled_outcome_with_evidence) ...
  test_http_malformed_sections_return_controlled_outcome_with_evidence (factory.tests.test_landing_live_executors.HttpLandingDraftNormalizationTests.test_http_malformed_sections_return_controlled_outcome_with_evidence) (sections=None) ... ERROR
  test_http_malformed_sections_return_controlled_outcome_with_evidence (factory.tests.test_landing_live_executors.HttpLandingDraftNormalizationTests.test_http_malformed_sections_return_controlled_outcome_with_evidence) (sections=3) ... ERROR
  test_http_malformed_sections_return_controlled_outcome_with_evidence (factory.tests.test_landing_live_executors.HttpLandingDraftNormalizationTests.test_http_malformed_sections_return_controlled_outcome_with_evidence) (sections=True) ... ERROR
test_http_provider_normalizes_mixed_language_unsorted_duplicate_items (factory.tests.test_landing_live_executors.HttpLandingDraftNormalizationTests.test_http_provider_normalizes_mixed_language_unsorted_duplicate_items) ...
  test_http_provider_normalizes_mixed_language_unsorted_duplicate_items (factory.tests.test_landing_live_executors.HttpLandingDraftNormalizationTests.test_http_provider_normalizes_mixed_language_unsorted_duplicate_items) (provider='grok') ... FAIL
  test_http_provider_normalizes_mixed_language_unsorted_duplicate_items (factory.tests.test_landing_live_executors.HttpLandingDraftNormalizationTests.test_http_provider_normalizes_mixed_language_unsorted_duplicate_items) (provider='qwen') ... FAIL
test_malformed_sections_persist_controlled_reason_and_evidence (factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_malformed_sections_persist_controlled_reason_and_evidence) ...
  test_malformed_sections_persist_controlled_reason_and_evidence (factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_malformed_sections_persist_controlled_reason_and_evidence) (sections=None) ... FAIL
  test_malformed_sections_persist_controlled_reason_and_evidence (factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_malformed_sections_persist_controlled_reason_and_evidence) (sections=3) ... FAIL
  test_malformed_sections_persist_controlled_reason_and_evidence (factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_malformed_sections_persist_controlled_reason_and_evidence) (sections=True) ... FAIL

======================================================================
ERROR: test_malformed_sections_return_controlled_outcome_with_evidence (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_malformed_sections_return_controlled_outcome_with_evidence) (sections=None)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_normalizer.py", line 427, in test_malformed_sections_return_controlled_outcome_with_evidence
    outcome, _ = self.normalize(
                 ^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_normalizer.py", line 279, in normalize
    ).normalize(
      ^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 279, in normalize
    spec = self._decode_result(request, result)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 384, in _decode_result
    return decode_landing_draft(
           ^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 472, in decode_landing_draft
    for section in draft["sections"]:
TypeError: 'NoneType' object is not iterable

======================================================================
ERROR: test_malformed_sections_return_controlled_outcome_with_evidence (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_malformed_sections_return_controlled_outcome_with_evidence) (sections=3)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_normalizer.py", line 427, in test_malformed_sections_return_controlled_outcome_with_evidence
    outcome, _ = self.normalize(
                 ^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_normalizer.py", line 279, in normalize
    ).normalize(
      ^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 279, in normalize
    spec = self._decode_result(request, result)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 384, in _decode_result
    return decode_landing_draft(
           ^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 472, in decode_landing_draft
    for section in draft["sections"]:
TypeError: 'int' object is not iterable

======================================================================
ERROR: test_malformed_sections_return_controlled_outcome_with_evidence (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_malformed_sections_return_controlled_outcome_with_evidence) (sections=True)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_normalizer.py", line 427, in test_malformed_sections_return_controlled_outcome_with_evidence
    outcome, _ = self.normalize(
                 ^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_normalizer.py", line 279, in normalize
    ).normalize(
      ^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 279, in normalize
    spec = self._decode_result(request, result)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 384, in _decode_result
    return decode_landing_draft(
           ^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 472, in decode_landing_draft
    for section in draft["sections"]:
TypeError: 'bool' object is not iterable

======================================================================
ERROR: test_malformed_outer_sections_raise_contract_error (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_malformed_outer_sections_raise_contract_error) (sections=None)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_normalizer.py", line 175, in test_malformed_outer_sections_raise_contract_error
    decode_landing_draft(
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 472, in decode_landing_draft
    for section in draft["sections"]:
TypeError: 'NoneType' object is not iterable

======================================================================
ERROR: test_malformed_outer_sections_raise_contract_error (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_malformed_outer_sections_raise_contract_error) (sections=3)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_normalizer.py", line 175, in test_malformed_outer_sections_raise_contract_error
    decode_landing_draft(
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 472, in decode_landing_draft
    for section in draft["sections"]:
TypeError: 'int' object is not iterable

======================================================================
ERROR: test_malformed_outer_sections_raise_contract_error (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_malformed_outer_sections_raise_contract_error) (sections=1.5)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_normalizer.py", line 175, in test_malformed_outer_sections_raise_contract_error
    decode_landing_draft(
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 472, in decode_landing_draft
    for section in draft["sections"]:
TypeError: 'float' object is not iterable

======================================================================
ERROR: test_malformed_outer_sections_raise_contract_error (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_malformed_outer_sections_raise_contract_error) (sections=True)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_normalizer.py", line 175, in test_malformed_outer_sections_raise_contract_error
    decode_landing_draft(
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 472, in decode_landing_draft
    for section in draft["sections"]:
TypeError: 'bool' object is not iterable

======================================================================
ERROR: test_malformed_outer_sections_raise_contract_error (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_malformed_outer_sections_raise_contract_error) (sections=False)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_normalizer.py", line 175, in test_malformed_outer_sections_raise_contract_error
    decode_landing_draft(
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 472, in decode_landing_draft
    for section in draft["sections"]:
TypeError: 'bool' object is not iterable

======================================================================
ERROR: test_mixed_language_and_escaped_items_have_stable_canonical_digest (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_mixed_language_and_escaped_items_have_stable_canonical_digest) (expected=('é', 'a'))
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_normalizer.py", line 163, in test_mixed_language_and_escaped_items_have_stable_canonical_digest
    spec = decode_landing_draft(
           ^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 481, in decode_landing_draft
    return StaticLandingSpecV1.from_facts(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_contracts.py", line 379, in from_facts
    sections = tuple(LandingSectionV1.from_dict(item) for item in sections_raw)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_contracts.py", line 379, in <genexpr>
    sections = tuple(LandingSectionV1.from_dict(item) for item in sections_raw)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_contracts.py", line 295, in from_dict
    items = _sorted_unique(data["items"], "section_items", lambda item: _plain(item, "item", 512), maximum=12)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_contracts.py", line 143, in _sorted_unique
    raise LandingContractError(name)
adaptive_factory.landing_contracts.LandingContractError: section_items

======================================================================
ERROR: test_mixed_language_and_escaped_items_have_stable_canonical_digest (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_mixed_language_and_escaped_items_have_stable_canonical_digest) (expected=('A', '"quoted"', '\\path', '\nitem', '\titem', 'é', 'Ж', '中', 'a'))
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_normalizer.py", line 163, in test_mixed_language_and_escaped_items_have_stable_canonical_digest
    spec = decode_landing_draft(
           ^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 481, in decode_landing_draft
    return StaticLandingSpecV1.from_facts(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_contracts.py", line 379, in from_facts
    sections = tuple(LandingSectionV1.from_dict(item) for item in sections_raw)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_contracts.py", line 379, in <genexpr>
    sections = tuple(LandingSectionV1.from_dict(item) for item in sections_raw)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_contracts.py", line 295, in from_dict
    items = _sorted_unique(data["items"], "section_items", lambda item: _plain(item, "item", 512), maximum=12)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_contracts.py", line 143, in _sorted_unique
    raise LandingContractError(name)
adaptive_factory.landing_contracts.LandingContractError: section_items

======================================================================
ERROR: test_http_malformed_sections_return_controlled_outcome_with_evidence (factory.tests.test_landing_live_executors.HttpLandingDraftNormalizationTests.test_http_malformed_sections_return_controlled_outcome_with_evidence) (sections=None)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_live_executors.py", line 247, in test_http_malformed_sections_return_controlled_outcome_with_evidence
    outcome, request = self.normalize({**document, "sections": sections})
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_live_executors.py", line 222, in normalize
    outcome = HttpLandingNormalizer(profile, executor, clock=lambda: FIXED_TIME).normalize(
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_http.py", line 247, in normalize
    spec = decode_landing_draft(
           ^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 472, in decode_landing_draft
    for section in draft["sections"]:
TypeError: 'NoneType' object is not iterable

======================================================================
ERROR: test_http_malformed_sections_return_controlled_outcome_with_evidence (factory.tests.test_landing_live_executors.HttpLandingDraftNormalizationTests.test_http_malformed_sections_return_controlled_outcome_with_evidence) (sections=3)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_live_executors.py", line 247, in test_http_malformed_sections_return_controlled_outcome_with_evidence
    outcome, request = self.normalize({**document, "sections": sections})
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_live_executors.py", line 222, in normalize
    outcome = HttpLandingNormalizer(profile, executor, clock=lambda: FIXED_TIME).normalize(
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_http.py", line 247, in normalize
    spec = decode_landing_draft(
           ^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 472, in decode_landing_draft
    for section in draft["sections"]:
TypeError: 'int' object is not iterable

======================================================================
ERROR: test_http_malformed_sections_return_controlled_outcome_with_evidence (factory.tests.test_landing_live_executors.HttpLandingDraftNormalizationTests.test_http_malformed_sections_return_controlled_outcome_with_evidence) (sections=True)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_live_executors.py", line 247, in test_http_malformed_sections_return_controlled_outcome_with_evidence
    outcome, request = self.normalize({**document, "sections": sections})
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_live_executors.py", line 222, in normalize
    outcome = HttpLandingNormalizer(profile, executor, clock=lambda: FIXED_TIME).normalize(
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_http.py", line 247, in normalize
    spec = decode_landing_draft(
           ^^^^^^^^^^^^^^^^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/src/adaptive_factory/landing_normalizer.py", line 472, in decode_landing_draft
    for section in draft["sections"]:
TypeError: 'bool' object is not iterable

======================================================================
FAIL: test_item_limit_applies_before_deduplication (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_item_limit_applies_before_deduplication) (items=['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'])
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_normalizer.py", line 195, in test_item_limit_applies_before_deduplication
    with self.subTest(items=items), self.assertRaisesRegex(LandingContractError, "^section_items$"):
AssertionError: LandingContractError not raised

======================================================================
FAIL: test_malformed_outer_sections_raise_contract_error (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_malformed_outer_sections_raise_contract_error) (sections='section')
----------------------------------------------------------------------
adaptive_factory.landing_contracts.LandingContractError: invalid_object: landing_section

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_normalizer.py", line 174, in test_malformed_outer_sections_raise_contract_error
    with self.subTest(sections=sections), self.assertRaisesRegex(LandingContractError, "^sections$"):
AssertionError: "^sections$" does not match "invalid_object: landing_section"

======================================================================
FAIL: test_malformed_outer_sections_raise_contract_error (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_malformed_outer_sections_raise_contract_error) (sections={'items': []})
----------------------------------------------------------------------
adaptive_factory.landing_contracts.LandingContractError: invalid_object: landing_section

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_normalizer.py", line 174, in test_malformed_outer_sections_raise_contract_error
    with self.subTest(sections=sections), self.assertRaisesRegex(LandingContractError, "^sections$"):
AssertionError: "^sections$" does not match "invalid_object: landing_section"

======================================================================
FAIL: test_http_provider_normalizes_mixed_language_unsorted_duplicate_items (factory.tests.test_landing_live_executors.HttpLandingDraftNormalizationTests.test_http_provider_normalizes_mixed_language_unsorted_duplicate_items) (provider='grok')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_live_executors.py", line 233, in test_http_provider_normalizes_mixed_language_unsorted_duplicate_items
    self.assertEqual(("normalized", "normalized"),
AssertionError: Tuples differ: ('normalized', 'normalized') != ('needs_human', 'http_outcome_unusable')

First differing element 0:
'normalized'
'needs_human'

- ('normalized', 'normalized')
+ ('needs_human', 'http_outcome_unusable')

======================================================================
FAIL: test_http_provider_normalizes_mixed_language_unsorted_duplicate_items (factory.tests.test_landing_live_executors.HttpLandingDraftNormalizationTests.test_http_provider_normalizes_mixed_language_unsorted_duplicate_items) (provider='qwen')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_live_executors.py", line 233, in test_http_provider_normalizes_mixed_language_unsorted_duplicate_items
    self.assertEqual(("normalized", "normalized"),
AssertionError: Tuples differ: ('normalized', 'normalized') != ('needs_human', 'http_outcome_unusable')

First differing element 0:
'normalized'
'needs_human'

- ('normalized', 'normalized')
+ ('needs_human', 'http_outcome_unusable')

======================================================================
FAIL: test_malformed_sections_persist_controlled_reason_and_evidence (factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_malformed_sections_persist_controlled_reason_and_evidence) (sections=None)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_live_executors.py", line 314, in test_malformed_sections_persist_controlled_reason_and_evidence
    self.assertEqual(("needs_human", "http_outcome_unusable"),
AssertionError: Tuples differ: ('needs_human', 'http_outcome_unusable') != ('needs_human', 'internal_failure')

First differing element 1:
'http_outcome_unusable'
'internal_failure'

- ('needs_human', 'http_outcome_unusable')
+ ('needs_human', 'internal_failure')

======================================================================
FAIL: test_malformed_sections_persist_controlled_reason_and_evidence (factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_malformed_sections_persist_controlled_reason_and_evidence) (sections=3)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_live_executors.py", line 314, in test_malformed_sections_persist_controlled_reason_and_evidence
    self.assertEqual(("needs_human", "http_outcome_unusable"),
AssertionError: Tuples differ: ('needs_human', 'http_outcome_unusable') != ('needs_human', 'internal_failure')

First differing element 1:
'http_outcome_unusable'
'internal_failure'

- ('needs_human', 'http_outcome_unusable')
+ ('needs_human', 'internal_failure')

======================================================================
FAIL: test_malformed_sections_persist_controlled_reason_and_evidence (factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_malformed_sections_persist_controlled_reason_and_evidence) (sections=True)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_live_executors.py", line 314, in test_malformed_sections_persist_controlled_reason_and_evidence
    self.assertEqual(("needs_human", "http_outcome_unusable"),
AssertionError: Tuples differ: ('needs_human', 'http_outcome_unusable') != ('needs_human', 'internal_failure')

First differing element 1:
'http_outcome_unusable'
'internal_failure'

- ('needs_human', 'http_outcome_unusable')
+ ('needs_human', 'internal_failure')

----------------------------------------------------------------------
Ran 18 tests in 0.254s

FAILED (failures=8, errors=13)
```
