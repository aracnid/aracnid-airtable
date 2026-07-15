"""AirtableConnector integration tests.

These tests require a real Airtable table and API key, and will create and delete records.

Set the following environment variables to run these tests:
- AIRTABLE_API_KEY: Your Airtable API key.
- AIRTABLE_BASE_ID: The ID of the Airtable base to use for testing.
- AIRTABLE_TABLE_NAME: The name of the Airtable table to use for testing.
"""
from collections.abc import Iterator
import os
import uuid

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


def test_read_many_with_filter_returns_matching_records(
    connector: AirtableConnector, created_ids: list[str]
) -> None:
    token = f"it-{uuid.uuid4().hex[:10]}"
    created = connector.create_one({"Name": token, "Status": "Active"})
    created_ids.append(created["id"])

    rows = connector.read_many({"Name": token})
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