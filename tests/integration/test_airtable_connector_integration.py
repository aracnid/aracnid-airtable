"""AirtableConnector integration tests.

These tests require a real Airtable table and API key, and will create and delete records.

Set the following environment variables to run these tests:
- AIRTABLE_API_KEY: Your Airtable API key.
- AIRTABLE_BASE_ID: The ID of the Airtable base to use for testing.
- AIRTABLE_TABLE_NAME: The name of the Airtable table to use for testing.
"""
from collections.abc import Iterator
from datetime import date, datetime, timezone
import os
import uuid

from aracnid_core.exceptions import QueryValidationError
import pytest

from aracnid_airtable.connector import AirtableConnector


pytestmark = [pytest.mark.integration]


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
    for rid in ids:
        try:
            connector.delete_one(rid, hard=True)
        except Exception:
            pass


def test_create_and_read_one_roundtrip(
    connector: AirtableConnector, created_ids: list[str]
) -> None:
    token = f"it-{uuid.uuid4().hex[:10]}"
    created = connector.create_one({"Name": token, "Status": "New"})
    created_ids.append(created["id"])

    got = connector.read_one(created["id"])
    assert got is not None
    assert got["id"] == created["id"]
    assert got["Name"] == token
    assert got["Status"] == "New"


def test_read_one_missing_returns_none(connector: AirtableConnector) -> None:
    missing_id = "rec" + uuid.uuid4().hex[:14]
    got = connector.read_one(missing_id)
    assert got is None


def test_read_many_with_query_returns_matching_records(
    connector: AirtableConnector, created_ids: list[str]
) -> None:
    token = f"it-{uuid.uuid4().hex[:10]}"
    created = connector.create_one({"Name": token, "Status": "Active"})
    created_ids.append(created["id"])

    rows = connector.read_many({"Name": token})
    ids = {r["id"] for r in rows}
    assert created["id"] in ids


def test_read_many_date_equality_with_python_date_literal(
    connector: AirtableConnector, created_ids: list[str]
) -> None:
    d = date(2026, 7, 22)
    tag = f"it-date-{uuid.uuid4().hex[:8]}"

    created = connector.create_one(
        {"Name": "date-eq", "Tag": tag, "DueDate": d, "Status": "Active"}
    )
    created_ids.append(created["id"])

    rows = connector.read_many(
        {
            "$and": [
                {"Tag": {"$eq": tag}},
                {"DueDate": {"$eq": d}},
            ]
        }
    )
    ids = {r["id"] for r in rows}
    assert created["id"] in ids
    
    
def test_update_one_persists_changes(
    connector: AirtableConnector, created_ids: list[str]
) -> None:
    created = connector.create_one({"Name": f"it-{uuid.uuid4().hex[:8]}", "Status": "New"})
    created_ids.append(created["id"])

    updated = connector.update_one(created["id"], {"Status": "Active"})
    assert updated["id"] == created["id"]
    assert updated["Status"] == "Active"

    got = connector.read_one(created["id"])
    assert got is not None
    assert got["Status"] == "Active"


def test_replace_one_replaces_fields(
    connector: AirtableConnector, created_ids: list[str]
) -> None:
    created = connector.create_one(
        {"Name": f"it-{uuid.uuid4().hex[:8]}", "Status": "New", "Category": "Old"}
    )
    created_ids.append(created["id"])

    replaced = connector.replace_one(created["id"], {"Name": "replaced"})
    assert replaced["id"] == created["id"]
    assert replaced["Name"] == "replaced"

    got = connector.read_one(created["id"])
    assert got is not None
    assert got["Name"] == "replaced"


def test_delete_one_hard_true_deletes_record(
    connector: AirtableConnector, created_ids: list[str]
) -> None:
    created = connector.create_one({"Name": f"it-{uuid.uuid4().hex[:8]}"})

    deleted = connector.delete_one(created["id"], hard=True)
    assert deleted is True

    # no cleanup append because already deleted
    got = connector.read_one(created["id"])
    assert got is None


def test_delete_one_hard_false_raises(connector: AirtableConnector) -> None:
    with pytest.raises(RuntimeError, match="soft delete is not supported"):
        connector.delete_one("rec_dummy", hard=False)


def test_update_missing_raises_runtimeerror(connector: AirtableConnector) -> None:
    missing_id = "rec" + uuid.uuid4().hex[:14]
    with pytest.raises(RuntimeError, match="not found|failed"):
        connector.update_one(missing_id, {"Status": "x"})


def test_replace_missing_raises_runtimeerror(connector: AirtableConnector) -> None:
    missing_id = "rec" + uuid.uuid4().hex[:14]
    with pytest.raises(RuntimeError, match="not found|failed"):
        connector.replace_one(missing_id, {"Name": "x"})


def test_delete_missing_returns_false(connector: AirtableConnector) -> None:
    missing_id = "rec" + uuid.uuid4().hex[:14]
    assert connector.delete_one(missing_id, hard=True) is False


def _ids(rows):
    return {r["id"] for r in rows}


