from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

from pyairtable.formulas import to_formula_str
import pytest

from aracnid_airtable.connector import AirtableConnector


@pytest.fixture
def connector_and_table() -> tuple[AirtableConnector, MagicMock]:
    with patch("aracnid_airtable.connector.os.getenv", return_value="key_test"), patch(
        "aracnid_airtable.connector.Api"
    ) as mock_api_cls:
        mock_api = MagicMock()
        mock_table = MagicMock()
        mock_api.table.return_value = mock_table
        mock_api_cls.return_value = mock_api

        c = AirtableConnector(base_id="app123", table_name="tbl123")
        # ensure table is the mock we control directly in tests
        c.table = mock_table
        return c, mock_table


def test_normalize_record_flattens_fields(connector_and_table: tuple[AirtableConnector, MagicMock]) -> None:
    connector, _ = connector_and_table
    rec: dict[str, Any] = {
        "id": "rec_1",
        "fields": {"name": "alpha", "status": "active"},
        "createdTime": "2026-07-15T00:00:00.000Z",
    }

    result = connector._normalize_record(rec)

    assert result == {
        "id": "rec_1",
        "name": "alpha",
        "status": "active",
        "_created_time": "2026-07-15T00:00:00.000Z",
    }


def test_create_one_sends_fields_only(connector_and_table: tuple[AirtableConnector, MagicMock]) -> None:
    connector, table = connector_and_table
    table.create.return_value = {
        "id": "rec_1",
        "fields": {"name": "alpha"},
        "createdTime": "2026-07-15T00:00:00.000Z",
    }

    record = {"name": "alpha"}
    out = connector.create_one(record)

    table.create.assert_called_once_with({"name": "alpha"})
    assert record == {"name": "alpha"}  # input not mutated
    assert out["id"] == "rec_1"
    assert out["name"] == "alpha"


def test_read_one_not_found_returns_none(connector_and_table: tuple[AirtableConnector, MagicMock]) -> None:
    connector, table = connector_and_table
    table.get.side_effect = Exception("404 Client Error: Not Found")

    out = connector.read_one("rec_missing")

    assert out is None


def test_read_many_with_query_builds_formula(connector_and_table: tuple[AirtableConnector, MagicMock]) -> None:
    connector, table = connector_and_table
    table.all.return_value = [
        {"id": "rec_1", "fields": {"status": "active"}, "createdTime": "t1"}
    ]

    query = {"status": "active"}  # shorthand DSL; normalized upstream
    out = connector.read_many(query)

    assert table.all.call_count == 1
    _, kwargs = table.all.call_args
    assert "formula" in kwargs
    assert kwargs["formula"] is not None  # don't compare to match(...) anymore
    assert str(kwargs["formula"])
    assert out[0]["status"] == "active"
    assert query == {"status": "active"}  # input not mutated


def test_update_one_not_found_raises_runtimeerror(connector_and_table: tuple[AirtableConnector, MagicMock]) -> None:
    connector, table = connector_and_table
    table.update.side_effect = Exception("404 Client Error: Not Found")

    with pytest.raises(RuntimeError, match="not found"):
        connector.update_one("missing-id", {"status": "active"})


def test_replace_one_not_found_raises_runtimeerror(connector_and_table: tuple[AirtableConnector, MagicMock]) -> None:
    connector, table = connector_and_table
    table.update.side_effect = Exception("404 Client Error: Not Found")

    with pytest.raises(RuntimeError, match="not found"):
        connector.replace_one("missing-id", {"name": "beta"})


def test_delete_one_hard_false_raises_runtimeerror(connector_and_table: tuple[AirtableConnector, MagicMock]) -> None:
    connector, table = connector_and_table
    with pytest.raises(RuntimeError, match="soft delete is not supported"):
        connector.delete_one("rec_1", hard=False)


def test_delete_one_not_found_returns_false(connector_and_table: tuple[AirtableConnector, MagicMock]) -> None:
    connector, table = connector_and_table
    table.delete.side_effect = Exception("404 Client Error: Not Found")

    out = connector.delete_one("missing-id", hard=True)

    assert out is False


@pytest.mark.parametrize(
    ("method_name", "args"),
    [
        ("create_one", ({"name": "x"},)),
        ("read_many", ({"x": 1},)),
        ("update_one", ("rec_1", {"status": "active"})),
        ("replace_one", ("rec_1", {"name": "y"})),
        ("delete_one", ("rec_1", True)),
    ],
)
def test_backend_exceptions_wrapped_as_runtimeerror(
    connector_and_table: tuple[AirtableConnector, MagicMock], method_name: str, args: tuple[Any, ...]
) -> None:
    connector, table = connector_and_table
    if method_name == "create_one":
        table.create.side_effect = Exception("boom")
    elif method_name == "read_many":
        table.all.side_effect = Exception("boom")
    elif method_name == "update_one":
        table.update.side_effect = Exception("boom")
    elif method_name == "replace_one":
        table.update.side_effect = Exception("boom")
    elif method_name == "delete_one":
        table.delete.side_effect = Exception("boom")

    method = getattr(connector, method_name)

    with pytest.raises(RuntimeError, match=rf"^{method_name} failed:"):
        method(*args)

    
