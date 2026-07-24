"""Unit tests for datetime read coercion.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from aracnid_airtable.connector import AirtableConnector


@pytest.fixture
def connector_and_table(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[AirtableConnector, MagicMock]:
    monkeypatch.setenv("AIRTABLE_API_KEY", "key_test")
    monkeypatch.delenv("ARACNID_DATETIME_TZ_MODE", raising=False)  # default utc
    monkeypatch.delenv("ARACNID_LOCAL_TIMEZONE", raising=False)

    with patch("aracnid_airtable.connector.Api") as mock_api_cls:
        mock_api = MagicMock()
        mock_table = MagicMock()
        mock_api.table.return_value = mock_table
        mock_api_cls.return_value = mock_api

        connector = AirtableConnector(base_id="app123", table_name="tbl123")
        connector.table = mock_table
        return connector, mock_table


@pytest.mark.parametrize(
    ("field_type", "raw"),
    [
        ("date", 123),
        ("date_time", True),
        ("date", None),
        ("date_time", {"x": 1}),
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


@pytest.mark.parametrize(
    ("field_type", "raw"),
    [
        ("date", "not-a-date"),
        ("date_time", "not-a-datetime"),
    ],
)
def test_coerce_by_airtable_type_invalid_string_passthrough(
    connector_and_table: tuple[AirtableConnector, MagicMock],
    field_type: str,
    raw: str,
) -> None:
    connector, _ = connector_and_table

    out = connector._coerce_by_airtable_type(field_type, raw)

    assert out == raw


def test_coerce_by_airtable_type_date_success(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, _ = connector_and_table

    out = connector._coerce_by_airtable_type("date", "2026-07-22")

    assert out == date(2026, 7, 22)


def test_datetime_coercion_default_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    # replacement: instantiate connector AFTER env is set
    monkeypatch.setenv("AIRTABLE_API_KEY", "key_test")
    monkeypatch.delenv("ARACNID_DATETIME_TZ_MODE", raising=False)
    monkeypatch.delenv("ARACNID_LOCAL_TIMEZONE", raising=False)

    with patch("aracnid_airtable.connector.Api") as mock_api_cls:
        mock_api = MagicMock()
        mock_api.table.return_value = MagicMock()
        mock_api_cls.return_value = mock_api

        connector = AirtableConnector(base_id="app123", table_name="tbl123")
        out = connector._coerce_by_airtable_type("date_time", "2026-07-22T12:00:00-04:00")

    assert isinstance(out, datetime)
    assert out.tzinfo is not None
    assert out.astimezone(timezone.utc) == datetime(2026, 7, 22, 16, 0, 0, tzinfo=timezone.utc)


def test_datetime_coercion_keep_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIRTABLE_API_KEY", "key_test")
    monkeypatch.setenv("ARACNID_DATETIME_TZ_MODE", "keep")
    monkeypatch.delenv("ARACNID_LOCAL_TIMEZONE", raising=False)

    with patch("aracnid_airtable.connector.Api") as mock_api_cls:
        mock_api = MagicMock()
        mock_api.table.return_value = MagicMock()
        mock_api_cls.return_value = mock_api

        connector = AirtableConnector(base_id="app123", table_name="tbl123")
        out = connector._coerce_by_airtable_type("date_time", "2026-07-22T12:00:00-04:00")

    assert isinstance(out, datetime)
    assert out.utcoffset() == timedelta(hours=-4)


def test_datetime_coercion_local_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIRTABLE_API_KEY", "key_test")
    monkeypatch.setenv("ARACNID_DATETIME_TZ_MODE", "local")
    monkeypatch.setenv("ARACNID_LOCAL_TIMEZONE", "America/New_York")

    with patch("aracnid_airtable.connector.Api") as mock_api_cls:
        mock_api = MagicMock()
        mock_api.table.return_value = MagicMock()
        mock_api_cls.return_value = mock_api

        connector = AirtableConnector(base_id="app123", table_name="tbl123")
        out = connector._coerce_by_airtable_type("date_time", "2026-07-22T12:00:00Z")

    assert isinstance(out, datetime)
    # 12:00Z == 08:00 EDT in July
    assert out.hour == 8


def test_normalize_record_applies_schema_typed_coercion(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, _ = connector_and_table

    # deterministic schema map
    connector._field_types = {
        "DueDate": "date",
        "EventAt": "date_time",
        "Name": "single_line_text",
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


def test_normalize_record_non_date_text_unchanged(
    connector_and_table: tuple[AirtableConnector, MagicMock],
) -> None:
    connector, _ = connector_and_table
    connector._field_types = {"Name": "single_line_text"}

    rec = {"id": "rec_1", "fields": {"Name": "2026-07-22T12:00:00Z"}}
    out = connector._normalize_record(rec)

    assert out["Name"] == "2026-07-22T12:00:00Z"