"""Tests for formula date/time detection and coercion in AirtableConnector.
"""
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from aracnid_airtable.connector import AirtableConnector


@pytest.fixture
def connector(monkeypatch: pytest.MonkeyPatch) -> AirtableConnector:
    monkeypatch.setenv("AIRTABLE_API_KEY", "key_test")
    monkeypatch.delenv("ARACNID_DATETIME_TZ_MODE", raising=False)  # default utc
    monkeypatch.delenv("ARACNID_LOCAL_TIMEZONE", raising=False)

    with patch("aracnid_airtable.connector.Api") as mock_api_cls:
        mock_api = MagicMock()
        mock_api.table.return_value = MagicMock()
        mock_api_cls.return_value = mock_api
        return AirtableConnector(base_id="app123", table_name="tbl123")


@pytest.mark.parametrize(
    "raw",
    [
        "2026-07-22T12:34Z",
        "2026-07-22T12:34:56Z",
        "2026-07-22T12:34:56.123456+02:00",
        "2026-07-22 12:34:56-04:00",
    ],
)
def test_looks_like_datetime_string_true(connector: AirtableConnector, raw: str) -> None:
    assert connector._looks_like_datetime_string(raw) is True


@pytest.mark.parametrize(
    "raw",
    [
        "2026-07-22",                # date only
        "07/22/2026 12:34 PM",       # non-ISO
        "hello 2026-07-22T12:34Z",   # embedded text
        "",
        "   ",
    ],
)
def test_looks_like_datetime_string_false(connector: AirtableConnector, raw: str) -> None:
    assert connector._looks_like_datetime_string(raw) is False


def test_formula_date_field_with_date_only_value_coerces_to_date(
    connector: AirtableConnector,
) -> None:
    # Simulate schema ambiguity resolved to "date" for formula field
    # and downstream logic not promoting when value is date-only.
    out = connector._coerce_by_airtable_type("date", "2026-07-22")
    assert out == date(2026, 7, 22)
    assert not isinstance(out, datetime)