@pytest.fixture
def seeded_records(connector):
    created_ids = []
    run = uuid.uuid4().hex[:8]
    tag = f"it_qdsl_{run}"

    def _create(payload):
        rec = connector.create_one(payload)
        created_ids.append(rec["id"])
        return rec

    recs = {}
    recs["r1"] = _create({"Name": "alpha", "Status": "Active", "Tag": tag, "Category": "exists", "Code": "A1"})
    recs["r2"] = _create({"Name": "beta", "Status": "Inactive", "Tag": tag, "Category": "exists"})
    recs["r3"] = _create({"Name": "gamma", "Status": "Active", "Tag": tag, "Category": "exists", "Code": "G1"})
    recs["num"] = _create({"Name": "numcase", "Status": "Active", "Tag": tag, "CountInt": 42, "ScoreFloat": 3.5})
    recs["time"] = _create({"Name": "timecase", "Status": "Active", "Tag": tag, "DueDate": "2026-07-19", "EventAt": "2026-07-19T12:34:56.000Z"})
    recs["quote"] = _create({"Name": "O'Brien", "Status": "Active", "Tag": tag})
    recs["dquote"] = _create({"Name": 'He said "hello"', "Status": "Active", "Tag": tag})
    recs["backslash"] = _create({"Name": r"path\to\file", "Status": "Active", "Tag": tag})
    recs["space"] = _create({"Name": "  padded value  ", "Status": "Active", "Tag": tag})
    recs["newline"] = _create({"Name": "line1\nline2", "Status": "Active", "Tag": tag})
    recs["unicode"] = _create({"Name": "café ☕", "Status": "Active", "Tag": tag})

    yield tag, recs

    # teardown (best-effort)
    for rid in reversed(created_ids):
        try:
            connector.delete_one(rid, hard=True)
        except Exception:
            pass


def test_read_many_query_dsl_integration_matrix(connector, seeded_records):
    tag, recs = seeded_records

    # 1) $eq
    out_eq = connector.read_many({"Tag": tag})
    assert _ids(out_eq) >= {recs["r1"]["id"], recs["r2"]["id"], recs["r3"]["id"]}

    # 2) $exists true
    out_exists_true = connector.read_many(
        {"$and": [{"Tag": tag}, {"Code": {"$exists": True}}]}
    )
    assert _ids(out_exists_true) == {recs["r1"]["id"], recs["r3"]["id"]}

    # 3) $exists false
    out_exists_false = connector.read_many(
        {"$and": [{"Tag": tag}, {"Category": "exists"}, {"Code": {"$exists": False}}]}
    )
    assert _ids(out_exists_false) == {recs["r2"]["id"]}

    # 4) $ne
    out_ne = connector.read_many(
        {"$and": [{"Tag": {"$eq": tag}}, {"Category": "exists"}, {"Name": {"$ne": "beta"}}]}
    )
    assert _ids(out_ne) == {recs["r1"]["id"], recs["r3"]["id"]}
    
    # 5) labdb2-style combined query: $and + $eq + $exists + $ne
    out_complex = connector.read_many(
        {
            "$and": [
                {"Tag": {"$eq": tag}},
                {"Status": {"$eq": "Active"}},
                {"Code": {"$exists": True}},
                {"Name": {"$ne": "gamma"}},
            ]
        }
    )
    assert _ids(out_complex) == {recs["r1"]["id"]}

    # 6) numeric literal equivalency (int + float)
    # Airtable often stores numeric-like values as numbers; verify eq translation works.
    out_int = connector.read_many(
        {"$and": [{"Tag": {"$eq": tag}}, {"CountInt": {"$eq": 42}}]}
    )
    assert _ids(out_int) == {recs["num"]["id"]}

    out_float = connector.read_many(
        {"$and": [{"Tag": {"$eq": tag}}, {"ScoreFloat": {"$eq": 3.5}}]}
    )
    assert _ids(out_float) == {recs["num"]["id"]}

    # 7) date + datetime literal equivalency
    # Store as Airtable date/date-time text representations and validate exact matching.
    # (If your Airtable fields are true Date/DateTime types, use matching format your base is configured for.)
    out_date = connector.read_many(
        {"$and": [{"Tag": {"$eq": tag}}, {"DueDate": {"$eq": date(2026, 7, 19)}}]}
    )
    assert _ids(out_date) == {recs["time"]["id"]}

    out_datetime = connector.read_many(
        {
            "$and": [
                {"Tag": {"$eq": tag}},
                {"EventAt": {"$eq": datetime(2026, 7, 19, 12, 34, 56, tzinfo=timezone.utc)}},
            ]
        }
    )
    assert _ids(out_datetime) == {recs["time"]["id"]}

    # 8) single quote in string
    out_quote = connector.read_many(
        {"$and": [{"Tag": {"$eq": tag}}, {"Name": {"$eq": "O'Brien"}}]}
    )
    assert _ids(out_quote) == {recs["quote"]["id"]}

    # 9) double quotes in string
    out_dquote = connector.read_many(
        {"$and": [{"Tag": {"$eq": tag}}, {"Name": {"$eq": 'He said "hello"'}}]}
    )
    assert _ids(out_dquote) == {recs["dquote"]["id"]}

    # 10) backslash in string
    out_backslash = connector.read_many(
        {"$and": [{"Tag": {"$eq": tag}}, {"Name": {"$eq": r"path\to\file"}}]}
    )
    assert _ids(out_backslash) == {recs["backslash"]["id"]}

    # 11) leading/trailing whitespace preserved
    out_space = connector.read_many(
        {"$and": [{"Tag": {"$eq": tag}}, {"Name": {"$eq": "  padded value  "}}]}
    )
    assert _ids(out_space) == {recs["space"]["id"]}

    # 12) newline in string
    out_newline = connector.read_many(
        {"$and": [{"Tag": {"$eq": tag}}, {"Name": {"$eq": "line1\nline2"}}]}
    )
    assert _ids(out_newline) == {recs["newline"]["id"]}

    # 13) unicode / emoji
    out_unicode = connector.read_many(
        {"$and": [{"Tag": {"$eq": tag}}, {"Name": {"$eq": "café ☕"}}]}
    )
    assert _ids(out_unicode) == {recs["unicode"]["id"]}

    # 14) contains with quote character
    out_contains_quote = connector.read_many(
        {"$and": [{"Tag": {"$eq": tag}}, {"Name": {"$contains": "O'"}}]}
    )
    assert _ids(out_contains_quote) == {recs["quote"]["id"]}


