"""A connector for Airtable using the pyairtable library.
"""

import os
from typing import Any

from pyairtable import Api
from pyairtable.formulas import match
from pyairtable.api.types import RecordDict

from aracnid_core.base import BaseConnector


class AirtableConnector(BaseConnector):
    """A connector for Airtable using the pyairtable library.
    """
    @property
    def capabilities(self) -> dict[str, bool]:
        """Returns a mapping of capabilities.

        Returns:
            dict[str, bool]: Mapping of capabilities.
        """
        return {
            "supports_filters": True,
            "supports_partial_update": True,
            "supports_replace_one": True,
            "supports_soft_delete": False,
            "supports_hard_delete": True,
            "supports_transactions": False,
        }


    def __init__(self, base_id: str, table_name: str):
        """Initialize the AirtableConnector.

        Args:
            base_id (str): The ID of the Airtable base.
            table_name (str): The name of the Airtable table.

        Raises:
            ValueError: If base_id or table_name is not a non-empty string, or if AIRTABLE_API_KEY is not set.
        """
        if not isinstance(base_id, str) or not base_id.strip():
            raise ValueError("base_id must be a non-empty string")
        if not isinstance(table_name, str) or not table_name.strip():
            raise ValueError("table_name must be a non-empty string")

        api_key = os.getenv("AIRTABLE_API_KEY")
        if not api_key or not api_key.strip():
            raise ValueError("AIRTABLE_API_KEY environment variable is required.")

        self.air_api_key = api_key.strip()
        self.base_id = base_id.strip()
        self.table_name = table_name.strip()

        self.api = Api(self.air_api_key)
        self.table = self.api.table(self.base_id, self.table_name)


    def _normalize_record(self, rec: RecordDict) -> dict[str, Any]:
        """Normalize an Airtable record into a dictionary with standard keys.

        Args:
            rec (RecordDict): The Airtable record to normalize.

        Returns:
            dict[str, Any]: The normalized record.
        """
        fields = rec.get("fields") or {}
        return {
            "id": rec.get("id"),
            **fields,
            "_created_time": rec.get("createdTime"),
        }


    def _as_runtime_error(self, exc: Exception, op: str) -> RuntimeError:
        """Convert an exception into a RuntimeError with a standardized message.

        Args:
            exc (Exception): The original exception.
            op (str): The operation being performed.

        Returns:
            RuntimeError: The converted runtime error.
        """
        return RuntimeError(f"{op} failed: {exc}")


    def _is_not_found_error(self, exc: Exception) -> bool:
        """Determine if an exception indicates a "not found" error.

        Args:
            exc (Exception): The exception to check.

        Returns:
            bool: True if the exception indicates a "not found" error, False otherwise.
        """
        msg = str(exc).lower()
        return "404" in msg or "not found" in msg


    def create_one(self, record: dict[str, Any]) -> dict[str, Any]:
        """Create a new record in the Airtable table.

        Args:
            record (dict[str, Any]): The record to create.
            
        Returns:
            dict[str, Any]: The created record.

        Raises:
            ValueError: If record is not a dict or is empty.
        """
        if not isinstance(record, dict):
            raise ValueError("record must be a dict")
        if not record:
            raise ValueError("record must not be empty")

        fields = dict(record)  # do not mutate caller input
        try:
            created = self.table.create(fields)
        except Exception as exc:
            raise self._as_runtime_error(exc, "create_one") from exc

        return self._normalize_record(created)


    def read_one(self, record_id: str) -> dict[str, Any] | None:
        """Read a single record from the Airtable table by its ID.

        Args:
            record_id (str): The ID of the record to read.

        Returns:
            dict[str, Any] | None: The record if found, None otherwise.

        Raises:
            ValueError: If record_id is not a non-empty string.
        """
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("record_id must be a non-empty string")

        try:
            rec = self.table.get(record_id.strip())
        except Exception as exc:
            if self._is_not_found_error(exc):
                return None
            raise self._as_runtime_error(exc, "read_one") from exc

        return self._normalize_record(rec) if rec else None


    def read_many(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Read multiple records from the Airtable table, optionally filtered by a dictionary of field values.

        Args:
            filters (dict[str, Any] | None): A dictionary of field values to filter records.

        Returns:
            list[dict[str, Any]]: A list of records matching the filters.

        Raises:
            ValueError: If filters is not a dict or None.
        """
        if filters is not None and not isinstance(filters, dict):
            raise ValueError("filters must be a dict or None")

        filter_obj: dict[str, Any] = dict(filters) if filters else {}

        try:
            recs = self.table.all(formula=match(filter_obj)) if filter_obj else self.table.all()
        except Exception as exc:
            raise self._as_runtime_error(exc, "read_many") from exc

        return [self._normalize_record(rec) for rec in recs]


    def update_one(self, record_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        """Update a single record in the Airtable table by its ID.
        
        Args:
            record_id (str): The ID of the record to update.
            changes (dict[str, Any]): A dictionary of field changes to apply.

        Returns:
            dict[str, Any]: The updated record.

        Raises:
            ValueError: If record_id is not a non-empty string or changes is not a non-empty dict.
        """
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("record_id must be a non-empty string")
        if not isinstance(changes, dict):
            raise ValueError("changes must be a dict")
        if not changes:
            raise ValueError("changes must not be empty")

        rid = record_id.strip()
        fields = dict(changes)  # do not mutate caller input

        try:
            updated = self.table.update(rid, fields)
        except Exception as exc:
            if self._is_not_found_error(exc):
                raise RuntimeError(f"update_one failed: record '{rid}' not found") from exc
            raise self._as_runtime_error(exc, "update_one") from exc

        if not updated:
            raise RuntimeError(f"update_one failed: record '{rid}' not found")

        return self._normalize_record(updated)


    def replace_one(self, record_id: str, new_record: dict[str, Any]) -> dict[str, Any]:
        """Replace a single record in the Airtable table by its ID.

        Args:
            record_id (str): The ID of the record to replace.
            new_record (dict[str, Any]): A dictionary representing the new record.

        Returns:
            dict[str, Any]: The replaced record.

        Raises:
            ValueError: If record_id is not a non-empty string or new_record is not a non-empty dict.
        """
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("record_id must be a non-empty string")
        if not isinstance(new_record, dict):
            raise ValueError("new_record must be a dict")
        if not new_record:
            raise ValueError("new_record must not be empty")

        rid = record_id.strip()
        fields = dict(new_record)  # do not mutate caller input

        try:
            replaced = self.table.update(rid, fields, replace=True)
        except Exception as exc:
            if self._is_not_found_error(exc):
                raise RuntimeError(f"replace_one failed: record '{rid}' not found") from exc
            raise self._as_runtime_error(exc, "replace_one") from exc

        if not replaced:
            raise RuntimeError(f"replace_one failed: record '{rid}' not found")

        return self._normalize_record(replaced)


    def delete_one(self, record_id: str, hard: bool = False) -> bool:
        """Delete a single record from the Airtable table by its ID.

        Args:
            record_id (str): The ID of the record to delete.
            hard (bool): Whether to perform a hard delete. Defaults to False.

        Returns:
            bool: True if the record was deleted, False if it was not found.

        Raises:
            ValueError: If record_id is not a non-empty string or hard is not a bool.
            RuntimeError: If soft delete is requested (not supported).
        """
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("record_id must be a non-empty string")
        if not isinstance(hard, bool):
            raise ValueError("hard must be a bool")

        # Airtable connector supports hard delete only.
        if not hard:
            raise RuntimeError("delete_one failed: soft delete is not supported; pass hard=True")

        rid = record_id.strip()
        try:
            result = self.table.delete(rid)
        except Exception as exc:
            if self._is_not_found_error(exc):
                return False
            raise self._as_runtime_error(exc, "delete_one") from exc

        return bool((result or {}).get("deleted", False))
    