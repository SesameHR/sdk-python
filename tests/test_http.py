import json

import httpx
import pytest

from sesamehr import SesameApiError
from sesamehr.config import SesameConfig, resolve_config
from sesamehr.http import HttpClient, _build_params, _drop_none

from conftest import Recorder


def make_http(handler):
    config = resolve_config(
        SesameConfig(token="test-token", region="EU1", company_id="company-1", employee_id="employee-1")
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return HttpClient(config, client)


def test_get_sends_auth_and_tenant_headers():
    recorder = Recorder({"data": []})
    http = make_http(recorder)
    http.get("/api/v3/things")

    request = recorder.last
    assert request.url == "https://back-eu1.sesametime.com/api/v3/things"
    assert request.headers["Authorization"] == "Bearer test-token"
    assert request.headers["Accept"] == "application/json"
    assert request.headers["CSID"] == "company-1"
    assert request.headers["ESID"] == "employee-1"


def test_get_data_unwraps_envelope():
    recorder = Recorder({"data": [{"id": "1"}]})
    http = make_http(recorder)
    assert http.get_data("/api/v3/things") == [{"id": "1"}]


def test_param_serialization():
    assert _build_params(None) is None
    assert _build_params({"skip": None}) is None
    assert _build_params(
        {"limit": 20, "flag": True, "off": False, "ids": ["a", "b"], "skip": None}
    ) == [("limit", "20"), ("flag", "true"), ("off", "false"), ("ids[]", "a"), ("ids[]", "b")]


def test_query_params_in_url():
    recorder = Recorder({"data": []})
    http = make_http(recorder)
    http.get("/api/v3/things", {"limit": 5, "archivedAt[null]": True, "tags": ["x", "y"]})

    params = recorder.last.url.params
    assert params["limit"] == "5"
    assert params["archivedAt[null]"] == "true"
    assert params.get_list("tags[]") == ["x", "y"]


def test_post_drops_none_and_sets_content_type():
    recorder = Recorder({"data": {"id": "1"}})
    http = make_http(recorder)
    http.post("/api/v3/things", {"a": 1, "b": None, "nested": {"x": None, "y": 2}})

    request = recorder.last
    assert request.headers["Content-Type"] == "application/json"
    assert json.loads(request.content) == {"a": 1, "nested": {"y": 2}}


def test_post_without_body_has_no_content():
    recorder = Recorder({"data": {}})
    http = make_http(recorder)
    http.post("/api/v3/approve/123")
    assert recorder.last.content == b""


def test_drop_none_keeps_falsy_values():
    assert _drop_none({"a": 0, "b": "", "c": False, "d": None}) == {"a": 0, "b": "", "c": False}


def test_api_error_mapping():
    def handler(request):
        return httpx.Response(422, json={"error": {"message": "nope", "errors": ["bad field"]}})

    http = make_http(handler)
    with pytest.raises(SesameApiError) as exc_info:
        http.get("/api/v3/things")

    assert exc_info.value.status == 422
    assert exc_info.value.message == "nope"
    assert exc_info.value.errors == ["bad field"]


def test_api_error_with_invalid_json_body():
    def handler(request):
        return httpx.Response(404, text="not json")

    http = make_http(handler)
    with pytest.raises(SesameApiError) as exc_info:
        http.get("/api/v3/things")
    assert exc_info.value.message == "Sesame API error: HTTP 404"


def test_empty_body_returns_none():
    def handler(request):
        return httpx.Response(204)

    http = make_http(handler)
    assert http.delete("/api/v3/things/1") is None


def test_retries_on_5xx(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    attempts = []

    def handler(request):
        attempts.append(1)
        if len(attempts) < 2:
            return httpx.Response(503, json={"message": "unavailable"})
        return httpx.Response(200, json={"data": "ok"})

    http = make_http(handler)
    assert http.get("/api/v3/things") == {"data": "ok"}
    assert len(attempts) == 2
