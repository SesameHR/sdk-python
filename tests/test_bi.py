import json

import httpx

from sesamehr import BiClient
from sesamehr.config import SesameConfig, resolve_config

from conftest import Recorder


def make_bi(handler):
    config = resolve_config(
        SesameConfig(token="test-token", region="EU1", company_id="company-1", employee_id="employee-1")
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return BiClient(config, client)


def test_url_and_headers():
    recorder = Recorder(lambda request: httpx.Response(200, json=[]))
    bi = make_bi(recorder)
    bi.query({"from": "core_context_employee", "select": [{"field": "core_context_employee.name"}]})

    request = recorder.last
    assert request.url == "https://gateway.sesametime.com/analytics/report-query"
    assert request.headers["Authorization"] == "Bearer test-token"
    assert request.headers["x-company-id"] == "company-1"
    assert request.headers["X-Region"] == "EU1"
    assert request.headers["CSID"] == "company-1"
    assert request.headers["ESID"] == "employee-1"


def test_body_shape_with_defaults():
    recorder = Recorder(lambda request: httpx.Response(200, json=[]))
    bi = make_bi(recorder)
    bi.query(
        {
            "from": "core_context_employee",
            "select": [{"field": "core_context_employee.name", "alias": "name"}],
        }
    )

    body = json.loads(recorder.last.content)
    assert body == {
        "from": "core_context_employee",
        "select": [
            {
                "field": "core_context_employee.name",
                "aggregate": None,
                "alias": "name",
                "placeholder": None,
                "format": None,
            }
        ],
        "where": [],
        "group_by": [],
        "order_by": [],
        "limit": 50,
        "offset": 0,
        "periodicity": None,
        "period_from": None,
        "period_to": None,
    }


def test_where_normalization():
    recorder = Recorder(lambda request: httpx.Response(200, json=[]))
    bi = make_bi(recorder)
    bi.query(
        {
            "from": "schedule_context_check",
            "select": [{"field": "schedule_context_check.date"}],
            "where": [
                {"field": "schedule_context_check.check_in_check_datetime", "operation": "TODAY"},
                {"field": "schedule_context_check.date", "operator": ">=", "value": "2026-01-01"},
                {"field": "core_context_employee.work_status", "operator": "IN", "value": ["online", "remote"]},
            ],
            "group_by": ["schedule_context_check.date"],
            "order_by": [{"field": "date", "direction": "DESC"}, {"field": "name"}],
            "limit": 10,
            "offset": 5,
        }
    )

    body = json.loads(recorder.last.content)
    assert body["where"] == [
        {"field": "schedule_context_check.check_in_check_datetime", "operation": "TODAY"},
        {"field": "schedule_context_check.date", "operator": ">=", "value": "2026-01-01"},
        {"field": "core_context_employee.work_status", "operator": "IN", "value": ["online", "remote"]},
    ]
    assert body["group_by"] == ["schedule_context_check.date"]
    assert body["order_by"] == [
        {"field": "date", "direction": "DESC"},
        {"field": "name", "direction": "ASC"},
    ]
    assert body["limit"] == 10
    assert body["offset"] == 5


def test_returns_rows():
    rows = [{"name": "Ana"}, {"name": "Luis"}]
    bi = make_bi(lambda request: httpx.Response(200, json=rows))
    result = bi.query({"from": "core_context_employee", "select": [{"field": "core_context_employee.name"}]})
    assert result == rows
