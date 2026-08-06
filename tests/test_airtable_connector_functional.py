from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

from pyairtable.formulas import to_formula_str
import pytest

from aracnid_airtable.connector import AirtableConnector


@pytest.fixture
def connector_and_table(monkeypatch) -> tuple[AirtableConnector, MagicMock]:
    monkeypatch.setenv("AIRTABLE_API_KEY", "key_test")
    monkeypatch.delenv("ARACNID_DATETIME_TZ_MODE", raising=False)   # default utc
    monkeypatch.delenv("ARACNID_LOCAL_TIMEZONE", raising=False)

    with patch("aracnid_airtable.connector.Api") as mock_api_cls:
        mock_api = MagicMock()
        mock_table = MagicMock()
        mock_api.table.return_value = mock_table
        mock_api_cls.return_value = mock_api

        c = AirtableConnector(base_id="app123", table_name="tbl123")
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
        "_created_time": datetime(2026, 7, 15, 0, 0, tzinfo=timezone.utc),
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
        ({"name": {"$eq": None}}, ["COUNTA({name})=0"]),
        ({"name": {"$ne": "alpha"}}, ["{name}", "!="]),
        ({"name": {"$ne": None}}, ["COUNTA({name})!=0"]),
        ({"age": {"$gt": 18}}, ["{age}", ">", "18"]),
        ({"age": {"$gte": 18}}, ["{age}", ">=", "18"]),
        ({"age": {"$lt": 65}}, ["{age}", "<", "65"]),
        ({"age": {"$lte": 65}}, ["{age}", "<=", "65"]),
        ({"$and": [{"name": {"$eq": "a"}}, {"age": {"$gt": 1}}]}, ["AND"]),
        ({"$or": [{"name": {"$eq": "a"}}, {"name": {"$eq": "b"}}]}, ["OR"]),
        ({"$not": {"name": {"$eq": "a"}}}, ["NOT"]),
        ({"name": {"$in": ["a", "b"]}}, ["OR"]),
        ({"name": {"$in": [None, "b"]}}, ["OR", "COUNTA({name})=0", "{name}='b'"]),
        ({"name": {"$nin": ["a", "b"]}}, ["AND"]),
        ({"name": {"$nin": [None, "b"]}}, ["AND", "COUNTA({name})!=0", "{name}!='b'"]),
        ({"name": {"$exists": True}}, ["COUNTA({name})!=0"]),
        ({"name": {"$exists": False}}, ["COUNTA({name})=0"]),
        ({"name": {"$contains": "ph"}}, ["FIND"]),
        ({"name": {"$startsWith": "al"}}, ["LEFT", "LEN"]),
        ({"name": {"$regex": "^al"}}, ["REGEX_MATCH", "^al"]),
        ({"name": {"$regex": "^AL", "$options": "i"}}, ["REGEX_MATCH", "(?i)^AL"]),
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