@pytest.mark.parametrize(
    ("query", "expected_parts"),
    [
        ({"name": {"$eq": "alpha"}}, ["{name}", "alpha"]),
        ({"name": {"$ne": "alpha"}}, ["{name}", "!="]),
        ({"age": {"$gt": 18}}, ["{age}", ">", "18"]),
        ({"age": {"$gte": 18}}, ["{age}", ">=", "18"]),
        ({"age": {"$lt": 65}}, ["{age}", "<", "65"]),
        ({"age": {"$lte": 65}}, ["{age}", "<=", "65"]),
        ({"$and": [{"name": {"$eq": "a"}}, {"age": {"$gt": 1}}]}, ["AND"]),
        ({"$or": [{"name": {"$eq": "a"}}, {"name": {"$eq": "b"}}]}, ["OR"]),
        ({"$not": {"name": {"$eq": "a"}}}, ["NOT"]),
        ({"name": {"$in": ["a", "b"]}}, ["OR"]),
        ({"name": {"$nin": ["a", "b"]}}, ["AND"]),
        ({"name": {"$exists": True}}, ["NOT({name}=BLANK())"]),
        ({"name": {"$exists": False}}, ["{name}=BLANK()"]),
        ({"name": {"$contains": "ph"}}, ["FIND"]),
        ({"name": {"$startsWith": "al"}}, ["LEFT", "LEN"]),
    ],
)
def test_query_to_formula_matrix(
    connector_and_table: tuple[AirtableConnector, MagicMock],
    query: dict[str, Any],
    expected_parts: list[str],
) -> None:
    connector, _ = connector_and_table

    formula = connector._query_to_formula(query)  # unit test converter directly
    rendered = to_formula_str(formula)

    for part in expected_parts:
        assert part in rendered


def test_query_to_formula_unsupported_operator_raises(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, _ = connector_and_table

    with pytest.raises(RuntimeError, match="unsupported operator"):
        connector._query_to_formula({"name": {"$wat": 1}})


def test_sort_to_airtable_sort_none_or_empty_returns_none(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, _ = connector_and_table
    assert connector._sort_to_airtable_sort([]) == []


def test_sort_to_airtable_sort_single_and_multi_preserves_order(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, _ = connector_and_table

    out = connector._sort_to_airtable_sort(
        [{"DueDate": 1}, {"Priority": -1}, {"Name": 1}]
    )

    assert out == ["DueDate", "-Priority", "Name"]


def test_read_many_with_query_and_sort_passes_formula_and_sort(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, table = connector_and_table
    table.all.return_value = [
        {"id": "rec_1", "fields": {"status": "active"}, "createdTime": "t1"}
    ]

    out = connector.read_many(
        {"status": "active"},
        sort=[{"DueDate": 1}, {"Priority": -1}],
    )

    assert table.all.call_count == 1
    _, kwargs = table.all.call_args
    assert kwargs["formula"] is not None
    assert kwargs["sort"] == ["DueDate", "-Priority"]
    assert out[0]["status"] == "active"


def test_read_many_with_sort_only_passes_sort_without_formula(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, table = connector_and_table
    table.all.return_value = []

    connector.read_many(sort=[{"CreatedAt": -1}])

    _, kwargs = table.all.call_args
    assert kwargs["formula"] is None
    assert kwargs["sort"] == ["-CreatedAt"]


@pytest.mark.parametrize(
    ("field_type", "raw", "expected_type", "expected_value"),
    [
        ("date", "2026-07-22", date, date(2026, 7, 22)),
        (
            "dateTime",
            "2026-07-22T12:34:56.000Z",
            datetime,
            datetime(2026, 7, 22, 12, 34, 56, tzinfo=timezone.utc),
        ),
        ("singleLineText", "2026-07-22", str, "2026-07-22"),  # untouched for non-date types
    ],
)
def test_coerce_by_airtable_type_happy_path(
    connector_and_table: tuple[AirtableConnector, MagicMock],
    field_type: str,
    raw: str,
    expected_type: type,
    expected_value: Any,
) -> None:
    connector, _ = connector_and_table

    out = connector._coerce_by_airtable_type(field_type, raw)

    assert isinstance(out, expected_type)
    assert out == expected_value


@pytest.mark.parametrize(
    ("field_type", "raw"),
    [
        ("date", "not-a-date"),
        ("dateTime", "not-a-datetime"),
        ("dateTime", "2026-13-99T99:99:99Z"),
    ],
)
def test_coerce_by_airtable_type_invalid_strings_passthrough(
    connector_and_table: tuple[AirtableConnector, MagicMock],
    field_type: str,
    raw: str,
) -> None:
    connector, _ = connector_and_table

    out = connector._coerce_by_airtable_type(field_type, raw)

    assert out == raw


@pytest.mark.parametrize(
    ("field_type", "raw"),
    [
        ("date", 123),
        ("dateTime", True),
        ("date", None),
        ("dateTime", {"x": 1}),
    ],
)
def test_coerce_by_airtable_type_non_string_passthrough(
    connector_and_table: tuple[AirtableConnector, MagicMock],
    field_type: str,
    raw: Any,
) -> None:
    connector, _ = connector_and_table

    out = connector._coerce_by_airtable_type(field_type, raw)

    assert out is raw


def test_normalize_record_applies_schema_typed_coercion(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, _ = connector_and_table

    # bypass metadata call and provide deterministic schema map
    connector._field_types = {
        "DueDate": "date",
        "EventAt": "dateTime",
        "Name": "singleLineText",
    }

    rec = {
        "id": "rec_1",
        "fields": {
            "DueDate": "2026-07-22",
            "EventAt": "2026-07-22T12:34:56.000Z",
            "Name": "alpha",
        },
        "createdTime": "2026-07-22T00:00:00.000Z",
    }

    out = connector._normalize_record(rec)

    assert out["id"] == "rec_1"
    assert out["DueDate"] == date(2026, 7, 22)
    assert out["EventAt"] == datetime(2026, 7, 22, 12, 34, 56, tzinfo=timezone.utc)
    assert out["Name"] == "alpha"
    assert out["_created_time"] == "2026-07-22T00:00:00.000Z"
