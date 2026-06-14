import json

import httpx

from conftest import Recorder, make_sdk


def bi_responder(rows):
    def handler(request):
        return httpx.Response(200, json=rows)

    return handler


def test_list_queries_bi_and_parses_models():
    rows = [
        {
            "name": "Ana García",
            "firstName": "Ana",
            "lastName": "García",
            "email": "ana@company.com",
            "workStatus": "online",
            "status": "active",
            "imageProfileURL": "https://img.example.com/ana.png",
        }
    ]
    recorder = Recorder(bi_responder(rows))
    sdk = make_sdk(recorder)

    employees = sdk.employees.list(status="active")

    body = json.loads(recorder.last.content)
    assert body["from"] == "core_context_employee"
    assert {"field": "core_context_employee.status", "operator": "=", "value": "active"} in body["where"]
    assert body["limit"] == 250

    assert len(employees) == 1
    assert employees[0].name == "Ana García"
    assert employees[0].work_status == "online"
    assert employees[0].image_profile_url == "https://img.example.com/ana.png"


def test_working_filters_by_work_status():
    recorder = Recorder(bi_responder([]))
    sdk = make_sdk(recorder)
    sdk.employees.working()

    body = json.loads(recorder.last.content)
    assert {
        "field": "core_context_employee.work_status",
        "operator": "IN",
        "value": ["online", "remote"],
    } in body["where"]


def test_employee_filter_by_email():
    recorder = Recorder(bi_responder([]))
    sdk = make_sdk(recorder)
    sdk.employees.working(employee="ana@company.com")

    body = json.loads(recorder.last.content)
    assert {"field": "core_context_employee.email", "operator": "=", "value": "ana@company.com"} in body["where"]


def test_by_department_groups_and_counts():
    rows = [{"group": "Engineering", "count": 12}]
    recorder = Recorder(bi_responder(rows))
    sdk = make_sdk(recorder)

    counts = sdk.employees.by_department()

    body = json.loads(recorder.last.content)
    assert body["group_by"] == ["core_context_department.name"]
    assert counts[0].group == "Engineering"
    assert counts[0].count == 12


def test_me_unwraps_array_response():
    payload = {
        "data": [
            {
                "id": "emp-1",
                "workStatus": "online",
                "firstName": "Ana",
                "highestRole": "admin",
                "isValidator": True,
                "entityPermissions": [
                    {
                        "id": "perm-1",
                        "section": "payroll.complements",
                        "entityReferenceId": "emp-1",
                        "entityReferenceType": "employee",
                        "read": True,
                        "write": False,
                        "admin": False,
                    }
                ],
            }
        ]
    }
    recorder = Recorder(payload)
    sdk = make_sdk(recorder)

    me = sdk.employees.me()

    assert recorder.last.url.path == "/api/v3/security/me"
    assert me.id == "emp-1"
    assert me.highest_role == "admin"
    assert me.is_validator is True
    assert me.entity_permissions[0].section == "payroll.complements"
    assert me.entity_permissions[0].read is True
