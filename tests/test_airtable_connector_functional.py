from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from pyairtable.formulas import match
import pytest

from i_airtable.connector import AirtableConnector


@pytest.fixture
def connector_and_table() -> tuple[AirtableConnector, MagicMock]:
    with patch("i_airtable.connector.os.getenv", return_value="key_test"), patch(
        "i_airtable.connector.Api"
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


def test_read_many_with_filters_builds_formula(connector_and_table: tuple[AirtableConnector, MagicMock]) -> None:
    connector, table = connector_and_table
    table.all.return_value = [
        {"id": "rec_1", "fields": {"status": "active"}, "createdTime": "t1"}
    ]

    filters = {"status": "active"}
    out = connector.read_many(filters)

    # formula kwarg should be used when filters provided
    assert table.all.call_count == 1
    _, kwargs = table.all.call_args
    assert "formula" in kwargs
    assert kwargs["formula"] == match({"status": "active"})
    assert out[0]["status"] == "active"
    assert filters == {"status": "active"}  # input not mutated


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