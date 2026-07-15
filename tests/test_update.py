"""Test update functionality for the i-airtable package.
"""
# pyright: reportAttributeAccessIssue=false
from aracnid_core.base import BaseConnector


def test_update_record(connector: BaseConnector):
    """Test updating a record in Airtable.

    Args:
        connector (BaseConnector): Test fixture for the Airtable connector.
    """
    # create a new record to be updated
    fields = {
        'Name': 'Initial Name',
        'Notes': 'Initial Notes',
    }
    created_record = connector.create(fields)
    record_id = created_record.id
    assert record_id, "Record ID should not be empty"

    # update the record using the connector
    updated_fields = {
        'Name': 'Updated Name',
        'Notes': 'Updated Notes',
    }
    updated_record = connector.update_one(record_id, updated_fields)

    # assert that the record was updated successfully
    assert updated_record
    assert updated_record.source.type == 'airtable'
    assert updated_record.Name == updated_fields['Name']
    assert updated_record.Notes == updated_fields['Notes']

def test_update_many_records(connector: BaseConnector):
    """Test updating multiple records in Airtable.

    Args:
        connector (BaseConnector): Test fixture for the Airtable connector.
    """
    # create a new record to be updated
    fields = {
        'Name': 'Initial Name',
        'Notes': 'Initial Notes',
    }
    created_record = connector.create(fields)
    record_id = created_record.id
    assert record_id, "Record ID should not be empty"

    # update the record using the connector
    updated_fields = {
        'Name': 'Updated Name',
        'Notes': 'Updated Notes',
    }
    updated_records = connector.update_many(
        filter=fields,
        fields=updated_fields
    )

    # assert that the records were updated successfully
    assert isinstance(updated_records, list), "Updated records should be a list"
    assert len(updated_records) >= 1, "Should have exactly one updated record"
    assert updated_records[0].source.type == 'airtable'
    assert updated_records[0].Name == updated_fields['Name']
    assert updated_records[0].Notes == updated_fields['Notes']

def test_replace_record(connector: BaseConnector):
    """Test replacing a record in Airtable.

    Args:
        connector (BaseConnector): Test fixture for the Airtable connector.
    """
    # create a new record to be replaced
    fields = {
        'Name': 'Initial Name',
        'Notes': 'Initial Notes',
    }
    created_record = connector.create(fields)
    record_id = created_record.id
    assert record_id, "Record ID should not be empty"

    # replace the record using the connector
    replacement_fields = {
        'Name': 'Replaced Name',
        'Notes': 'Replaced Notes',
    }
    replaced_record = connector.replace(record_id, replacement_fields)

    # assert that the record was replaced successfully
    assert replaced_record
    assert replaced_record.source.type == 'airtable'
    assert replaced_record.Name == replacement_fields['Name']
    assert replaced_record.Notes == replacement_fields['Notes']