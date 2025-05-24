"""Convert Airtable formatted records into the standard model.
"""
from datetime import datetime
from pytz import timezone
from typing import Optional, Dict, Any

from aracnid_core.schema.base_model import MetadataBase
from pyairtable.api.types import RecordDict

from schema.model import AirtableRecordBase, AirtableSource

# set the local timezone
EST = timezone('America/New_York')

def from_airtable(model: type[AirtableRecordBase], obj: RecordDict) -> AirtableRecordBase:
    """Convert an Airtable record to the standard model.

    Args:
        airtable_obj (dict): The Airtable record to convert.

    Returns:
        AirtableRecordBase: The converted record.
    """
    # get the fields from the Airtable object
    fields = obj.get('fields', {})

    # get created time
    created_at_str = obj.get('createdTime')
    created_at = None
    if created_at_str:
        try:
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00')).astimezone(EST)
        except ValueError:
            created_at = None

    # create the source object
    airtable_source = AirtableSource(
        id=obj.get('id'),
        created_at=created_at,
        modified_at=fields.get('Updated')
    )

    # create the metadata object
    metadata = MetadataBase(
        is_deleted=False,
        synced_at=datetime.now()
    )

    # create the AirtableRecordBase object
    return model(
        id=obj.get('id'),
        source=airtable_source,
        metadata=metadata,
        **{k: v for k, v in fields.items()}

    )