def test_read_many_query_dsl_unsupported_operator_raises(connector):
    query = {"Name": {"$regex": "^alp"}}

    with pytest.raises(QueryValidationError, match=r"unsupported field operator '\$regex'"):
        connector.read_many(query)


def test_create_one_naive_datetime_raises_valueerror(connector: AirtableConnector) -> None:
    naive_dt = datetime(2026, 7, 19, 12, 34, 56)  # tzinfo=None
    with pytest.raises(ValueError, match=r"datetime field values must be timezone-aware|timezone-aware|tzinfo"):
        connector.create_one({"Name": f"it-{uuid.uuid4().hex[:8]}", "EventAt": naive_dt})


def test_update_one_naive_datetime_raises_valueerror(
    connector: AirtableConnector, created_ids: list[str]
) -> None:
    created = connector.create_one({"Name": f"it-{uuid.uuid4().hex[:8]}", "Status": "New"})
    created_ids.append(created["id"])

    naive_dt = datetime(2026, 7, 19, 12, 34, 56)  # tzinfo=None
    with pytest.raises(ValueError, match=r"datetime field values must be timezone-aware|timezone-aware|tzinfo"):
        connector.update_one(created["id"], {"EventAt": naive_dt})


def test_replace_one_naive_datetime_raises_valueerror(
    connector: AirtableConnector, created_ids: list[str]
) -> None:
    created = connector.create_one({"Name": f"it-{uuid.uuid4().hex[:8]}", "Status": "New"})
    created_ids.append(created["id"])

    naive_dt = datetime(2026, 7, 19, 12, 34, 56)  # tzinfo=None
    with pytest.raises(ValueError, match=r"datetime field values must be timezone-aware|timezone-aware|tzinfo"):
        connector.replace_one(created["id"], {"Name": "replaced", "EventAt": naive_dt})


def test_create_one_date_field_roundtrip(
    connector: AirtableConnector, created_ids: list[str]
) -> None:
    d = date(2026, 7, 19)
    created = connector.create_one(
        {"Name": f"it-{uuid.uuid4().hex[:8]}", "DueDate": d, "Status": "New"}
    )
    created_ids.append(created["id"])

    got = connector.read_one(created["id"])
    assert got is not None
    # Airtable may return date-like values as strings; assert calendar-day semantic.
    assert str(got["DueDate"]).startswith("2026-07-19")


def test_update_one_date_field_roundtrip(
    connector: AirtableConnector, created_ids: list[str]
) -> None:
    created = connector.create_one({"Name": f"it-{uuid.uuid4().hex[:8]}", "Status": "New"})
    created_ids.append(created["id"])

    d = date(2026, 7, 20)
    updated = connector.update_one(created["id"], {"DueDate": d})
    assert updated["id"] == created["id"]

    got = connector.read_one(created["id"])
    assert got is not None
    assert str(got["DueDate"]).startswith("2026-07-20")


def test_replace_one_date_field_roundtrip(
    connector: AirtableConnector, created_ids: list[str]
) -> None:
    created = connector.create_one(
        {"Name": f"it-{uuid.uuid4().hex[:8]}", "Status": "New", "Category": "Old"}
    )
    created_ids.append(created["id"])

    d = date(2026, 7, 21)
    replaced = connector.replace_one(created["id"], {"Name": "replaced", "DueDate": d})
    assert replaced["id"] == created["id"]

    got = connector.read_one(created["id"])
    assert got is not None
    assert got["Name"] == "replaced"
    assert str(got["DueDate"]).startswith("2026-07-21")
