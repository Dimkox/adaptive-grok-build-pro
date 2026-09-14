# PDF fixture verification recovery

Route `597b421e450b`; sole implementation owner continues PR #82. No PDF worker/runtime, dependency or lock change. The initial full verifier remains failed; final full verification is pending.

## Diagnosis before edits

`git diff origin/main -- factory/tests/test_landing_pdf_worker.py factory/src/adaptive_factory/resources/landing_pdf_worker.py factory/src/adaptive_factory/landing_media.py factory/uv.lock factory/pyproject.toml` was empty before fixture correction. The isolated module reproduced the same one failure with pinned parser 6.18.1, so no interaction with the newly added normalizer tests is needed.

The original fixture had one actual page and declared/actual xref offsets 371/371. Replacing `/Count 1>>` with `/Count 101>>` increased the body by two bytes without updating offsets: declared/actual xref became 371/373. Direct `PdfReader(io.BytesIO(payload), strict=True)` raised `PdfReadError: Broken xref table`; the child correctly maps that exception to `pdf_invalid`. A `PdfWriter` document with 101 actual blank pages parsed as 101 pages (12,639 bytes) and the existing real bounded child returned `pdf_page_limit`, confirming that parser capability and resource limits were not the failing boundary.

Isolated red command (exit 1):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:delivery/src:. uv run --project factory --locked python3 -m unittest factory.tests.test_landing_pdf_worker -v
```

```text
test_decoder_drift_is_rejected_before_any_spawn (factory.tests.test_landing_pdf_worker.PdfWorkerInputGuards.test_decoder_drift_is_rejected_before_any_spawn) ... ok
test_empty_payload_is_rejected_before_any_spawn (factory.tests.test_landing_pdf_worker.PdfWorkerInputGuards.test_empty_payload_is_rejected_before_any_spawn) ... ok
test_blank_pdf_reports_empty_or_scanned (factory.tests.test_landing_pdf_worker.PdfWorkerWithPinnedParser.test_blank_pdf_reports_empty_or_scanned) ... ok
test_corrupt_pdf_reports_invalid (factory.tests.test_landing_pdf_worker.PdfWorkerWithPinnedParser.test_corrupt_pdf_reports_invalid) ... ok
test_oversized_page_count_reports_page_limit (factory.tests.test_landing_pdf_worker.PdfWorkerWithPinnedParser.test_oversized_page_count_reports_page_limit) ... FAIL
test_textual_pdf_returns_normalized_text (factory.tests.test_landing_pdf_worker.PdfWorkerWithPinnedParser.test_textual_pdf_returns_normalized_text) ... ok
test_worker_executes_and_reports_parser_unavailable (factory.tests.test_landing_pdf_worker.PdfWorkerWithoutParser.test_worker_executes_and_reports_parser_unavailable) ... skipped 'pinned pypdf 6.18.1 present; unavailable branch cannot run'

======================================================================
FAIL: test_oversized_page_count_reports_page_limit (factory.tests.test_landing_pdf_worker.PdfWorkerWithPinnedParser.test_oversized_page_count_reports_page_limit)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_pdf_worker.py", line 120, in test_oversized_page_count_reports_page_limit
    self.assertEqual(ctx.exception.code, "pdf_page_limit")
AssertionError: 'pdf_invalid' != 'pdf_page_limit'
- pdf_invalid
+ pdf_page_limit


----------------------------------------------------------------------
Ran 7 tests in 2.162s

FAILED (failures=1, skipped=1)
```

## Fixture-only correction and focused result

Parameterize the existing blank-PDF helper using PdfWriter, produce 101 real pages for the limit test, and verify that 100 pages reach the existing empty-content rejection. The separate corrupt-PDF test stays unchanged.

Exit 0: 74 tests in 8.295s, one expected skip because the pinned parser is present and its unavailable branch cannot run.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:delivery/src:. uv run --project factory --locked python3 -m unittest factory.tests.test_landing_pdf_worker factory.tests.test_landing_normalizer factory.tests.test_landing_contracts factory.tests.test_landing_provider factory.tests.test_landing_live_executors -v
```

