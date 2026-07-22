"""A connector for Airtable using the pyairtable library.
"""

from datetime import date, datetime, timezone
import os
from typing import Any


from pyairtable import Api
from pyairtable.api.types import RecordDict
from pyairtable.formulas import AND, OR, NOT
from pyairtable.formulas import BLANK, TRUE, FALSE
from pyairtable.formulas import DATETIME_PARSE
from pyairtable.formulas import EQ, NE, GT, GTE, LT, LTE
from pyairtable.formulas import FIND, LEFT, LEN
from pyairtable.formulas import Field, Formula
from aracnid_core.base import BaseConnector
from aracnid_core.query_dsl import QueryDict, SortSpec


class AirtableConnector(BaseConnector):
    """A connector for Airtable using the pyairtable library.
    """
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
        self.base = self.api.base(self.base_id)
        self.table = self.base.table(self.table_name)

        # lazy-loaded cache: field name -> field type
        self._field_types: dict[str, str] | None = None


    @property
    def capabilities(self) -> dict[str, bool]:
        """Returns a mapping of capabilities.

        Returns:
            dict[str, bool]: Mapping of capabilities.
        """
        return {
            "supports_query": True,
            "supports_partial_update": True,
            "supports_replace_one": True,
            "supports_soft_delete": False,
            "supports_hard_delete": True,
            "supports_transactions": False,
        }


    def _load_field_types(self) -> dict[str, str]:
        """Load Airtable field types for this table (best effort).

        Returns empty mapping if metadata lookup is unavailable.

        Returns:
            dict[str, str]: Mapping of field names to field types.
        """
        if self._field_types is not None:
            return self._field_types

        mapping: dict[str, str] = {}
        try:
            # pyairtable typically exposes schema helpers either on Api/Base.
            # Adapt this block to your exact pyairtable version if needed.
            # Pattern:
            #   base = self.api.base(self.base_id)
            #   table_schema = base.table(self.table_name).schema()   OR base.schema()
            # then find the target table's fields.
            base_schema = self.base.schema()

            target = None
            for tbl in getattr(base_schema, "tables", []) or []:
                if getattr(tbl, "name", None) == self.table_name:
                    target = tbl
                    break

            if target is not None:
                for f in getattr(target, "fields", []) or []:
                    fname = getattr(f, "name", None)
                    ftype = getattr(f, "type", None)
                    if fname and ftype:
                        mapping[str(fname)] = str(ftype)

        except Exception:
            # Non-fatal: no metadata scope/permission/version mismatch/etc.
            mapping = {}

        self._field_types = mapping
        return mapping


    @staticmethod
    def _coerce_by_airtable_type(field_type: str, value: Any) -> Any:
        """Coerce value using Airtable-declared field type.
        
        Args:
            field_type (str): The Airtable field type.
            value (Any): The value to coerce.

        Returns:
            Any: The coerced value, or the original value if no coercion is applicable.
        """
        if not isinstance(value, str):
            return value

        if field_type == "date":
            try:
                return date.fromisoformat(value)
            except ValueError:
                return value

        if field_type == "dateTime":
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return value

        return value


    def _normalize_record(self, rec: RecordDict | dict[str, Any]) -> dict[str, Any]:
        """Normalize an Airtable record into a dictionary with standard keys.

        Args:
            rec (RecordDict | dict[str, Any]): The Airtable record to normalize.

        Returns:
            dict[str, Any]: The normalized record.
        """
        fields = rec.get("fields") or {}
        out: dict[str, Any] = {'id': rec['id'], '_created_time': rec.get('createdTime')}

        field_types = self._load_field_types()

        for k, v in fields.items():
            field_type = field_types.get(k)
            if field_type:
                out[k] = self._coerce_by_airtable_type(field_type, v)
            else:
                out[k] = v

        return out


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


    def _normalize_field_value_for_write(self, value: Any) -> Any:
        """Normalize a field value for writing to Airtable.

        Args:
            value (Any): The field value to normalize.

        Returns:
            Any: The normalized field value.
        """
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("datetime field values must be timezone-aware (tzinfo required)")
            return (
                value.astimezone(timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
            )
        if isinstance(value, date): 
            return value.isoformat()
        return value


    def create_one(self, record: dict[str, Any]) -> dict[str, Any]:
        """Create a new record in the Airtable table.

        Args:
            record (dict[str, Any]): The record to create.

        Returns:
            dict[str, Any]: The created record.

        Raises:
            ValueError: If record is not a dict/empty, or contains naive datetime values.
        """
        if not isinstance(record, dict):
            raise ValueError("record must be a dict")
        if not record:
            raise ValueError("record must not be empty")

        # Do not mutate caller input.
        fields = {
            key: self._normalize_field_value_for_write(value)
            for key, value in record.items()
        }

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

        # Do not mutate caller input.
        fields = {
            key: self._normalize_field_value_for_write(value)
            for key, value in changes.items()
        }

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

        # Do not mutate caller input.
        fields = {
            key: self._normalize_field_value_for_write(value)
            for key, value in new_record.items()
        }

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
    

    def _read_many_normalized(self, query_dsl: QueryDict, sort_dsl: SortSpec) -> list[dict[str, Any]]:
        """Execute a normalized Query DSL object against Airtable.
        
        Args:
            query_dsl (QueryDict): The normalized Query DSL object.
            sort_dsl (SortSpec): The normalized Sort specification.

        Returns:
            list[dict[str, Any]]: A list of normalized records matching the query.
        """
        formula = self._query_to_formula(query_dsl) if query_dsl else None
        airtable_sort = self._sort_to_airtable_sort(sort_dsl)

        try:
            recs = self.table.all(formula=formula, sort=airtable_sort)
        except Exception as exc:
            raise self._as_runtime_error(exc, "read_many") from exc

        return [self._normalize_record(rec) for rec in recs]


    def _query_to_formula(self, node: QueryDict) -> Formula:
        """Convert a normalized Query DSL node into an Airtable formula.

        Args:
            node (QueryDict): The normalized Query DSL node.

        Returns:
            Formula: The corresponding Airtable formula.
        """
        # logical
        if "$and" in node:
            return AND(*(self._query_to_formula(child) for child in node["$and"]))
        if "$or" in node:
            return OR(*(self._query_to_formula(child) for child in node["$or"]))
        if "$not" in node:
            return NOT(self._query_to_formula(node["$not"]))

        # field-node (normalized form should generally be single-field, but support multi)
        formulas: list[Formula] = []
        for field, condition in node.items():
            formulas.append(self._field_condition_to_formula(field, condition))

        if len(formulas) == 1:
            return formulas[0]
        return AND(*formulas)


    def _field_condition_to_formula(self, field: str, condition: dict[str, Any]) -> Any:
        """Convert a field condition into an Airtable formula.

        Args:
            field (str): The field name.
            condition (dict[str, Any]): The field condition.

        Returns:
            Any: The corresponding Airtable formula.
        """
        # condition is normalized op-object
        parts: list[Any] = []
        for op, value in condition.items():
            if op == "$eq":
                parts.append(EQ(Field(field), self._literal(value)))
            elif op == "$ne":
                parts.append(NE(Field(field), self._literal(value)))
            elif op == "$gt":
                parts.append(GT(Field(field), self._literal(value)))
            elif op == "$gte":
                parts.append(GTE(Field(field), self._literal(value)))
            elif op == "$lt":
                parts.append(LT(Field(field), self._literal(value)))
            elif op == "$lte":
                parts.append(LTE(Field(field), self._literal(value)))
            elif op == "$in":
                parts.append(OR(*(EQ(Field(field), self._literal(v)) for v in value)))
            elif op == "$nin":
                parts.append(AND(*(NE(Field(field), self._literal(v)) for v in value)))
            elif op == "$exists":
                parts.append(NOT(EQ(Field(field), BLANK())) if value else EQ(Field(field), BLANK()))
            elif op == "$contains":
                parts.append(GT(FIND(self._literal(value), Field(field)), 0))
            elif op == "$startsWith":
                parts.append(EQ(LEFT(Field(field), LEN(self._literal(value))), self._literal(value)))
            else:
                raise RuntimeError(f"read_many failed: unsupported operator '{op}'")

        if len(parts) == 1:
            return parts[0]
        return AND(*parts)


    def _literal(self, value: Any) -> str | int | float | Formula:
        """Convert a value into an Airtable formula literal.

        Args:
            value (Any): The value to convert.

        Returns:
            str | int | float | Formula: The corresponding Airtable formula literal.
        """
        if isinstance(value, bool):
            return TRUE() if value else FALSE()
        if value is None:
            return BLANK()
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, datetime):
            dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
            iso = dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            return DATETIME_PARSE(iso)
        if isinstance(value, date):
            # date-only; Airtable date fields compare cleanly with ISO date strings
            return DATETIME_PARSE(value.isoformat())

        return value


    def _sort_to_airtable_sort(self, sort_dsl: SortSpec) -> list[str]:
        """Translate normalized SortSpec into Airtable sort payload.

        pyairtable format:
        - ascending: "FieldName"
        - descending: "-FieldName"
        
        Args:
            sort_dsl (SortSpec): The normalized Sort specification.

        Returns:
            list[str]: The Airtable sort payload.
        """
        if not sort_dsl:
            return []

        out: list[str] = []
        for entry in sort_dsl:
            field, direction = next(iter(entry.items()))
            out.append(field if direction == 1 else f'-{field}')

        return out
