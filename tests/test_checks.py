import json
from datetime import datetime

import httpx

from conftest import Recorder, make_sdk


def test_clock_in_posts_with_default_coordinates():
    recorder = Recorder(
        {
            "data": {
                "id": "check-1",
                "employeeId": "employee-1",
                "checkIn": "2026-06-12T09:00:00",
                "origin": "web",
                "createdAt": "2026-06-12T09:00:00",
            }
        }
    )
    sdk = make_sdk(recorder)

    result = sdk.checks.clock_in()

    request = recorder.last
    assert request.url.path == "/api/v3/employees/employee-1/check-in"
    assert json.loads(request.content) == {
        "origin": "web",
        "coordinates": {"latitude": 0.0001, "longitude": 0.0001},
    }
    assert result.id == "check-1"
    assert result.employee_id == "employee-1"


def test_clock_out_with_custom_coordinates():
    recorder = Recorder({"data": {"id": "check-2"}})
    sdk = make_sdk(recorder)

    sdk.checks.clock_out({"latitude": 39.47, "longitude": -0.38})

    body = json.loads(recorder.last.content)
    assert body["coordinates"] == {"latitude": 39.47, "longitude": -0.38}


def test_history_builds_date_range_query():
    recorder = Recorder(lambda request: httpx.Response(200, json=[]))
    sdk = make_sdk(recorder)

    sdk.checks.history("2026-06-01", "2026-06-12")

    body = json.loads(recorder.last.content)
    assert body["from"] == "schedule_context_check"
    assert {"field": "schedule_context_check.date", "operator": ">=", "value": "2026-06-01"} in body["where"]
    assert {"field": "schedule_context_check.date", "operator": "<=", "value": "2026-06-12"} in body["where"]


def test_today_uses_temporal_operation():
    recorder = Recorder(lambda request: httpx.Response(200, json=[]))
    sdk = make_sdk(recorder)

    sdk.checks.today()

    body = json.loads(recorder.last.content)
    assert {
        "field": "schedule_context_check.check_in_check_datetime",
        "operation": "TODAY",
    } in body["where"]


def test_request_create_builds_structured_timestamps():
    recorder = Recorder({"data": {"id": "req-1"}})
    sdk = make_sdk(recorder)

    result = sdk.checks.request_create(check_in="2026-06-10 09:00", comment="forgot to clock in")

    body = json.loads(recorder.last.content)
    assert recorder.last.url.path == "/api/v3/check-request-for-create"
    assert body["employeeId"] == "employee-1"
    assert body["type"] == "work"
    assert body["comment"] == "forgot to clock in"
    # check_out=None is dropped like `undefined` in the TS SDK
    assert "checkOut" not in body
    assert "workBreakId" not in body

    expected_epoch = int(datetime.fromisoformat("2026-06-10T09:00").timestamp())
    assert body["checkIn"] == {
        "date": expected_epoch,
        "origin": "request",
        "timezone": "Europe/Madrid",
    }
    assert result == {"id": "req-1"}


def test_breaks_parses_models():
    recorder = Recorder(
        {"data": [{"id": "wb-1", "name": "Lunch", "breakMinutes": 60, "remunerated": False, "active": True}]}
    )
    sdk = make_sdk(recorder)

    breaks = sdk.checks.breaks()

    assert recorder.last.url.path == "/api/v3/employees/employee-1/work-breaks"
    assert breaks[0].id == "wb-1"
    assert breaks[0].break_minutes == 60
