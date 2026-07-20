"""Airtable datetime semantics integration tests.

These tests require a real Airtable table and API key, and will create and delete records.

Set the following environment variables to run these tests:
- AIRTABLE_API_KEY: Your Airtable API key.
- AIRTABLE_BASE_ID: The ID of the Airtable base to use for testing.
- AIRTABLE_TABLE_NAME: The name of the Airtable table to use for testing.
"""
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
import os
import uuid
from zoneinfo import ZoneInfo

import pytest
from aracnid_core.exceptions import QueryValidationError

from aracnid_airtable.connector import AirtableConnector


pytestmark = [pytest.mark.integration]

# Module-level field constants (env-overridable), matching existing integration style.
DATETIME_FIELD = 'EventAt'
TAG_FIELD = 'Tag'


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        pytest.skip(f"{name} is required for Airtable integration tests")
    return value.strip()


@pytest.fixture
def connector() -> AirtableConnector:
    base_id = _require_env("AIRTABLE_BASE_ID")
    table_name = _require_env("AIRTABLE_TABLE_NAME")
    # Connector already reads AIRTABLE_API_KEY from env.
    return AirtableConnector(base_id=base_id, table_name=table_name)


@pytest.fixture
def created_ids(connector: AirtableConnector) -> Iterator[list[str]]:
    ids: list[str] = []
    yield ids
    for rid in reversed(ids):
        try:
            connector.delete_one(rid, hard=True)
        except Exception:
            pass


@pytest.fixture
def seeded_temporal_records(
    connector: AirtableConnector, created_ids: list[str]
) -> dict[str, object]:
    run = uuid.uuid4().hex[:8]
    tag = f"it_dt_{run}"

    dt_local = datetime(2026, 7, 19, 9, 30, tzinfo=ZoneInfo("America/New_York"))
    dt_utc = dt_local.astimezone(timezone.utc)
    dt_before = dt_local - timedelta(minutes=1)
    dt_after = dt_local + timedelta(minutes=1)

    rec_before = connector.create_one(
        {TAG_FIELD: tag, "Name": "before", DATETIME_FIELD: dt_before}
    )
    created_ids.append(rec_before["id"])

    rec_exact = connector.create_one(
        {TAG_FIELD: tag, "Name": "exact", DATETIME_FIELD: dt_local}
    )
    created_ids.append(rec_exact["id"])

    rec_after = connector.create_one(
        {TAG_FIELD: tag, "Name": "after", DATETIME_FIELD: dt_after}
    )
    created_ids.append(rec_after["id"])

    return {
        "tag": tag,
        "dt_local": dt_local,
        "dt_utc": dt_utc,
        "dt_before": dt_before,
        "dt_after": dt_after,
        "id_before": rec_before["id"],
        "id_exact": rec_exact["id"],
        "id_after": rec_after["id"],
    }


def _ids(rows):
    return {r["id"] for r in rows}


def test_datetime_eq_accepts_aware_local_tz(connector, seeded_temporal_records) -> None:
    data = seeded_temporal_records
    out = connector.read_many(
        {
            "$and": [
                {TAG_FIELD: {"$eq": data["tag"]}},
                {DATETIME_FIELD: {"$eq": data["dt_local"]}},
            ]
        }
    )
    assert data["id_exact"] in _ids(out)


def test_datetime_eq_utc_equivalent_matches_same_records(
    connector, seeded_temporal_records
) -> None:
    data = seeded_temporal_records

    out_local = connector.read_many(
        {
            "$and": [
                {TAG_FIELD: {"$eq": data["tag"]}},
                {DATETIME_FIELD: {"$eq": data["dt_local"]}},
            ]
        }
    )
    out_utc = connector.read_many(
        {
            "$and": [
                {TAG_FIELD: {"$eq": data["tag"]}},
                {DATETIME_FIELD: {"$eq": data["dt_utc"]}},
            ]
        }
    )

    assert _ids(out_local) == _ids(out_utc)
    assert data["id_exact"] in _ids(out_local)


def test_datetime_range_with_aware_boundary(connector, seeded_temporal_records) -> None:
    data = seeded_temporal_records

    out = connector.read_many(
        {
            "$and": [
                {TAG_FIELD: {"$eq": data["tag"]}},
                {DATETIME_FIELD: {"$gte": data["dt_local"]}},
                {DATETIME_FIELD: {"$lt": data["dt_after"] + timedelta(seconds=1)}},
            ]
        }
    )
    ids = _ids(out)
    assert data["id_before"] not in ids
    assert data["id_exact"] in ids
    assert data["id_after"] in ids


def test_datetime_naive_rejected(connector, seeded_temporal_records) -> None:
    data = seeded_temporal_records
    dt_naive = datetime(2026, 7, 19, 9, 30)  # tzinfo=None

    with pytest.raises(QueryValidationError, match=r"datetime|timezone|naive|tzinfo"):
        connector.read_many(
            {
                "$and": [
                    {TAG_FIELD: {"$eq": data["tag"]}},
                    {DATETIME_FIELD: {"$eq": dt_naive}},
                ]
            }
        )


def test_datetime_dst_local_and_utc_instant_equivalence(
    connector: AirtableConnector, created_ids: list[str]
) -> None:
    """
    DST-focused check using aware local datetime and equivalent UTC instant.
    """
    run = uuid.uuid4().hex[:8]
    tag = f"it_dst_{run}"

    dt_local = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"))
    dt_utc = dt_local.astimezone(timezone.utc)

    created = connector.create_one({TAG_FIELD: tag, "Name": "dst", DATETIME_FIELD: dt_local})
    created_ids.append(created["id"])

    out_local = connector.read_many(
        {"$and": [{TAG_FIELD: {"$eq": tag}}, {DATETIME_FIELD: {"$eq": dt_local}}]}
    )
    out_utc = connector.read_many(
        {"$and": [{TAG_FIELD: {"$eq": tag}}, {DATETIME_FIELD: {"$eq": dt_utc}}]}
    )

    assert _ids(out_local) == _ids(out_utc)
    assert created["id"] in _ids(out_local)