```text
test_decoder_drift_is_rejected_before_any_spawn (factory.tests.test_landing_pdf_worker.PdfWorkerInputGuards.test_decoder_drift_is_rejected_before_any_spawn) ... ok
test_empty_payload_is_rejected_before_any_spawn (factory.tests.test_landing_pdf_worker.PdfWorkerInputGuards.test_empty_payload_is_rejected_before_any_spawn) ... ok
test_blank_pdf_reports_empty_or_scanned (factory.tests.test_landing_pdf_worker.PdfWorkerWithPinnedParser.test_blank_pdf_reports_empty_or_scanned) ... ok
test_corrupt_pdf_reports_invalid (factory.tests.test_landing_pdf_worker.PdfWorkerWithPinnedParser.test_corrupt_pdf_reports_invalid) ... ok
test_maximum_page_count_reaches_content_validation (factory.tests.test_landing_pdf_worker.PdfWorkerWithPinnedParser.test_maximum_page_count_reaches_content_validation) ... ok
test_oversized_page_count_reports_page_limit (factory.tests.test_landing_pdf_worker.PdfWorkerWithPinnedParser.test_oversized_page_count_reports_page_limit) ... ok
test_textual_pdf_returns_normalized_text (factory.tests.test_landing_pdf_worker.PdfWorkerWithPinnedParser.test_textual_pdf_returns_normalized_text) ... ok
test_worker_executes_and_reports_parser_unavailable (factory.tests.test_landing_pdf_worker.PdfWorkerWithoutParser.test_worker_executes_and_reports_parser_unavailable) ... skipped 'pinned pypdf 6.18.1 present; unavailable branch cannot run'
test_duplicate_docx_document_members_are_rejected_in_both_orders (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_duplicate_docx_document_members_are_rejected_in_both_orders) ... ok
test_invalid_text_and_malformed_model_result_fail_closed (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_invalid_text_and_malformed_model_result_fail_closed) ... ok
test_malformed_sections_return_controlled_outcome_with_evidence (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_malformed_sections_return_controlled_outcome_with_evidence) ... ok
test_pdf_and_audio_need_human_before_blob_or_executor (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_pdf_and_audio_need_human_before_blob_or_executor) ... ok
test_profile_drift_is_rejected_before_blob_read (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_profile_drift_is_rejected_before_blob_read) ... ok
test_text_image_and_safe_docx_use_one_closed_executor_call (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_text_image_and_safe_docx_use_one_closed_executor_call) ... ok
test_unavailable_profile_stops_before_blob_read_or_executor (factory.tests.test_landing_normalizer.CodexLandingNormalizerTests.test_unavailable_profile_stops_before_blob_read_or_executor) ... ok
test_invalid_items_keep_their_strict_rejection (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_invalid_items_keep_their_strict_rejection) ... ok
test_item_limit_applies_before_deduplication (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_item_limit_applies_before_deduplication) ... ok
test_malformed_outer_sections_raise_contract_error (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_malformed_outer_sections_raise_contract_error) ... ok
test_mixed_language_and_escaped_items_have_stable_canonical_digest (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_mixed_language_and_escaped_items_have_stable_canonical_digest) ... ok
test_model_order_and_duplicates_are_canonicalized (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_model_order_and_duplicates_are_canonicalized) ... ok
test_section_fields_and_content_remain_closed (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_section_fields_and_content_remain_closed) ... ok
test_strict_spec_still_rejects_noncanonical_items_outside_decoder (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_strict_spec_still_rejects_noncanonical_items_outside_decoder) ... ok
test_twelve_sections_keep_their_original_order (factory.tests.test_landing_normalizer.DraftItemCanonicalizationTests.test_twelve_sections_keep_their_original_order) ... ok
test_all_six_records_are_closed_round_trip_and_digest_stable (factory.tests.test_landing_contracts.LandingContractTests.test_all_six_records_are_closed_round_trip_and_digest_stable) ... ok
test_asset_paths_are_unambiguous_site_relative_paths (factory.tests.test_landing_contracts.LandingContractTests.test_asset_paths_are_unambiguous_site_relative_paths) ... ok
test_attempt_ordinal_and_evaluator_collections_are_finite_and_closed (factory.tests.test_landing_contracts.LandingContractTests.test_attempt_ordinal_and_evaluator_collections_are_finite_and_closed) ... ok
test_input_binds_the_authoritative_repository_sha_and_tree (factory.tests.test_landing_contracts.LandingContractTests.test_input_binds_the_authoritative_repository_sha_and_tree) ... ok
test_json_parser_rejects_duplicate_keys_and_nonfinite_numbers (factory.tests.test_landing_contracts.LandingContractTests.test_json_parser_rejects_duplicate_keys_and_nonfinite_numbers) ... ok
test_published_v1_provider_evidence_digest_and_schema_remain_unchanged (factory.tests.test_landing_contracts.LandingContractTests.test_published_v1_provider_evidence_digest_and_schema_remain_unchanged) ... ok
test_six_json_schemas_and_frozen_openapi_snapshot_are_closed_version_one (factory.tests.test_landing_contracts.LandingContractTests.test_six_json_schemas_and_frozen_openapi_snapshot_are_closed_version_one) ... ok
test_spec_cta_paths_have_one_same_origin_root_relative_interpretation (factory.tests.test_landing_contracts.LandingContractTests.test_spec_cta_paths_have_one_same_origin_root_relative_interpretation) ... ok
test_spec_preserves_source_indexing_policy_without_provider_authority (factory.tests.test_landing_contracts.LandingContractTests.test_spec_preserves_source_indexing_policy_without_provider_authority) ... ok
test_spec_rejects_markup_remote_paths_and_policy_shaped_content (factory.tests.test_landing_contracts.LandingContractTests.test_spec_rejects_markup_remote_paths_and_policy_shaped_content) ... ok
test_v2_evidence_roundtrip_uses_independent_version_domain (factory.tests.test_landing_contracts.LandingContractTests.test_v2_evidence_roundtrip_uses_independent_version_domain) ... ok
test_blob_digest_mismatch_fails_without_process (factory.tests.test_landing_provider.LandingProviderTests.test_blob_digest_mismatch_fails_without_process) ... ok
test_explicit_sealed_fixture_normalizes_all_five_kinds_to_same_semantics (factory.tests.test_landing_provider.LandingProviderTests.test_explicit_sealed_fixture_normalizes_all_five_kinds_to_same_semantics) ... ok
test_outcome_state_spec_and_evidence_disposition_are_closed (factory.tests.test_landing_provider.LandingProviderTests.test_outcome_state_spec_and_evidence_disposition_are_closed) ... ok
test_profile_mismatch_and_executable_drift_fail_before_blob_read (factory.tests.test_landing_provider.LandingProviderTests.test_profile_mismatch_and_executable_drift_fail_before_blob_read) ... ok
test_profile_rejects_shell_or_environment_shaped_configuration (factory.tests.test_landing_provider.LandingProviderTests.test_profile_rejects_shell_or_environment_shaped_configuration) ... ok
test_stdout_stderr_and_wall_time_are_hard_bounded (factory.tests.test_landing_provider.LandingProviderTests.test_stdout_stderr_and_wall_time_are_hard_bounded) ... ok
test_strict_jsonl_and_closed_spec_fail_without_native_retention (factory.tests.test_landing_provider.LandingProviderTests.test_strict_jsonl_and_closed_spec_fail_without_native_retention) ... ok
test_unavailable_default_stops_before_blob_read_or_process_creation (factory.tests.test_landing_provider.LandingProviderTests.test_unavailable_default_stops_before_blob_read_or_process_creation) ... ok
test_http_malformed_sections_return_controlled_outcome_with_evidence (factory.tests.test_landing_live_executors.HttpLandingDraftNormalizationTests.test_http_malformed_sections_return_controlled_outcome_with_evidence) ... ok
test_http_provider_normalizes_mixed_language_unsorted_duplicate_items (factory.tests.test_landing_live_executors.HttpLandingDraftNormalizationTests.test_http_provider_normalizes_mixed_language_unsorted_duplicate_items) ... ok
test_empty_constructor_key_fails_closed (factory.tests.test_landing_live_executors.LandingLiveExecutorTests.test_empty_constructor_key_fails_closed) ... ok
test_factory_server_does_not_import_httpx_or_live_executors (factory.tests.test_landing_live_executors.LandingLiveExecutorTests.test_factory_server_does_not_import_httpx_or_live_executors) ... ok
test_grok_mock_transport_returns_draft_json (factory.tests.test_landing_live_executors.LandingLiveExecutorTests.test_grok_mock_transport_returns_draft_json) ... ok
test_host_requirements_match_current_python_and_httpx (factory.tests.test_landing_live_executors.LandingLiveExecutorTests.test_host_requirements_match_current_python_and_httpx) ... ok
test_http_error_status_fails_closed (factory.tests.test_landing_live_executors.LandingLiveExecutorTests.test_http_error_status_fails_closed) ... ok
test_landing_runtime_does_not_import_httpx (factory.tests.test_landing_live_executors.LandingLiveExecutorTests.test_landing_runtime_does_not_import_httpx) ... ok
test_malformed_body_fails_closed (factory.tests.test_landing_live_executors.LandingLiveExecutorTests.test_malformed_body_fails_closed) ... ok
test_missing_env_key_fails_closed (factory.tests.test_landing_live_executors.LandingLiveExecutorTests.test_missing_env_key_fails_closed) ... ok
test_non_https_base_url_fails_closed (factory.tests.test_landing_live_executors.LandingLiveExecutorTests.test_non_https_base_url_fails_closed) ... ok
test_pyproject_pins_match_host_record (factory.tests.test_landing_live_executors.LandingLiveExecutorTests.test_pyproject_pins_match_host_record) ... ok
test_qwen_mock_transport_returns_draft_json (factory.tests.test_landing_live_executors.LandingLiveExecutorTests.test_qwen_mock_transport_returns_draft_json) ... ok
test_sync_only_transport_is_rejected_before_any_request (factory.tests.test_landing_live_executors.LandingLiveExecutorTests.test_sync_only_transport_is_rejected_before_any_request) ... ok
test_transport_error_fails_closed (factory.tests.test_landing_live_executors.LandingLiveExecutorTests.test_transport_error_fails_closed) ... ok
test_compose_env_landing_grok_seals_with_mocked_http (factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_compose_env_landing_grok_seals_with_mocked_http) ... ok
test_compose_env_landing_unknown_provider_fails_closed (factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_compose_env_landing_unknown_provider_fails_closed) ... ok
test_compose_env_landing_unset_provider_returns_none (factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_compose_env_landing_unset_provider_returns_none) ... ok
test_explicit_qwen_region_rejects_conflicting_profile_before_credentials (factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_explicit_qwen_region_rejects_conflicting_profile_before_credentials) ... ok
test_grok_compose_seals_complete_artifact_with_mocked_http (factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_grok_compose_seals_complete_artifact_with_mocked_http) ... ok
test_malformed_sections_persist_controlled_reason_and_evidence (factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_malformed_sections_persist_controlled_reason_and_evidence) ... ok
test_qwen_compose_seals_complete_artifact_with_mocked_http (factory.tests.test_landing_live_executors.LandingLiveGrokQwenCompositionTests.test_qwen_compose_seals_complete_artifact_with_mocked_http) ... ok
test_environment_alias_has_explicit_project_key_precedence (factory.tests.test_landing_live_executors.QwenCredentialAndProfileTests.test_environment_alias_has_explicit_project_key_precedence) ... ok
test_explicit_file_reads_only_standard_assignment_without_interpolation (factory.tests.test_landing_live_executors.QwenCredentialAndProfileTests.test_explicit_file_reads_only_standard_assignment_without_interpolation) ... ok
test_file_rejects_missing_duplicate_empty_expansion_and_malformed_values (factory.tests.test_landing_live_executors.QwenCredentialAndProfileTests.test_file_rejects_missing_duplicate_empty_expansion_and_malformed_values) ... ok
test_malformed_provider_unicode_is_closed_at_decoder_and_probe_cli (factory.tests.test_landing_live_executors.QwenCredentialAndProfileTests.test_malformed_provider_unicode_is_closed_at_decoder_and_probe_cli) ... ok
test_private_file_mode_symlink_size_and_path_rejection (factory.tests.test_landing_live_executors.QwenCredentialAndProfileTests.test_private_file_mode_symlink_size_and_path_rejection) ... ok
test_probe_cli_failure_never_prints_exception_or_credential (factory.tests.test_landing_live_executors.QwenCredentialAndProfileTests.test_probe_cli_failure_never_prints_exception_or_credential) ... ok
test_probe_rejects_invalid_draft_after_valid_http_envelope (factory.tests.test_landing_live_executors.QwenCredentialAndProfileTests.test_probe_rejects_invalid_draft_after_valid_http_envelope) ... ok
test_probe_rejects_malformed_draft_and_usage (factory.tests.test_landing_live_executors.QwenCredentialAndProfileTests.test_probe_rejects_malformed_draft_and_usage) ... ok
test_probe_uses_real_executor_decoder_and_reports_only_safe_facts (factory.tests.test_landing_live_executors.QwenCredentialAndProfileTests.test_probe_uses_real_executor_decoder_and_reports_only_safe_facts) ... ok
test_qwen_intl_is_pinned_and_distinct_from_existing_china_profile (factory.tests.test_landing_live_executors.QwenCredentialAndProfileTests.test_qwen_intl_is_pinned_and_distinct_from_existing_china_profile) ... ok

----------------------------------------------------------------------
Ran 74 tests in 8.295s

OK (skipped=1)
```

Ruff exit 0:

```sh
ruff check factory/src/adaptive_factory/landing_normalizer.py factory/tests/test_landing_normalizer.py factory/tests/test_landing_live_executors.py factory/tests/test_landing_pdf_worker.py
```

```text
All checks passed!
```

Verified file hashes:

```json
{
  "factory/src/adaptive_factory/landing_normalizer.py": "f6cc54452df605e9bcfbf163d0ce567cb1c74ece4501f29a9292674af30fbf9e",
  "factory/tests/test_landing_normalizer.py": "58e51dcb3fcae2893c76f89a5938761bdddd8679f6e191e9d8fb9024432daaf2",
  "factory/tests/test_landing_live_executors.py": "ca269aef9424ffd70e4e26497d38874f052c62f4e63244b469c80b3cbec947b9",
  "factory/tests/test_landing_pdf_worker.py": "c736d9bc9bf7e5c6b1d1e86e3b8feb2734623188ecdad22cda306800f0250f22",
  "factory/src/adaptive_factory/resources/landing_pdf_worker.py": "55d527a6fbaa3e54340cb0fba9764c4b3682610b38c6b4d7555304b9432454ae"
}
```
