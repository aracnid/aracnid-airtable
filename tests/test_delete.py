"""Test delete functionality for the i-airtable package.
"""
from aracnid_core.base import BaseConnector


def test_delete_record_hard(connector: BaseConnector):
    """Test deleting a record in Airtable.

    Args:
        connector (BaseConnector): Test fixture for the Airtable connector.
    """
    # create a new record to be deleted
    fields = {
        'Name': 'Test Name',
        'Notes': 'Test Notes',
    }
    created_record = connector.create(fields)
    record_id = created_record.id
    assert record_id, "Record ID should not be empty"

    # delete the record using the connector
    delete_success = connector.delete_one(record_id, hard=True)

    # assert that the record was deleted successfully
    assert delete_success, "delete_one() failed"


def test_delete_record_soft_supported(connector_soft: BaseConnector):
    """Test soft deletion of a record in Airtable.

    Args:
        connector_soft (BaseConnector): Test fixture for the Airtable connector,
            where soft delete is supported.
    """
    # create a new record to be deleted
    fields = {
        'Name': 'Test Name',
        'Notes': 'Test Notes',
    }
    created_record = connector_soft.create(fields)
    record_id = created_record.id
    assert record_id, "Record ID should not be empty"

    # delete the record using the connector_soft
    delete_success = connector_soft.delete_one(record_id, hard=False)

    # assert that the record was deleted successfully
    assert delete_success, "Soft deletion is not supported"


def test_delete_record_soft_unsupported(connector: BaseConnector):
    """Test soft deletion of a record in Airtable.

    Args:
        connector (BaseConnector): Test fixture for the Airtable connector,
            where soft delete is not supported.
    """
    # create a new record to be deleted
    fields = {
        'Name': 'Test Name',
        'Notes': 'Test Notes',
    }
    created_record = connector.create(fields)
    record_id = created_record.id
    assert record_id, "Record ID should not be empty"

    # delete the record using the connector
    delete_success = connector.delete_one(record_id, hard=False)

    # assert that the record was deleted successfully
    assert not delete_success, "Soft deletion is not supported"


def test_delete_many_records_hard(connector: BaseConnector):
    """Test deleting multiple records from Airtable.

    Filter is a simple match on the 'Name' field.

    Args:
        connector (BaseConnector): Test fixture for the Airtable connector.
    """
    # create a new record to be deleted
    fields = {
        'Name': 'Test Name',
        'Notes': 'Test Notes',
    }
    created_record = connector.create(fields)
    record_id = created_record.id
    assert record_id, "Record ID should not be empty"

    # delete filtered records using the connector
    deleted_count = connector.delete_many(
        filter={'Name': 'Test Name'},
        hard=True
    )

    # assert that the records were deleted successfully
    assert isinstance(deleted_count, int), "Records should be a list"
    assert deleted_count >= 1, "Should have at least one record"


def test_delete_many_records_soft_supported(connector_soft: BaseConnector):
    """Test deleting multiple records from Airtable.

    Filter is a simple match on the 'Name' field.

    Args:
        connector_soft (BaseConnector): Test fixture for the Airtable connector_soft.
    """
    # create a new record to be deleted
    fields = {
        'Name': 'Test Name',
        'Notes': 'Test Notes',
    }
    created_record = connector_soft.create(fields)
    record_id = created_record.id
    assert record_id, "Record ID should not be empty"

    # delete filtered records using the connector_soft
    deleted_count = connector_soft.delete_many(
        filter={'Name': 'Test Name'},
        hard=False
    )

    # assert that the records were deleted successfully
    assert isinstance(deleted_count, int), "Records should be a list"
    assert deleted_count >= 1, "Should have at least one record"


def test_delete_many_records_soft_unsupported(connector: BaseConnector):
    """Test deleting multiple records from Airtable.

    Filter is a simple match on the 'Name' field.

    Args:
        connector (BaseConnector): Test fixture for the Airtable connector.
    """
    # create a new record to be deleted
    fields = {
        'Name': 'Test Name',
        'Notes': 'Test Notes',
    }
    created_record = connector.create(fields)
    record_id = created_record.id
    assert record_id, "Record ID should not be empty"

    # delete filtered records using the connector
    deleted_count = connector.delete_many(
        filter={'Name': 'Test Name'},
        hard=False
    )

    # assert that the records were deleted successfully
    assert isinstance(deleted_count, int), "Records should be a list"
    assert deleted_count == 0, "Should have at least one record"

