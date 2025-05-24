"""Airtable schema for Aracnid Framework.
"""
# pyright: reportIncompatibleVariableOverride=false
from typing import Literal, Optional

from aracnid_core.schema.base_model import RecordBase, SourceBase
from pydantic import create_model, Field


class AirtableSource(SourceBase):
    type: str = Field(default='airtable')


class AirtableRecordBase(RecordBase):
    """Base class for Airtable records.

    This class overrides the `RecordBase` class to include Airtable-specific
    fields and metadata. Pyright reports an incompatible variable override error
    because the `metadata` field is defined as a `MetadataBase` in the base class,
    but it is defined as an `AirtableMetadata` in this class. This is a known
    limitation of Pyright and does not affect the functionality of the code.
    """
    source: AirtableSource = AirtableSource()


def create_model_from_dict(fields: dict) -> type:
    """Dynamically create a Pydantic model for a specific Airtable table.

    Args:
        fields (dict): A dictionary where keys are field names and values are tuples
            containing the type and default value (or None for optional fields).

    Returns:
        type: A Pydantic model class with the specified fields.
    """
    return create_model(
        'DynamicAirtableRecord',
        __base__=AirtableRecordBase,
        **{k: v for k, v in fields.items()}
    )
