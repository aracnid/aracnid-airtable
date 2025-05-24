"""Airtable connector for Aracnid integration framework.
"""
import os
from typing import Any, Dict, List, Optional

from aracnid_core.base_connector import BaseConnector
from pyairtable import Api

from schema.model import AirtableRecordBase, create_model_from_dict
from schema.transform import from_airtable


class AirtableConnector(BaseConnector):
    """Airtable connector for Aracnid integration framework.
    """
    def __init__(self, base_id: str, table_name: str, schema: Optional[Dict] = None):
        """Initialize the Airtable connector.
        Args:
            base_id (str): The Airtable base ID.
            table_name (str): The Airtable table name.
            schema (Optional[Dict]): The schema for the Airtable table.
                If not provided, the schema will be self-discovered.
        Raises:
            ValueError: If the base ID or table name is not found.

        Environment Variables:
            AIRTABLE_API_KEY: The Airtable API key.
        """
        # read environment variables
        self.air_api_key = os.environ.get('AIRTABLE_API_KEY')
        if not self.air_api_key:
            raise ValueError('AIRTABLE_API_KEY environment variable is required.')

        # initialize api
        self.api = Api(self.air_api_key)

        # set the base
        self.base_id = base_id
        bases = self.api.bases()
        self.base = None
        for base in bases:
            if base.id == self.base_id:
                self.base = base
                break
        if not self.base:
            raise ValueError(f'Base with ID {self.base_id} not found.')

        # set the table
        self.table_name = table_name
        self.table = self.api.table(self.base_id, table_name)
        if not self.table:
            raise ValueError(
                f'Table with name {self.table_name} not found in base {self.base_id}.'
            )
        
        # set the schema
        self.schema = schema or self._discover_schema()
        self.model = create_model_from_dict(self.schema)


    def _discover_schema(self) -> Dict:
        # Future enhancement: introspect fields from Airtable
        raise NotImplementedError('Schema must be provided for now.')
    

    def create(self, fields: Dict) -> AirtableRecordBase:
        """Create a record with the given fields in the Airtable table.

        Args:
            fields (Dict): The fields to create in the record.

        Returns:
            AirtableRecordBase: The created record.
        """
        # validate fields against the model
        validated_record = self.model(**fields)

        # convert the validated record to a dictionary excluding certain fields
        validated_dict = validated_record.model_dump(
            exclude={'id', 'metadata', 'source'}
        )

        # create the record in Airtable
        created_dict = self.table.create(validated_dict)

        # convert the created Airtable record to the standard model
        created_record = from_airtable(self.model, created_dict)

        # return the created record
        return created_record


    def read_one(self, record_id: str) -> Optional[Dict]:
        pass


    def read_many(self, filters: Optional[Dict] = None) -> List[Dict]:
        return []


    def update(self, record_id: str, changes: Dict) -> Dict:
        return {}


    def replace(self, record_id: str, new_record: Dict) -> Dict:
        return {}


    def delete_one(self, record_id: str, hard: bool = False) -> bool:
        return False


    def delete_many(self, filters: Optional[Dict] = None, hard: bool = False) -> int:
        return 0


    def get_source_name(self) -> str:
        if not self.base:
            raise ValueError(f'Base with ID {self.base_id} not found.')

        return f'airtable.{self.base.name}.{self.table_name}'
