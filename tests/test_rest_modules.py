import json

import httpx

from conftest import Recorder, make_sdk


def test_announcements_list_params():
    recorder = Recorder({"data": [{"id": "a-1", "title": "News", "iReadIt": False}]})
    sdk = make_sdk(recorder)

    announcements = sdk.announcements.list(limit=5)

    params = recorder.last.url.params
    assert recorder.last.url.path == "/private/notification/v1/employee-announcements"
    assert params["limit"] == "5"
    assert params["orderBy"] == "sentAt desc"
    assert params["archivedAt[null]"] == "true"
    assert announcements[0].i_read_it is False


def test_documents_list_paginated():
    recorder = Recorder(
        {
            "data": [{"id": "doc-1", "name": "payroll.pdf"}],
            "meta": {"total": 1, "page": 1, "lastPage": 1, "perPage": 20},
        }
    )
    sdk = make_sdk(recorder)

    page = sdk.documents.list()

    params = recorder.last.url.params
    assert params["viewerReferenceType"] == "employee"
    assert params["viewerReferenceId"] == "employee-1"
    assert page.data[0].name == "payroll.pdf"
    assert page.meta.last_page == 1


def test_documents_upload_multipart():
    recorder = Recorder({"id": "doc-2"})
    sdk = make_sdk(recorder)

    result = sdk.documents.upload(
        directory_id="dir-1",
        file=b"pdf-bytes",
        file_name="contract.pdf",
        name="Contract",
        notify_employee=True,
    )

    request = recorder.last
    assert request.url.path == "/api/v3/directories/dir-1/documents"
    assert request.headers["Content-Type"].startswith("multipart/form-data")
    assert b'filename="contract.pdf"' in request.content
    assert b'name="notifyEmployee"' in request.content
    assert result == {"id": "doc-2"}


def test_work_stats_summary():
    recorder = Recorder(
        {
            "data": {
                "secondsWorked": 28800,
                "secondsToWork": 28800,
                "balance": 0,
                "workedDays": 1,
                "checksOrigin": {"mobile": 1, "web": 2},
                "checksGeo": {"with": 1, "without": 2},
            }
        }
    )
    sdk = make_sdk(recorder)

    stats = sdk.work_stats.summary("2026-06-01", "2026-06-12")

    body = json.loads(recorder.last.content)
    assert body == {"employeeIds": ["employee-1"], "from": "2026-06-01", "to": "2026-06-12"}
    assert stats.seconds_worked == 28800
    assert stats.checks_origin.web == 2
    assert stats.checks_geo.with_ == 1


def test_team_approvals_post_to_id_paths():
    recorder = Recorder({"data": {}})
    sdk = make_sdk(recorder)

    sdk.team.approve_check_request("req-1")
    assert recorder.last.url.path == "/api/v3/accepted-check-requests/req-1"

    sdk.team.reject_vacation("req-2")
    assert recorder.last.url.path == "/api/v3/rejected-day-off-requests/req-2"


def test_vacations_request_body():
    recorder = Recorder({"data": {"id": "vac-1"}})
    sdk = make_sdk(recorder)

    result = sdk.vacations.request(calendar_id="cal-1", dates=["2026-07-01", "2026-07-02"])

    body = json.loads(recorder.last.content)
    assert body == {
        "employeeId": "employee-1",
        "calendarId": "cal-1",
        "dates": ["2026-07-01", "2026-07-02"],
    }
    assert result == {"id": "vac-1"}


def test_notifications_send_push_graceful_failure():
    sdk = make_sdk(lambda request: httpx.Response(403, json={"message": "forbidden"}))
    assert (
        sdk.notifications.send_push(
            employee_id="emp-2", title="Hi", message="Hello", application_id="app-1"
        )
        is False
    )


def test_notifications_send_push_success():
    recorder = Recorder({"data": {}})
    sdk = make_sdk(recorder)

    ok = sdk.notifications.send_push(
        employee_id="emp-2", title="Hi", message="Hello", application_id="app-1"
    )

    body = json.loads(recorder.last.content)
    assert ok is True
    assert body["clickAction"] == "ApiPushNotificationSent"
    assert body["clickActionPayload"] == {"id": "app-1", "employeeId": ""}


def test_recruitment_vacancies_uses_company_id():
    recorder = Recorder({"data": [], "meta": {"total": 0, "page": 1, "lastPage": 1, "perPage": 20}})
    sdk = make_sdk(recorder)

    sdk.recruitment.vacancies(search="dev")

    request = recorder.last
    assert request.url.path == "/api/v3/companies/company-1/vacancies"
    assert request.url.params["name[contains]"] == "dev"


def test_expenses_list_filters_and_envelope():
    # The expenses endpoints nest the list under data.expenses alongside totals,
    # with currentPage-style meta (NOT the standard Paginated envelope).
    recorder = Recorder(
        {
            "data": {
                "expenses": [
                    {
                        "id": "exp-1",
                        "concept": "Taxi",
                        "totalImport": 12.5,
                        "currency": "EUR",
                        "status": "pending",
                        "paymentStatus": {"value": "booked", "reason": None},
                        "category": {"id": "cat-1", "name": "transport", "isDefault": True},
                    }
                ],
                "totalAmount": 12.5,
                "totalExpenses": 1,
                "totalAmountAccepted": 0,
                "totalPendingToRefund": 12.5,
            },
            "meta": {"currentPage": 1, "lastPage": 3, "total": 5, "perPage": 1},
        }
    )
    sdk = make_sdk(recorder)

    page = sdk.expenses.list(from_="2026-06-01", to="2026-06-30", status="pending")

    params = recorder.last.url.params
    assert recorder.last.url.path == "/api/v3/employee-expenses"
    assert params["from"] == "2026-06-01"
    assert params["to"] == "2026-06-30"
    assert params["status"] == "pending"

    assert len(page.expenses) == 1
    assert page.expenses[0].id == "exp-1"
    assert page.expenses[0].total_import == 12.5
    assert page.expenses[0].payment_status.value == "booked"
    assert page.expenses[0].category.name == "transport"
    assert page.total_amount == 12.5
    assert page.total_pending_to_refund == 12.5
    assert page.meta.current_page == 1
    assert page.meta.total == 5
