"""Test read functionality for the i-airtable package.
"""
# pyright: reportAttributeAccessIssue=false
from aracnid_core.base import BaseConnector


def test_read_record(connector: BaseConnector):
    """Test creating a record in Airtable.

    Args:
        connector (BaseConnector): Test fixture for the Airtable connector.
    """
    # create a new record to be read
    fields = {
        'Name': 'Test Name',
        'Notes': 'Test Notes',
    }
    created_record = connector.create(fields)
    record_id = created_record.id
    assert record_id, "Record ID should not be empty"

    # read the record using the connector
    read_record = connector.read_one(record_id)

    # assert that the record was read successfully
    assert read_record
    assert read_record.source.type == 'airtable'
    assert read_record.Name == fields['Name']
    assert read_record.Notes == fields['Notes']

def test_read_many_records(connector: BaseConnector):
    """Test reading multiple records from Airtable.

    Filter is a simple match on the 'Name' field.
    Args:
        connector (BaseConnector): Test fixture for the Airtable connector.
    """
    # read all records using the connector
    records = connector.read_many(
        filter={
            'Name': 'Test Name'
        }
    )

    # assert that the records were read successfully
    assert isinstance(records, list), "Records should be a list"
    assert len(records) >= 1, "Should have at least one record"
    assert all(record.source.type == 'airtable' for record in records)

def test_read_many_records_match_on_two_fields(connector: BaseConnector):
    """Test reading multiple records from Airtable.

    Filter is a compound match on the 'Name' and 'Notes' fields.

    Args:
        connector (BaseConnector): Test fixture for the Airtable connector.
    """
    # read all records using the connector
    records = connector.read_many(
        filter={
            'Name': 'Test Name',
            'Notes': 'Test Notes'
        }
    )

    # assert that the records were read successfully
    assert isinstance(records, list), "Records should be a list"
    assert len(records) >= 1, "Should have at least one record"
    assert all(record.source.type == 'airtable' for record in records)

def test_read_many_records_no_filter(connector: BaseConnector):
    """Test reading multiple records from Airtable without a filter.

    Args:
        connector (BaseConnector): Test fixture for the Airtable connector.
    """
    # read all records using the connector
    records = connector.read_many()

    # assert that the records were read successfully
    assert isinstance(records, list), "Records should be a list"
    assert len(records) >= 1, "Should have at least one record"
    assert all(record.source.type == 'airtable' for record in records)

def test_read_record_not_found(connector: BaseConnector):
    """Test reading a record that does not exist in Airtable.

    Args:
        connector (BaseConnector): Test fixture for the Airtable connector.
    """
    # attempt to read a non-existent record
    read_record = connector.read_one('non_existent_record_id')

    # assert that the record was not found
    assert read_record is None, "Record should not be found"

def test_read_many_records_not_found(connector: BaseConnector):
    """Test reading multiple records with a filter that matches no records.

    Args:
        connector (BaseConnector): Test fixture for the Airtable connector.
    """
    # read records using a filter that matches no records
    records = connector.read_many(
        filter={
            'Name': 'Non Existent Name'
        }
    )

    # assert that no records were found
    assert isinstance(records, list), "Records should be a list"
    assert len(records) == 0, "Should have no records"