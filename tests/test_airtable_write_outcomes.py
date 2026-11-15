import json
from urllib.parse import parse_qs, urlsplit

import pytest
from requests import Response
from requests.exceptions import HTTPError, ReadTimeout
from unittest.mock import Mock

from aracnid_airtable.connector import AirtableConnector
from aracnid_core import RecordNotFoundError, WriteOutcomeUnknownError, WriteRejectedError


BASE_ID = "app00000000000000"
TABLE_ID = "tbl00000000000000"
RECORD_ID = "rec00000000000000"
FIELDS = {"Name": "write outcome test"}


@pytest.fixture
def connector_and_dispatch(monkeypatch):
    monkeypatch.setenv("AIRTABLE_API_KEY", "offline-test-key")
    connector = AirtableConnector(BASE_ID, TABLE_ID)
    dispatch = Mock()
    monkeypatch.setattr(connector.api.session, "send", dispatch)
    return connector, dispatch


def response_with_json(status, reason, payload):
    response = Response()
    response.status_code = status
    response.reason = reason
    response._content = json.dumps(payload).encode()
    return response


def error_response(status, reason):
    return response_with_json(status, reason, {"error": {"message": reason}})


def test_update_one_missing_record_creates_nothing(connector_and_dispatch):
    connector, dispatch = connector_and_dispatch
    dispatch.return_value = error_response(404, "Record not found")

    with pytest.raises(RecordNotFoundError, match=RECORD_ID) as caught:
        connector.update_one(RECORD_ID, FIELDS)

    assert isinstance(caught.value.__cause__, HTTPError)
    dispatch.assert_called_once()
    request = dispatch.call_args.args[0]
    assert request.method == "PATCH"
    assert request.url.endswith(f"/{TABLE_ID}/{RECORD_ID}")
    assert json.loads(request.body)["fields"] == FIELDS
    assert "performUpsert" not in json.loads(request.body)


@pytest.mark.parametrize(
    "lookup_result", ["absent", "present", "table-forbidden", "table-not-found"]
)
def test_delete_queries_table_after_ambiguous_forbidden_response(
    connector_and_dispatch, lookup_result
):
    connector, dispatch = connector_and_dispatch
    forbidden = response_with_json(
        403,
        "Forbidden",
        {"error": {"type": "INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND"}},
    )
    lookup_responses = {
        "absent": response_with_json(200, "OK", {"records": []}),
        "present": response_with_json(
            200,
            "OK",
            {"records": [{"id": RECORD_ID, "fields": FIELDS, "createdTime": "2026-01-01T00:00:00Z"}]},
        ),
        "table-forbidden": response_with_json(
            403, "Forbidden", {"error": {"type": "INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND"}}
        ),
        "table-not-found": error_response(404, "Table not found"),
    }
    dispatch.side_effect = [forbidden, lookup_responses[lookup_result]]

    if lookup_result == "absent":
        assert connector.delete_one(RECORD_ID, hard=True) is False
    else:
        with pytest.raises(WriteRejectedError, match="INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND") as caught:
            connector.delete_one(RECORD_ID, hard=True)
        cause = caught.value.__cause__
        assert isinstance(cause, HTTPError)
        assert cause.response is forbidden

    requests = [call.args[0] for call in dispatch.call_args_list]
    assert [request.method for request in requests] == ["DELETE", "GET"]
    assert urlsplit(requests[0].url).path == f"/v0/{BASE_ID}/{TABLE_ID}/{RECORD_ID}"
    lookup_url = urlsplit(requests[1].url)
    assert lookup_url.path == f"/v0/{BASE_ID}/{TABLE_ID}"
    lookup_params = parse_qs(lookup_url.query)
    assert lookup_params["filterByFormula"] == [f"RECORD_ID()='{RECORD_ID}'"]
    assert lookup_params["maxRecords"] == ["1"]


@pytest.mark.parametrize(
    ("operation", "args", "method"),
    [
        ("create_one", (FIELDS,), "POST"),
        ("update_one", (RECORD_ID, FIELDS), "PATCH"),
        ("replace_one", (RECORD_ID, FIELDS), "PUT"),
        ("delete_one", (RECORD_ID, True), "DELETE"),
    ],
)
@pytest.mark.parametrize("lost_response", [False, True], ids=["rejected", "lost-response"])
def test_single_record_write_outcomes(
    connector_and_dispatch, operation, args, method, lost_response
):
    connector, dispatch = connector_and_dispatch
    if lost_response:
        dispatch.side_effect = ReadTimeout("Response lost after dispatch")
        expected_error = WriteOutcomeUnknownError
        reason = "Response lost after dispatch"
    else:
        reason = "Provider declined the write"
        dispatch.return_value = error_response(422, reason)
        expected_error = WriteRejectedError

    with pytest.raises(expected_error, match=reason) as caught:
        getattr(connector, operation)(*args)

    if lost_response:
        assert caught.value.__cause__ is dispatch.side_effect
    else:
        assert isinstance(caught.value.__cause__, HTTPError)
    dispatch.assert_called_once()
    request = dispatch.call_args.args[0]
    assert request.method == method
    retries = connector.api.session.get_adapter(request.url).max_retries
    assert not retries.is_retry(method, 429)
