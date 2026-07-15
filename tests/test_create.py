"""Test create functionality for the i-airtable package.
"""
# pyright: reportAttributeAccessIssue=false
from aracnid_core.base import BaseConnector


def test_create_record(connector: BaseConnector):
    """Test creating a record in Airtable.

    Args:
        connector (BaseConnector): Test fixture for the Airtable connector.
    """
    # set the fields for the record to be created
    fields = {
        'Name': 'Test Name',
        'Notes': 'Test Notes',
    }

    # create the record using the connector
    created_record = connector.create(fields)

    # assert that the record was created successfully
    assert created_record
    assert 'id' in created_record.model_fields_set
    assert created_record.source.type == 'airtable'
    assert created_record.Name == fields['Name']
    assert created_record.Notes == fields['Notes']
