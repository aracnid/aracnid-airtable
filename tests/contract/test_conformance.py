from __future__ import annotations

import os

import pytest

from aracnid_core.contract_tests import base_connector_contract as contract_tests
from aracnid_core.contract_tests import (
    query_dsl_temporal_contract as temporal_contract_tests,
    query_dsl_sort_contract as sort_contract_tests,
)
from aracnid_airtable.connector import AirtableConnector


@pytest.fixture
def connector():
    """Contract fixture expected by shared aracnid-core contract tests.
    Uses env vars so tests can run against a real Airtable table.
    """
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    table_name = os.getenv("AIRTABLE_TABLE_NAME")

    if not api_key or not base_id or not table_name:
        pytest.skip(
            "Contract tests require AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME"
        )

    return AirtableConnector(
        base_id=base_id,
        table_name=table_name,
    )


# Re-export shared tests into THIS repo's pytest discovery.
test_required_capabilities_keys = contract_tests.test_required_capabilities_keys
test_read_many_returns_list = contract_tests.test_read_many_returns_list
test_read_one_validates_input = contract_tests.test_read_one_validates_input
test_create_one_validates_input = contract_tests.test_create_one_validates_input
test_update_one_validates_input = contract_tests.test_update_one_validates_input
test_replace_one_validates_input = contract_tests.test_replace_one_validates_input
test_delete_one_validates_input = contract_tests.test_delete_one_validates_input
test_input_objects_not_mutated = contract_tests.test_input_objects_not_mutated

# Re-export Query DSL Sort contract tests
test_normalize_sort_accepts_none = (
    sort_contract_tests.test_normalize_sort_accepts_none
)
test_normalize_sort_accepts_single_and_multi = (
    sort_contract_tests.test_normalize_sort_accepts_single_and_multi
)
test_normalize_sort_rejects_invalid_shapes = (
    sort_contract_tests.test_normalize_sort_rejects_invalid_shapes
)
test_normalize_sort_rejects_duplicate_fields = (
    sort_contract_tests.test_normalize_sort_rejects_duplicate_fields
)

# Re-export Query DSL temporal contract tests.
test_normalize_query_accepts_timezone_aware_datetime_local_tz = (
    temporal_contract_tests.test_normalize_query_accepts_timezone_aware_datetime_local_tz
)
test_normalize_query_accepts_timezone_aware_datetime_utc = (
    temporal_contract_tests.test_normalize_query_accepts_timezone_aware_datetime_utc
)
test_normalize_query_rejects_naive_datetime = (
    temporal_contract_tests.test_normalize_query_rejects_naive_datetime
)
test_normalize_query_date_literal_still_valid = (
    temporal_contract_tests.test_normalize_query_date_literal_still_valid
)