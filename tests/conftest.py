"""Test configuration for the i-airtable package.
"""
import os

import pytest

from i_airtable.connector import AirtableConnector

@pytest.fixture
def connector() -> AirtableConnector:
    """Fixture for Airtable connector.

    Returns:
        AirtableConnector: The Airtable connector.
    """
    # get the environment variable for the base ID and table name
    base_id = os.getenv('AIRTABLE_TEST_BASE_ID', '')
    table_name = 'test_table'

    # set the schema for the test table
    schema = {
        'Name': (str, ...),
        'Notes': (str, None)
    }

    # return the Airtable connector
    return AirtableConnector(
        base_id=base_id,
        table_name=table_name,
        schema=schema
    )
