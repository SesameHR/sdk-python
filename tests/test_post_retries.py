"""A POST that may already have been processed must not be sent a second time.

Each handler below answers the first request with a failure that can happen after
the backend has already acted (a gateway 5xx, a dropped connection, a non-JSON
reply), then answers normally. A write must reach the server exactly once.
"""

import io

import httpx
import pytest

from sesamehr import SesameApiError, SesameConnectionError
from sesamehr.retry import retry_if_not_sent

from conftest import make_sdk

WRITES = {
    "checks.clock_in": lambda sdk: sdk.checks.clock_in(),
    "checks.clock_out": lambda sdk: sdk.checks.clock_out(),
    "checks.pause": lambda sdk: sdk.checks.pause("break-1"),
    "checks.request_create": lambda sdk: sdk.checks.request_create(check_in="2026-06-10 09:00:00"),
    "team.create_check": lambda sdk: sdk.team.create_check("employee-2", check_in="2026-06-10 09:00:00"),
    "team.approve_check_request": lambda sdk: sdk.team.approve_check_request("request-1"),
    "team.approve_vacation": lambda sdk: sdk.team.approve_vacation("request-1"),
    "vacations.request": lambda sdk: sdk.vacations.request(calendar_id="cal-1", dates=["2026-07-01"]),
    "notifications.send_push": lambda sdk: sdk.notifications.send_push(
        employee_id="employee-2", title="t", message="m", application_id="app-1"
    ),
    "documents.upload": lambda sdk: sdk.documents.upload(
        directory_id="dir-1", file=io.BytesIO(b"%PDF-1.4"), file_name="payslip.pdf"
    ),
    "community.create_post": lambda sdk: sdk.community.create_post(channel_id="channel-1", content="hello"),
}


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)


def fail_first(failure, data=None):
    """Handler that records requests, fails the first one, then answers 200."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return failure(request)
        return httpx.Response(200, json={"data": {"id": "1"} if data is None else data})

    return handler, requests


def gateway(status):
    return lambda request: httpx.Response(status, json={"message": "Bad Gateway"})


def dropped(request):
    raise httpx.RemoteProtocolError("Server disconnected without sending a response.", request=request)


def html_page(request):
    return httpx.Response(200, text="<html>proxy</html>", headers={"content-type": "text/html"})


def refused(request):
    raise httpx.ConnectError("[Errno 61] Connection refused", request=request)


def run(call, sdk):
    try:
        call(sdk)
    except (SesameApiError, SesameConnectionError):
        pass


@pytest.mark.parametrize("status", [500, 502, 503, 504])
@pytest.mark.parametrize("name", sorted(WRITES))
def test_write_is_sent_once_after_5xx(name, status):
    handler, requests = fail_first(gateway(status))
    run(WRITES[name], make_sdk(handler))
    assert len(requests) == 1


@pytest.mark.parametrize("name", sorted(WRITES))
def test_write_is_sent_once_after_dropped_connection(name):
    handler, requests = fail_first(dropped)
    run(WRITES[name], make_sdk(handler))
    assert len(requests) == 1


def test_clock_in_after_5xx_raises_instead_of_repeating():
    handler, requests = fail_first(gateway(502))
    with pytest.raises(SesameApiError) as exc_info:
        make_sdk(handler).checks.clock_in()
    assert exc_info.value.status == 502
    assert len(requests) == 1


def test_clock_in_with_unreadable_success_body_is_sent_once():
    handler, requests = fail_first(html_page)
    with pytest.raises(SesameConnectionError):
        make_sdk(handler).checks.clock_in()
    assert len(requests) == 1


@pytest.mark.parametrize("name", ["checks.clock_in", "documents.upload"])
def test_write_is_retried_when_connection_could_not_be_opened(name):
    handler, requests = fail_first(refused)
    WRITES[name](make_sdk(handler))
    assert len(requests) == 2


def test_get_is_still_retried_after_5xx():
    handler, requests = fail_first(gateway(503), data=[])
    make_sdk(handler).checks.breaks()
    assert len(requests) == 2


def test_put_is_still_retried_after_5xx():
    handler, requests = fail_first(gateway(503))
    make_sdk(handler).team.edit_check("check-1", check_in="2026-06-10 09:00:00")
    assert len(requests) == 2


def test_delete_is_still_retried_after_dropped_connection():
    handler, requests = fail_first(dropped)
    make_sdk(handler).vacations.cancel("request-1")
    assert len(requests) == 2


def test_work_stats_summary_is_a_read_and_is_still_retried():
    def handler(request):
        handler.calls += 1
        if handler.calls == 1:
            return httpx.Response(503, json={"message": "unavailable"})
        return httpx.Response(200, json={"data": {"secondsWorked": 1}})

    handler.calls = 0
    make_sdk(handler).work_stats.summary("2026-06-01", "2026-06-30")
    assert handler.calls == 2


def test_retry_if_not_sent_predicate():
    assert retry_if_not_sent(SesameConnectionError("refused", is_connect_error=True))
    assert not retry_if_not_sent(SesameConnectionError("Server disconnected"))
    assert not retry_if_not_sent(SesameConnectionError("timed out", is_timeout=True))
    assert not retry_if_not_sent(SesameApiError(502, None))
    assert not retry_if_not_sent(SesameApiError(404, None))