def test_query_to_formula_regex_invalid_pattern_raises(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, _ = connector_and_table

    with pytest.raises(RuntimeError, match=r"invalid '\$regex' pattern"):
        connector._query_to_formula({"name": {"$regex": "("}})


def test_query_to_formula_regex_requires_string_field_when_known(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, _ = connector_and_table
    connector._field_types = {"age": "number"}

    with pytest.raises(RuntimeError, match=r"requires a string field"):
        connector._query_to_formula({"age": {"$regex": "^1"}})


def test_query_to_formula_regex_rejects_unsupported_options(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, _ = connector_and_table

    with pytest.raises(RuntimeError, match=r"unsupported '\$options' flags"):
        connector._query_to_formula({"name": {"$regex": "^a", "$options": "m"}})


def test_query_to_formula_regex_rejects_excessive_pattern_length(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, _ = connector_and_table
    long_pattern = "a" * 257

    with pytest.raises(RuntimeError, match=r"pattern exceeds max length"):
        connector._query_to_formula({"name": {"$regex": long_pattern}})


def test_query_to_formula_regex_rejects_excessive_pattern_complexity(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, _ = connector_and_table
    complex_pattern = "|".join("a" for _ in range(70))

    with pytest.raises(RuntimeError, match=r"pattern exceeds complexity policy"):
        connector._query_to_formula({"name": {"$regex": complex_pattern}})


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
            "date_time",
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
        ("date_time", "not-a-datetime"),
        ("date_time", "2026-13-99T99:99:99Z"),
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


def test_local_mode_without_timezone_raises(monkeypatch):
    monkeypatch.setenv("ARACNID_DATETIME_TZ_MODE", "local")
    monkeypatch.delenv("ARACNID_LOCAL_TIMEZONE", raising=False)
    with pytest.raises(ValueError, match="ARACNID_LOCAL_TIMEZONE is required"):
        AirtableConnector(base_id="app123", table_name="tbl123")


def test_update_many_builds_query_and_calls_batch_update(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, table = connector_and_table

    # read_many phase (records matched by query)
    table.all.return_value = [
        {"id": "rec_1", "fields": {"Status": "New"}, "createdTime": "2026-07-15T00:00:00.000Z"},
        {"id": "rec_2", "fields": {"Status": "New"}, "createdTime": "2026-07-15T00:00:00.000Z"},
    ]

    # batch_update response shape from pyairtable-style call
    table.batch_update.return_value = [
        {"id": "rec_1", "fields": {"Status": "Done"}, "createdTime": "2026-07-15T00:00:00.000Z"},
        {"id": "rec_2", "fields": {"Status": "Done"}, "createdTime": "2026-07-15T00:00:00.000Z"},
    ]

    out = connector.update_many({"Status": "New"}, {"Status": "Done"})

    # verify query path used
    assert table.all.call_count == 1
    _, all_kwargs = table.all.call_args
    assert "formula" in all_kwargs
    assert all_kwargs["formula"] is not None

    # verify batch payload
    table.batch_update.assert_called_once_with(
        [
            {"id": "rec_1", "fields": {"Status": "Done"}},
            {"id": "rec_2", "fields": {"Status": "Done"}},
        ]
    )

    # if connector returns count
    assert out == 2


def test_update_many_no_matches_returns_zero_and_skips_batch_update(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, table = connector_and_table
    table.all.return_value = []

    out = connector.update_many({"Status": "Missing"}, {"Status": "Done"})

    assert out == 0
    table.batch_update.assert_not_called()


def test_update_many_rejects_empty_changes(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, table = connector_and_table

    with pytest.raises(ValueError):
        connector.update_many({"Status": "New"}, {})

    table.all.assert_not_called()
    table.batch_update.assert_not_called()


def test_delete_many_hard_false_raises_runtimeerror(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, table = connector_and_table

    with pytest.raises(RuntimeError, match="soft delete is not supported"):
        connector.delete_many({"status": "inactive"}, hard=False)

    table.all.assert_not_called()
    table.batch_delete.assert_not_called()


def test_delete_many_no_matches_returns_zero_and_skips_batch_delete(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, table = connector_and_table
    table.all.return_value = []

    out = connector.delete_many({"status": "inactive"}, hard=True)

    assert out == 0
    table.batch_delete.assert_not_called()


def test_delete_many_builds_query_and_calls_batch_delete(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, table = connector_and_table
    table.all.return_value = [
        {"id": "rec_1", "fields": {"status": "inactive"}, "createdTime": "t1"},
        {"id": "rec_2", "fields": {"status": "inactive"}, "createdTime": "t2"},
    ]
    table.batch_delete.return_value = [
        {"id": "rec_1", "deleted": True},
        {"id": "rec_2", "deleted": True},
    ]

    out = connector.delete_many({"status": "inactive"}, hard=True)

    assert table.all.call_count == 1
    _, kwargs = table.all.call_args
    assert "formula" in kwargs
    assert kwargs["formula"] is not None

    table.batch_delete.assert_called_once_with(["rec_1", "rec_2"])
    assert out == 2


def test_delete_many_backend_exceptions_wrapped_as_runtimeerror(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, table = connector_and_table
    table.all.return_value = [
        {"id": "rec_1", "fields": {"status": "inactive"}, "createdTime": "t1"},
    ]
    table.batch_delete.side_effect = Exception("boom")

    with pytest.raises(RuntimeError, match=r"^delete_many failed:"):
        connector.delete_many({"status": "inactive"}, hard=True)

